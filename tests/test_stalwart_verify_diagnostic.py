import importlib.util
from pathlib import Path

import pytest
import yaml

BASE = Path(__file__).resolve().parents[1] / 'operations/stalwart-self-service/rehearsal/verify-diagnostic'
spec = importlib.util.spec_from_file_location('verify_diagnostic', BASE / 'diagnose.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(path, stdout):
    path.mkdir()
    (path / 'native-exit').write_text('1\n')
    (path / 'stdout').write_text(stdout)
    (path / 'stderr').write_text('SENTINEL_SECRET')
    module.ROOT = path


def test_numeric_only_summary(tmp_path):
    fixture(tmp_path / 'state', 'private SENTINEL_SECRET\nverify: 17 accounts checked, 2 mismatches, 1 not explained by earlier reports (failed)\n')
    result = module.diagnose()
    assert result['numericSummary'] == {'accountsChecked': 17, 'mismatches': 2, 'unexplained': 1}
    assert result['fullVerificationAccepted'] is False
    assert 'SENTINEL' not in str(result)


def test_pre_summary_failure_and_malformed_count(tmp_path):
    fixture(tmp_path / 'state', 'private SENTINEL_SECRET\n')
    result = module.diagnose()
    assert result['nativeSummaryPresent'] is False
    (module.ROOT / 'stdout').write_text('verify: 1 accounts checked, 1 mismatches, 2 not explained by earlier reports (failed)')
    with pytest.raises(ValueError):
        module.diagnose()


def test_job_has_only_readonly_state_and_no_token():
    job = yaml.safe_load((BASE / 'job.yaml').read_text())
    pod = job['spec']['template']['spec']
    assert job['spec']['suspend'] and pod['automountServiceAccountToken'] is False
    assert len(pod['volumes']) == 2
    assert pod['volumes'][0]['persistentVolumeClaim']['readOnly'] is True
    assert all(m['readOnly'] for m in pod['containers'][0]['volumeMounts'])
