from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parents[1] / 'operations/stalwart-self-service/rehearsal/full-verify'


def test_full_verify_is_suspended_read_only_and_no_token():
    job = yaml.safe_load((BASE / 'job.yaml').read_text())
    pod = job['spec']['template']['spec']
    assert job['spec']['suspend'] is True
    assert pod['automountServiceAccountToken'] is False
    container = pod['containers'][0]
    assert container['command'] == ['/bin/sh', '/scripts/verify.sh']
    mounts = {mount['name']: mount for mount in container['volumeMounts']}
    assert mounts['source']['readOnly'] is True
    assert mounts['target']['readOnly'] is True
    claims = {v['name']: v['persistentVolumeClaim'] for v in pod['volumes'] if 'persistentVolumeClaim' in v}
    assert claims['source']['claimName'] == 'stalwart-rehearsal-source-v01627-local'
    assert claims['target']['claimName'] == 'stalwart-rehearsal-target-v1-local'
