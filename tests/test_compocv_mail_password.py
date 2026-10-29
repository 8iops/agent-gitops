import base64
import importlib.util
import io
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mail_password',ROOT/'operations/compocv-feedback/provision_mail_password.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)


def fixture(monkeypatch, fail_persist=False):
    state={'secret':None,'calls':[],'apps':[]}
    def kube(*args,body=None):
        if args[:2]==('get','service'):return {'spec':{'clusterIP':'10.43.1.1','ports':[{'port':8080}]}}
        if args[:3]==('get','secret','stalwart-recovery-admin'):return {'data':{'STALWART_RECOVERY_ADMIN':base64.b64encode(b'admin:synthetic').decode()}}
        if args[:2]==('get','secret'):return state['secret']
        if args[0]=='create':
            if fail_persist:raise ValueError('persistence failed')
            state['secret']={'metadata':{'resourceVersion':'1'},'data':{k:base64.b64encode(v.encode()).decode() for k,v in body['stringData'].items()}}
            return state['secret']
        raise AssertionError(args)
    class Opener:
        def open(self,req,timeout):
            if req.data is None:result={'apiUrl':'https://id.re8ch.com/jmap','accounts':{'q':{}}}
            else:
                method,args,tag=json.loads(req.data)['methodCalls'][0];state['calls'].append((method,args))
                result={
                    'x:Domain/query':{'ids':['b']},'x:Account/query':{'ids':['q']},
                    'x:Account/get':{'list':[{'id':'q','domainId':'b','roles':{'@type':'User'}}]},
                    'x:AppPassword/query':{'ids':[x['id'] for x in state['apps']]},
                    'x:AppPassword/get':{'list':state['apps']},
                }.get(method)
                if method=='x:AppPassword/set':
                    if 'create' in args:
                        state['apps']=[{'id':'1','description':p.DESCRIPTION}]
                        result={'created':{'intake':{'id':'1','secret':'synthetic-app-password'}}}
                    else:state['apps']=[];result={'destroyed':args['destroy']}
                assert result is not None
                result={'methodResponses':[[method,result,tag]]}
            return io.BytesIO(json.dumps(result).encode())
    monkeypatch.setattr(p,'kubectl',kube);monkeypatch.setattr(p.m,'build_opener',lambda *args:Opener())
    return state


def test_plan_has_no_writes_and_rejects_changed_approval(monkeypatch):
    state=fixture(monkeypatch)
    assert p.run()['plan']['secretVersion'] is None
    with pytest.raises(ValueError,match='plan changed'):p.run(True,'wrong')
    assert not any(method.endswith('/set') for method,_ in state['calls'])


def test_create_and_replay_keep_credential_private_and_scoped(monkeypatch):
    state=fixture(monkeypatch)
    result=p.run(True,p.run()['planHash'])
    assert result['outcome']=='ready' and 'synthetic-app-password' not in json.dumps(result)
    p.run(True,p.run()['planHash'])
    creates=[args for method,args in state['calls'] if method.endswith('/set') and 'create' in args]
    assert len(creates)==1
    permissions=creates[0]['create']['intake']['permissions']
    assert permissions=={'@type':'Replace','permissions':p.PERMISSIONS}
    assert not any('Send' in x or 'Create' in x or 'Destroy' in x for x in p.PERMISSIONS)


def test_failed_secret_persistence_revokes_new_app_password(monkeypatch):
    state=fixture(monkeypatch,fail_persist=True)
    with pytest.raises(ValueError,match='persistence failed'):p.run(True,p.run()['planHash'])
    assert not state['apps']
    assert state['calls'][-1]==('x:AppPassword/set',{'accountId':'q','destroy':['1']})
