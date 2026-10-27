from pathlib import Path
from urllib.parse import urlparse
import yaml

ROOT=Path(__file__).resolve().parents[1]

def test_cube_identity_matches_registered_public_callback_without_privilege_changes():
    plan=yaml.safe_load((ROOT/'operations/identity/cube-stalwart-migration.yaml').read_text())
    docs=list(yaml.safe_load_all((ROOT/'releases/agent-runtime-domain-cube-trial/resources.yaml').read_text()))
    deployment=next(d for d in docs if d['kind']=='Deployment')
    route=next(d for d in docs if d['kind']=='HTTPRoute')
    pod=deployment['spec']['template']['spec'];container=pod['containers'][0]
    args=dict(arg[2:].split('=',1) for arg in container['args'] if '=' in arg)
    assert args['oidc-issuer-url']==plan['provider']['issuer']
    assert args['redirect-url'] in plan['client']['redirectUris']
    assert urlparse(args['redirect-url']).hostname in route['spec']['hostnames']
    assert args['email-domain']==plan['constraints']['preserveProxyEmailPolicy']
    assert args['scope']==plan['constraints']['preserveProxyScopes']
    assert container['envFrom']==[{'secretRef':{'name':'oauth2-proxy-cube'}}]
    assert deployment['metadata']['namespace']==plan['application']['namespace']=='cube-trial'
    assert pod['automountServiceAccountToken'] is False
    assert plan['client']['newClientScopes']=={}
    assert plan['client']['secretFrom']['namespace']=='cube-trial'
    assert plan['constraints']['markFirstParty'] is False

def test_cube_registration_is_confidential_minimal_and_redirects_stay_internal():
    import importlib.util
    import pytest
    spec=importlib.util.spec_from_file_location('cube_registration',ROOT/'operations/identity/register_cube_stalwart.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    payload=module.registration('existing-client','fixture-not-a-real-secret')
    assert payload['clientId']=='existing-client' and payload['secret']=='fixture-not-a-real-secret'
    assert payload['redirectUris']=={'https://cube.re8ch.com/oauth2/callback':True}
    assert payload['scopes']=={} and 'firstParty' not in payload and 'memberTenantId' not in payload
    assert module.internal_api_url({'apiUrl':'https://id.re8ch.com/jmap/'},'http://127.0.0.1:8080')=='http://127.0.0.1:8080/jmap/'
    with pytest.raises(ValueError):module.internal_api_url({'apiUrl':'https://other.invalid/steal'},'http://127.0.0.1:8080')
    assert module.plan_hash(payload,'state-1')!=module.plan_hash(payload,'state-2')
    assert module.plan_hash(payload,'state-1')!=module.plan_hash({**payload,'secret':'changed-fixture'},'state-1')

def test_cube_registration_requires_same_reviewed_state_before_one_create(monkeypatch):
    import importlib.util,json,io
    import pytest
    spec=importlib.util.spec_from_file_location('cube_registration_flow',ROOT/'operations/identity/register_cube_stalwart.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    credentials={'STALWART_RECOVERY_ADMIN':'fixture-user:fixture-pass','OAUTH2_PROXY_CLIENT_ID':'fixture-client','OAUTH2_PROXY_CLIENT_SECRET':'fixture-private-value','OAUTH2_PROXY_COOKIE_SECRET':'fixture-cookie'}
    monkeypatch.setattr(module,'secret',lambda *_:credentials)
    monkeypatch.setattr(module,'service_base',lambda:'http://127.0.0.1:8080')
    requests=[]
    existing=[False]
    class Response(io.BytesIO):
        def __enter__(self):return self
        def __exit__(self,*args):self.close()
    class Opener:
        def open(self,request,timeout):
            assert request.full_url.startswith('http://127.0.0.1:8080/')
            if request.data is None:reply={'apiUrl':'https://id.re8ch.com/jmap/'}
            else:
                method,args,_=json.loads(request.data)['methodCalls'][0];requests.append((method,args))
                if method.endswith('/query'):data={'ids':['id1'] if existing[0] else []}
                elif method.endswith('/get') and not args['ids']:data={'list':[],'notFound':[],'accountId':None}
                elif method.endswith('/get'):data={'state':'new-state','list':[{'id':'id1','clientId':'fixture-client','redirectUris':{module.CALLBACK:True},'scopes':{}}]}
                else:
                    assert method=='x:OAuthClient/set'
                    assert set(args)=={'create'}
                    data={'created':{'cube':{'id':'id1'}}}
                reply={'methodResponses':[[method,data,'cube']]}
            return Response(json.dumps(reply).encode())
    monkeypatch.setattr(module,'build_opener',lambda *_:Opener())
    plan=module.execute();assert plan['outcome']=='planned'
    assert not any(m.endswith('/set') for m,_ in requests)
    with pytest.raises(ValueError):module.execute(True,'wrong-hash')
    assert not any(m.endswith('/set') for m,_ in requests)
    result=module.execute(True,plan['planHash']);assert result['outcome']=='created-and-verified'
    assert sum(m.endswith('/set') for m,_ in requests)==1
    assert 'fixture-private-value' not in json.dumps([plan,result])
    assert result['kubernetesSecretsChanged'] is False

    existing[0]=True
    with pytest.raises(ValueError,match='independent credential verification'):module.execute(True,plan['planHash'])
    assert sum(m.endswith('/set') for m,_ in requests)==1

def test_fixed_service_resolution_rejects_wrong_port_and_headless(monkeypatch):
    import importlib.util,json,types
    import pytest
    spec=importlib.util.spec_from_file_location('cube_service',ROOT/'operations/identity/register_cube_stalwart.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    service={'clusterIP':'10.43.1.2','ports':[{'port':8080,'protocol':'TCP'}]}
    def run(argv,**kwargs):
        assert argv[2:7]==['get','service','stalwart','-n','mail-system']
        return types.SimpleNamespace(stdout=json.dumps({'spec':service}))
    monkeypatch.setattr(module.subprocess,'run',run)
    assert module.service_base()=='http://10.43.1.2:8080'
    service['ports'][0]['port']=80
    with pytest.raises(ValueError):module.service_base()
    service['ports'][0]['port']=8080;service['clusterIP']='None'
    with pytest.raises(ValueError):module.service_base()
