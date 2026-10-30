from pathlib import Path
import json
import subprocess
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'operations/stalwart-self-service/rehearsal/startup-diagnostic'


def test_log_values_never_return(tmp_path):
    stage = tmp_path / 'startup-v01627'
    stage.mkdir()
    (stage / 'startup.stdout').write_text('Starting Stalwart\nsecret=SENTINEL_PRIVATE_VALUE\n')
    (stage / 'startup.stderr').write_text('Permission denied: SENTINEL_PRIVATE_VALUE\nRead-only file system\n')
    script = (PROBE / 'classify.sh').read_text().replace('/state', str(tmp_path))
    result = subprocess.run(['sh', '-c', script], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'SENTINEL' not in result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data['matches']['permission'] == 1
    assert data['matches']['readonlyFilesystem'] == 1
    assert data['matches']['migration'] == 0


def test_only_readonly_state_is_mounted():
    job = yaml.safe_load((PROBE / 'job.yaml').read_text())
    pod = job['spec']['template']['spec']
    assert job['spec']['suspend'] is True
    assert 'fsGroup' not in pod['securityContext']
    assert pod['automountServiceAccountToken'] is False
    assert len(pod['volumes']) == 2
    assert pod['volumes'][0]['persistentVolumeClaim'] == {'claimName': 'stalwart-rehearsal-migration-state-local', 'readOnly': True}
    assert all(m['readOnly'] for m in pod['containers'][0]['volumeMounts'])
    assert pod['containers'][0]['securityContext']['capabilities'] == {'drop': ['ALL']}


def test_grep_read_failure_is_not_zero_matches(tmp_path):
    import os
    stage = tmp_path / 'startup-v01627'
    stage.mkdir()
    (stage / 'startup.stdout').write_text('private')
    (stage / 'startup.stderr').write_text('private')
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    grep = binaries / 'grep'
    grep.write_text('#!/bin/sh\necho SENTINEL_READ_ERROR >&2\nexit 2\n')
    grep.chmod(0o755)
    script = (PROBE / 'classify.sh').read_text().replace('/state', str(tmp_path))
    result = subprocess.run(['sh', '-c', script], capture_output=True, text=True,
                            env={**os.environ, 'PATH': str(binaries) + ':' + os.environ['PATH']})
    assert result.returncode != 0
    assert json.loads(result.stdout) == {'diagnostic': 'failed', 'reason': 'log_read_failed'}
    assert 'SENTINEL' not in result.stdout + result.stderr
