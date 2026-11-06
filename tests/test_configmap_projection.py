import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parents[1]/'operations/releases'))
from ssa_compare import configmap_owned_fields_match


def pair():
    desired = {'apiVersion':'v1','kind':'ConfigMap',
               'metadata':{'name':'catalog','namespace':'tools','annotations':{'release':'accepted'}},
               'data':{'catalog.json':'accepted content'}}
    live = copy.deepcopy(desired)
    live['metadata']['managedFields'] = [{
        'manager':'release/test','operation':'Apply','apiVersion':'v1','fieldsType':'FieldsV1',
        'fieldsV1':{'f:data':{'f:catalog.json':{}},'f:metadata':{'f:annotations':{'f:release':{}}}}}]
    return desired, live


def test_equal_owned_fields_ignore_other_owners_without_upload():
    desired, live = pair()
    live['data']['foreign'] = 'owned by another manager'
    live['metadata']['annotations']['foreign'] = 'external'
    assert configmap_owned_fields_match(desired, live, 'release/test')


@pytest.mark.parametrize('case', ['data-drift','annotation-drift','removed-owned-key','new-desired-key',
    'unknown-ownership','wrong-manager','update-manager','wrong-version','wrong-type',
    'duplicate-manager','finalizers','different-object','not-configmap','immutable-drift'])
def test_uncertain_or_changed_projection_requires_server_dryrun(case):
    desired, live = pair()
    entry = live['metadata']['managedFields'][0]
    if case == 'data-drift': live['data']['catalog.json']='changed'
    elif case == 'annotation-drift': live['metadata']['annotations']['release']='changed'
    elif case == 'removed-owned-key':
        live['data']['old']='removed from accepted bundle'
        entry['fieldsV1']['f:data']['f:old']={}
    elif case == 'new-desired-key': desired['data']['new']='new value'
    elif case == 'unknown-ownership': entry['fieldsV1']['f:data']['k:unsupported']={}
    elif case == 'wrong-manager': entry['manager']='another'
    elif case == 'update-manager': entry['operation']='Update'
    elif case == 'wrong-version': entry['apiVersion']='unknown'
    elif case == 'wrong-type': entry['fieldsType']='unknown'
    elif case == 'duplicate-manager': live['metadata']['managedFields'].append(copy.deepcopy(entry))
    elif case == 'finalizers': desired['metadata']['finalizers']=['unknown']
    elif case == 'different-object': live['metadata']['name']='other'
    elif case == 'not-configmap': desired['kind']='Secret'
    elif case == 'immutable-drift':
        desired['immutable']=True;live['immutable']=False;entry['fieldsV1']['f:immutable']={}
    assert not configmap_owned_fields_match(desired, live, 'release/test')
