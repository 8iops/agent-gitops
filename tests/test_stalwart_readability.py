import json
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'operations/stalwart-self-service/rehearsal/readability'


def test_console_filter_discards_private_values_and_logs():
    sample = 'temporary admin password: DO_NOT_RETURN\n> \\x00\\x00\\x00\\x06\np\\x00 : \\x00\\x00\\x00\\x06\np\\x01 : PRIVATE_MAIL_CONTENT\n> Exiting...\n'
    result = subprocess.run(['awk', '-f', str(PROBE / 'readability.awk')], input=sample, text=True, capture_output=True)
    assert result.returncode == 0
    assert json.loads(result.stdout) == {'nativeReadability': 'pass', 'schemaVersion': 6, 'propertyRecords': 2}
    assert 'DO_NOT_RETURN' not in result.stdout and 'PRIVATE_MAIL_CONTENT' not in result.stdout


@pytest.mark.parametrize('sample', ['', '> \\x00\\x00\\x00\\x06\np\\x00 : schema\n', 'pkey : value\npkey2 : value\n'])
def test_console_filter_rejects_missing_version_or_empty_data(sample):
    result = subprocess.run(['awk', '-f', str(PROBE / 'readability.awk')], input=sample, text=True, capture_output=True)
    assert result.returncode != 0
    assert json.loads(result.stdout) == {'nativeReadability': 'failed'}


def test_probe_uses_only_working_copy_and_prevents_bootstrap_fallback():
    job = yaml.safe_load((PROBE / 'job.yaml').read_text())
    assert job['spec']['suspend'] is True
    pod = job['spec']['template']['spec']
    assert pod['automountServiceAccountToken'] is False
    claims = {v['name']: v['persistentVolumeClaim'] for v in pod['volumes'] if 'persistentVolumeClaim' in v}
    assert claims['baseline'] == {'claimName': 'stalwart-rehearsal-source-restore-local', 'readOnly': True}
    assert claims['working']['claimName'] == 'stalwart-rehearsal-source-v01627-local'
    assert all(c['claimName'] != 'stalwart-flk-local-data' for c in claims.values())
    script = (PROBE / 'readability.sh').read_text()
    assert 'unset CONFIG_PATH' in script
    assert script.index('[ -s /baseline/database/CURRENT ]') < script.index('/usr/local/bin/stalwart')
    assert 'MANIFEST-*' in script
    assert '"path":"/var/lib/stalwart/database"' in script
    assert '--config /work/config.json --console' in script
    assert 'quit > /work/commands' in script
    assert 'mkfifo /work/native-output' in script
    assert '> /work/native-output' in script
    assert 'cat /state/native-v01618/result.json' in script
