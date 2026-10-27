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
    assert module.internal_api_url({'apiUrl':'https://id.re8ch.com/jmap/'})==module.BASE+'/jmap/'
    with pytest.raises(ValueError):module.internal_api_url({'apiUrl':'https://other.invalid/steal'})
    assert module.plan_hash(payload,'state-1')!=module.plan_hash(payload,'state-2')
    assert module.plan_hash(payload,'state-1')!=module.plan_hash({**payload,'secret':'changed-fixture'},'state-1')

def test_cube_registration_requires_same_reviewed_state_before_one_create(monkeypatch):
    import importlib.util,json,io
    import pytest
    spec=importlib.util.spec_from_file_location('cube_registration_flow',ROOT/'operations/identity/register_cube_stalwart.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    credentials={'STALWART_RECOVERY_ADMIN':'fixture-user:fixture-pass','OAUTH2_PROXY_CLIENT_ID':'fixture-client','OAUTH2_PROXY_CLIENT_SECRET':'fixture-private-value','OAUTH2_PROXY_COOKIE_SECRET':'fixture-cookie'}
    monkeypatch.setattr(module,'secret',lambda *_:credentials)
    requests=[]
    class Response(io.BytesIO):
        def __enter__(self):return self
        def __exit__(self,*args):self.close()
    class Opener:
        def open(self,request,timeout):
            assert request.full_url.startswith(module.BASE+'/')
            if request.data is None:reply={'apiUrl':'https://id.re8ch.com/jmap/'}
            else:
                method,args,_=json.loads(request.data)['methodCalls'][0];requests.append((method,args))
                if method.endswith('/query'):data={'ids':[]}
                elif method.endswith('/get') and not args['ids']:data={'state':'reviewed-state','list':[]}
                elif method.endswith('/get'):data={'state':'new-state','list':[{'id':'id1','clientId':'fixture-client','redirectUris':{module.CALLBACK:True},'scopes':{}}]}
                else:
                    assert method=='x:OAuthClient/set' and args['ifInState']=='reviewed-state'
                    assert set(args)=={'ifInState','create'}
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
