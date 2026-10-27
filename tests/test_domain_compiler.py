import importlib.util
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'operations/releases'))
import compile_domain as compiler

def obj(kind='ConfigMap',api='v1',namespace='demo',name='demo',**extra):
    d={'apiVersion':api,'kind':kind,'metadata':{'name':name}}
    if namespace:d['metadata']['namespace']=namespace
    d.update(extra)
    return d

@pytest.mark.parametrize('item,reason',[
    (obj('Role','rbac.authorization.k8s.io/v1'),'platform-owned-rbac'),
    (obj('RoleBinding','rbac.authorization.k8s.io/v1'),'platform-owned-rbac'),
    (obj('Secret',data={'token':'not-a-real-credential'}),'secret-provisioning'),
    (obj(data={'config':'ENC[AES256_GCM,data:opaque]'}),'restricted-cloud-decryption'),
    (obj('HelmRelease','helm.toolkit.fluxcd.io/v2'),'helm-render'),
    (obj('Namespace',namespace=None),'cluster-scoped-bootstrap'),
    (obj('Deployment','apps/v1',spec={'template':{'spec':{'containers':[{'name':'app','image':'repo/app:latest'}]}}}),'image-digest-required'),
    (obj('Unregistered','unregistered.example/v1'),'custom-resource-access-required'),
])
def test_unpublishable_objects_are_visible_deferred_work(item,reason):
    assert compiler.classify(item,set())==reason

def test_existing_release_remains_single_writer():
    item=obj();ident=compiler.object_identity(item)
    assert compiler.classify(item,{ident})=='existing-release-contract'
    assert compiler.classify(item,set()) is None

def test_long_namespace_names_do_not_collide():
    names=[compiler.release_name('a'*56+suffix) for suffix in ['-first','-other']]
    assert len(set(names))==2
    assert all(len(name)<=63 for name in names)


def test_runtime_profiles_cannot_write_rbac_or_escalate():
    import yaml
    access=list(yaml.safe_load_all((ROOT/'operations/releases/domain-access.yaml').read_text()))
    for role in access:
        if role['kind']!='Role':continue
        for rule in role['rules']:
            assert 'rbac.authorization.k8s.io' not in rule['apiGroups']
            assert not {'bind','escalate','impersonate'} & set(rule['verbs'])
