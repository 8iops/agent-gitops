#!/usr/bin/env python3
"""Platform-only, bounded app-password provisioning; default is a read-only plan."""
import argparse
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

MODULE = Path(__file__).resolve().parents[1]/'identity/register_cube_stalwart.py'
spec = importlib.util.spec_from_file_location('registration', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NAME = 'compocv-feedback-app-password'
ADDRESS = 'compocv-maintain@phonaid.com'
DESCRIPTION = 'CompoCV private GitHub feedback intake'
PERMISSIONS = dict.fromkeys(['authenticate', 'jmapMailboxGet', 'jmapMailboxQuery', 'jmapEmailGet', 'jmapEmailQuery', 'jmapThreadGet'], True)


def kubectl(*args, body=None):
    p = subprocess.run(['sudo','-n','/usr/local/bin/k3s','kubectl',*args], input=None if body is None else json.dumps(body), text=True, capture_output=True)
    if p.returncode: raise ValueError('bounded Kubernetes operation failed')
    return json.loads(p.stdout) if p.stdout.strip() else None


def run(apply=False, expected=None):
    service=kubectl('get','service','stalwart','-n','mail-system','-o','json')
    address=m.ipaddress.ip_address(service['spec']['clusterIP'])
    if not any(p['port']==8080 for p in service['spec']['ports']): raise ValueError('service port mismatch')
    base='http://'+str(address)+':8080'
    admin=kubectl('get','secret','stalwart-recovery-admin','-n','mail-system','-o','json')
    authorization='Basic '+admin['data']['STALWART_RECOVERY_ADMIN']
    opener=m.build_opener(m.ProxyHandler({}),m.NoRedirect())
    def request(url, body=None, auth=None):
        req=m.Request(url,data=None if body is None else json.dumps(body).encode(),headers={'Host':m.HOST,'Authorization':auth or authorization,'Content-Type':'application/json'})
        with opener.open(req,timeout=20) as response:return json.load(response)
    session=request(base+'/jmap/session')
    endpoint=m.internal_api_url(session,base)
    def call(method,args):
        rows=request(endpoint,{'using':m.CAPABILITIES,'methodCalls':[[method,args,'feedback']]})['methodResponses']
        if len(rows)!=1 or rows[0][0]!=method: raise m.RegistrationError('method-error',{'error':m.safe_api_error(rows[0][1])})
        result=rows[0][1]
        for key in ('notCreated','notUpdated','notDestroyed'):
            if result.get(key): raise m.RegistrationError('object-error',{'error':m.safe_api_error(next(iter(result[key].values())))})
        return result
    domains=call('x:Domain/query',{'filter':{'name':'phonaid.com'}})['ids']
    ids=call('x:Account/query',{'filter':{'name':'compocv-maintain'}})['ids']
    accounts=call('x:Account/get',{'ids':ids,'properties':['id','name','domainId','roles']})['list']
    if len(domains)!=1 or len(accounts)!=1 or accounts[0]['domainId']!=domains[0] or accounts[0]['roles']!={'@type':'User'}:raise ValueError('mailbox identity mismatch')
    account=accounts[0]['id']
    current=kubectl('get','secret',NAME,'-n','mail-system','--ignore-not-found','-o','json')
    app_ids=call('x:AppPassword/query',{'accountId':account})['ids']
    apps=call('x:AppPassword/get',{'accountId':account,'ids':app_ids,'properties':['id','description']})['list']
    ours=[a for a in apps if a.get('description')==DESCRIPTION]
    plan={'accountId':account,'email':ADDRESS,'secretName':NAME,'permissions':PERMISSIONS,'existingAppIds':[a['id'] for a in ours],'secretVersion':current['metadata']['resourceVersion'] if current else None}
    digest=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
    if not apply:return {'plan':plan,'planHash':digest}
    if expected!=digest:raise ValueError('plan changed')
    if current:
        password=base64.b64decode(current['data']['password']).decode()
    else:
        if ours:raise ValueError('orphan app credential requires explicit recovery')
        created=call('x:AppPassword/set',{'accountId':account,'create':{'intake':{'description':DESCRIPTION,'permissions':{'@type':'Replace','permissions':PERMISSIONS}}}})['created']['intake']
        password=created['secret']
        # Secret is persisted before login verification so retries never mint duplicates.
        try:
            kubectl('create','-f','-','-o','json',body={'apiVersion':'v1','kind':'Secret','metadata':{'name':NAME,'namespace':'mail-system','labels':{'app.kubernetes.io/managed-by':'compocv-feedback-bootstrap'}},'type':'Opaque','stringData':{'username':ADDRESS,'password':password,'credential-id':created['id'],'account-id':account}})
        except Exception:
            call('x:AppPassword/set',{'accountId':account,'destroy':[created['id']]})
            raise
    auth='Basic '+base64.b64encode((ADDRESS+':'+password).encode()).decode()
    verified=request(base+'/jmap/session',auth=auth)
    if account not in verified.get('accounts',{}):raise ValueError('application password account mismatch')
    return {'outcome':'ready','accountId':account,'secretName':NAME,'permissions':list(PERMISSIONS),'credentialsPrinted':False}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--expected-plan-hash');args=p.parse_args()
    try:print(json.dumps(run(args.apply,args.expected_plan_hash)))
    except Exception as error:
        print(json.dumps(m.failure_report(error)));sys.exit(1)
