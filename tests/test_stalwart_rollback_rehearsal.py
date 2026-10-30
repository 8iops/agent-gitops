from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parents[1] / 'operations/stalwart-self-service/rehearsal/rollback'


def test_rollback_is_isolated_suspended_and_full_verified():
    job = yaml.safe_load((BASE / 'job.yaml').read_text())
    pod = job['spec']['template']['spec']
    assert job['spec']['suspend'] is True
    assert pod['automountServiceAccountToken'] is False
    claims = {v['name']: v['persistentVolumeClaim'] for v in pod['volumes'] if 'persistentVolumeClaim' in v}
    assert set(claims) == {'target', 'state', 'rollback'}
    assert claims['target']['claimName'] == 'stalwart-rehearsal-target-v1-local'
    assert claims['target']['readOnly'] is True
    assert claims['rollback']['claimName'] == 'stalwart-rehearsal-rollback-v01627-local'
    script = (BASE / 'rollback.sh').read_text()
    assert 'startup-v1-rehearsal-v1/ACCEPTED' in script
    assert 'stalwart-migrate rollback --verify-full --yes' in script
    assert '--allow-errors' not in script and '--allow-shared-deletes' not in script
