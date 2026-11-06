import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(Path(__file__).parents[1]/'operations/releases'))
import receipt_reconcile as receipt

@pytest.mark.parametrize('failure', [None, 'timeout', 'ownership'])
def test_real_receipt_projection_chain(tmp_path, monkeypatch, failure):
    item = {'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'demo','namespace':'test','resourceVersion':'1','annotations':{'delivery.re8ch.com/release-id':'demo'}},'data':{'key':'value'}}
    operation = {'releaseId':'demo','bundle':{'digest':'sha256:accepted'}}
    (tmp_path/'operation.json').write_text(json.dumps(operation))
    contract = tmp_path/'contract.yaml'
    contract.write_text(json.dumps({'spec':{'authorization':{'fieldManager':'test'}}}))
    (tmp_path/'state-cm.json').write_text(json.dumps({'metadata':{'name':'state','namespace':'test'}}))
    monkeypatch.setenv('RUNNER_TEMP',str(tmp_path));monkeypatch.setenv('CONTRACT',str(contract))
    monkeypatch.setattr(receipt.time,'sleep',lambda _:None)
    counts = {'reads':0, 'dryruns':0}
    class FakeExecutor:
        def validate(self,*args): return {},[copy.deepcopy(item)],''
        def with_audit(self,objects,*args): return objects
        def reconcile(self,*args): pytest.fail('aligned projection must never write')
        def command(self,argv,*args,**kwargs):
            if argv[1:4]==['get','configmap','state']:
                state={'releaseId':'demo','appliedDigest':'sha256:accepted','acceptedDigest':'sha256:accepted','blocked':False}
                return SimpleNamespace(stdout=json.dumps({'data':{'accepted-state.json':json.dumps(state)}}))
            if argv[1]=='get':
                counts['reads']+=1
                if failure=='timeout' and counts['reads']==1: raise receipt.Rejected('i/o timeout')
            else:
                assert '--dry-run=server' in argv
                counts['dryruns']+=1
                if failure=='ownership': raise receipt.Rejected('conflict with another field manager')
            return SimpleNamespace(stdout=json.dumps(item))
    monkeypatch.setattr(receipt,'Executor',FakeExecutor)
    report={ 'objects':[], 'applied':[] }
    if failure=='ownership':
        with pytest.raises(receipt.Rejected): receipt.run(report)
        assert counts['dryruns']==1
    else:
        assert receipt.run(report) is True
        assert report['outcome']=='aligned'
        assert counts['dryruns']==2
        assert counts['reads']==(3 if failure=='timeout' else 2)
