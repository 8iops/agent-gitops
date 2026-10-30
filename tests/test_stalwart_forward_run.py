import importlib.util
from pathlib import Path

import pytest
import yaml

BASE = Path(__file__).resolve().parents[1] / 'operations/stalwart-self-service/rehearsal/forward-run'
spec = importlib.util.spec_from_file_location('forward_run_verify', BASE / 'verify.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_verify_only_fixed_status(tmp_path, monkeypatch):
    stage = tmp_path / 'answered-prepare-v1/forward-run-v1'
    stage.mkdir(parents=True)
    (stage / 'native-exit').write_text('0\n')
    target = tmp_path / 'target/database'
    target.mkdir(parents=True)
    (target / 'CURRENT').write_text('SENTINEL_SECRET')
    (target / 'MANIFEST-1').write_text('SENTINEL_SECRET')
    monkeypatch.setattr(module, 'Path', lambda path: stage if path == '/state/answered-prepare-v1/forward-run-v1' else target)
    output = module.verify()
    assert output['forwardRunComplete'] is True
    assert output['fullVerificationComplete'] is False
    assert 'SENTINEL_SECRET' not in str(output)
    (stage / 'native-exit').write_text('1\n')
    with pytest.raises(ValueError):
        module.verify()


def test_job_only_targets_rehearsal_pvcs_and_is_suspended():
    job = yaml.safe_load((BASE / 'job.yaml').read_text())
    pod = job['spec']['template']['spec']
    assert job['spec']['suspend'] and not pod['automountServiceAccountToken']
    pvc = {v['name']: v['persistentVolumeClaim'] for v in pod['volumes'] if 'persistentVolumeClaim' in v}
    assert pvc['source']['claimName'] == 'stalwart-rehearsal-source-v01627-local'
    assert pvc['source']['readOnly'] is True
    assert pvc['target']['claimName'] == 'stalwart-rehearsal-target-v1-local'
    assert pvc['state']['claimName'] == 'stalwart-rehearsal-migration-state-local'
