#!/usr/bin/env python3
"""Bounded platform-only Cube registration using existing Kubernetes Secrets.

Default is read-only planning. Never run on a developer workstation. Credentials
are read in process memory, sent only to the reviewed internal Stalwart Service,
and are never included in stdout, exceptions or files.
"""
import argparse
import base64
import hashlib
import ipaddress
import json
import subprocess
import sys
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from urllib.error import HTTPError

HOST='stalwart.mail-system.svc.cluster.local:8080'
CALLBACK='https://cube.re8ch.com/oauth2/callback'
CAPABILITIES=['urn:ietf:params:jmap:core','urn:stalwart:jmap']

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def secret(namespace,name):
    result=subprocess.run(['/usr/local/bin/k3s','kubectl','get','secret',name,'-n',namespace,'-o','json'],capture_output=True,text=True,check=True)
    return {k:base64.b64decode(v).decode() for k,v in json.loads(result.stdout)['data'].items()}

def service_base():
    result=subprocess.run(['/usr/local/bin/k3s','kubectl','get','service','stalwart','-n','mail-system','-o','json'],capture_output=True,text=True,check=True)
    spec=json.loads(result.stdout)['spec']
    if not any(p.get('port')==8080 and p.get('protocol','TCP')=='TCP' for p in spec['ports']):raise ValueError('unexpected Service port')
    address=ipaddress.ip_address(spec['clusterIP'])
    return 'http://'+('['+str(address)+']' if address.version==6 else str(address))+':8080'

def registration(client_id,client_secret):
    if not client_id or not client_secret:raise ValueError('empty credential')
    return {'clientId':client_id,'secret':client_secret,'description':'Cube sandbox','redirectUris':{CALLBACK:True},'scopes':{}}

def plan_hash(payload,client_state):
    return hashlib.sha256(json.dumps({'payload':payload,'state':client_state},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def internal_api_url(session,base):
    url=urlsplit(session['apiUrl'])
    if url.path.rstrip('/')!='/jmap' or url.query or url.fragment:raise ValueError('unexpected JMAP endpoint')
    # Session advertises a public URL; bind the transport to the existing internal
    # Service rather than sending the administrative credential to that URL.
    return base+url.path

def execute(apply=False,expected_plan_hash=None):
    base=service_base()
    admin=secret('mail-system','stalwart-recovery-admin')['STALWART_RECOVERY_ADMIN']
    cube=secret('cube-trial','oauth2-proxy-cube')
    payload=registration(cube['OAUTH2_PROXY_CLIENT_ID'],cube['OAUTH2_PROXY_CLIENT_SECRET'])
    authorization='Basic '+base64.b64encode(admin.encode()).decode()
    opener=build_opener(ProxyHandler({}),NoRedirect())
    def request(url,body=None):
        data=None if body is None else json.dumps(body).encode()
        req=Request(url,data=data,headers={'Host':HOST,'Authorization':authorization,'Content-Type':'application/json','Accept':'application/json'})
        with opener.open(req,timeout=20) as response:return json.load(response)
    try:session=request(base+'/.well-known/jmap')
    except HTTPError as error:
        if error.code!=307 or error.headers.get('Location')!='/jmap/session':raise ValueError('unexpected session redirect') from None
        session=request(base+'/jmap/session')
    endpoint=internal_api_url(session,base)
    def call(method,args):
        result=request(endpoint,{'using':CAPABILITIES,'methodCalls':[[method,args,'cube']]})['methodResponses']
        if len(result)!=1 or result[0][0]!=method:raise ValueError('unexpected API response')
        return result[0][1]
    ids=call('x:OAuthClient/query',{'filter':{'clientId':payload['clientId']}})['ids']
    current=call('x:OAuthClient/get',{'ids':ids,'properties':['id','clientId','description','redirectUris','scopes','memberTenantId','firstParty']})
    if ids:
        if len(ids)!=1 or len(current['list'])!=1:raise ValueError('ambiguous registration')
        item=current['list'][0]
        if item.get('clientId')!=payload['clientId'] or item.get('redirectUris')!=payload['redirectUris'] or item.get('scopes',{})!={}:raise ValueError('existing client needs separate review')
        if item.get('memberTenantId') is not None or item.get('firstParty',False) is not False:raise ValueError('existing client policy requires separate review')
        raise ValueError('existing client requires independent credential verification; no write performed')
    approval=plan_hash(payload,{'absent':True,'endpoint':endpoint})
    if not apply:
        return {'outcome':'planned','planHash':approval,'clientCount':0,'action':'create-confidential-OAuthClient','callback':CALLBACK,'dataScopes':[],'namespace':'cube-trial','existingClientIdAndSecretReused':True,'cookieSecretUnchanged':True}
    if expected_plan_hash!=approval:raise ValueError('reviewed plan changed')
    result=call('x:OAuthClient/set',{'create':{'cube':payload}})
    if result.get('notCreated') or 'cube' not in result.get('created',{}):raise ValueError('registration rejected')
    object_id=result['created']['cube']['id']
    item=call('x:OAuthClient/get',{'ids':[object_id],'properties':['id','clientId','redirectUris','scopes','memberTenantId','firstParty']})['list'][0]
    if item['clientId']!=payload['clientId'] or item['redirectUris']!=payload['redirectUris'] or item.get('scopes',{})!={} or item.get('memberTenantId') is not None or item.get('firstParty',False) is not False:raise ValueError('registration verification failed')
    return {'outcome':'created-and-verified','clientCount':1,'callback':CALLBACK,'dataScopes':[],'credentialValuesExported':False,'kubernetesSecretsChanged':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--expected-plan-hash');args=parser.parse_args()
    try:
        result=execute(args.apply,args.expected_plan_hash)
    except Exception:
        # HTTP/API diagnostics may contain submitted credential data.
        print(json.dumps({'outcome':'failed','reason':'platform registration failed; credential-bearing diagnostics withheld'}))
        sys.exit(1)
    print(json.dumps(result,sort_keys=True))
