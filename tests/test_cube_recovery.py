import base64
import importlib.util
from pathlib import Path
import yaml
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cube_credentials', ROOT/'operations/cube-recovery/provision_credentials.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_credentials_are_fresh_once_and_replay_preserves_them():
    data = module.credential_data({'data': {}})
    assert len({data[k] for k in module.KEYS}) == len(module.KEYS)
    assert module.credential_data({'data': data}) == data
    rendered = module.master_data('password: __CUBE_MYSQL_PASSWORD__', data)
    assert '__CUBE_' not in base64.b64decode(rendered['conf.yaml']).decode()


def test_partial_credentials_fail_without_rotation():
    with pytest.raises(KeyError):
        module.credential_data({'data': {'mysql-password': base64.b64encode(b'partial').decode()}})
    with pytest.raises(ValueError):
        module.master_data('__CUBE_UNKNOWN__', module.credential_data({}))


def test_runtime_has_isolated_host_paths_and_immutable_images():
    docs = [d for d in yaml.safe_load_all((ROOT/'clusters/re8ch/cube-recovery-resources.yaml').read_text()) if d]
    assert not any(d['kind'] in ('Secret','Job','ClusterRole','ClusterRoleBinding') for d in docs)
    node = next(d for d in docs if d['metadata']['name']=='cube-recovery-node' and d['kind']=='DaemonSet')
    pod = node['spec']['template']['spec']
    assert not pod.get('hostNetwork')
    volumes = {v['name']:v for v in pod['volumes']}
    assert volumes['data-cubelet']['hostPath']['path']=='/data/cube-recovery/cubelet'
    assert volumes['run-containerd']['hostPath']['path'].startswith('/data/cube-recovery/')
    for c in pod['containers']:
        assert '@sha256:' in c['image']
    cubelet=next(c for c in pod['containers'] if c['name']=='cubelet')
    assert next(v for v in cubelet['volumeMounts'] if v['name']=='data-cubelet')['mountPath']=='/data/cubelet'


def test_credentials_job_cannot_create_or_read_unrelated_secrets():
    docs=list(yaml.safe_load_all((ROOT/'operations/cube-recovery/platform-seed.yaml').read_text()))
    role=next(d for d in docs if d['kind']=='Role' and d['metadata']['name']=='cube-recovery-credentials')
    assert role['rules']==[{'apiGroups':[''],'resources':['secrets'],'resourceNames':['cube-recovery-secret','cube-recovery-master-config'],'verbs':['get','patch']}]
    assert all(not d.get('data') and not d.get('stringData') for d in docs if d['kind']=='Secret')
