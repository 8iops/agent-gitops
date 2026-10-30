"""Exercise the acceptance boundary without running a server or touching data."""
from pathlib import Path
import os
import subprocess
import yaml
import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'operations/stalwart-self-service/rehearsal/startup-v01627'

@pytest.mark.parametrize('status,shutdown,expected', [('200', 0, 0), ('503', 0, 1), ('302', 0, 1), ('200', 7, 1)])
def test_startup_requires_ready_and_clean_shutdown(tmp_path, status, shutdown, expected):
    ready = status == '200' and shutdown == 0
    state = tmp_path / 'state'
    (state / 'native-v01618-v2').mkdir(parents=True)
    (state / 'native-v01618-v2/ACCEPTED').touch()
    database = tmp_path / 'database'
    database.mkdir()
    (database / 'CURRENT').write_text('MANIFEST-1')
    (database / 'MANIFEST-1').touch()
    work = tmp_path / 'work'
    work.mkdir()
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    server = binaries / 'stalwart'
    server.write_text(f'#!/bin/sh\ntrap "exit {shutdown}" TERM\nwhile :; do sleep 0.05; done\n')
    server.chmod(0o755)
    curl = binaries / 'curl'
    curl.write_text('#!/bin/sh\nsleep 0.1\nprintf ' + status + '\nexit 0\n')
    curl.chmod(0o755)
    script = (PROBE / 'startup.sh').read_text().replace('/state', str(state)).replace('/var/lib/stalwart/database', str(database)).replace('/work', str(work)).replace('/usr/local/bin/stalwart', str(server)).replace('"$attempt" -lt 60', '"$attempt" -lt 2')
    result = subprocess.run(['sh', '-c', script], capture_output=True, text=True, timeout=10,
                            env={**os.environ, 'PATH': str(binaries) + ':' + os.environ['PATH'], 'CONFIG_PATH': '/should-be-unset'})
    assert result.returncode == expected, result.stderr
    assert (state / 'startup-v01627/ACCEPTED').exists() == ready
    assert ('"normalStartup":"pass"' in result.stdout) == ready
    assert 'MANIFEST' not in result.stdout


def test_startup_cannot_mount_production_or_baseline():
    job = yaml.safe_load((PROBE / 'job.yaml').read_text())
    assert job['spec']['suspend'] is True
    assert job['spec']['backoffLimit'] == 0
    pod = job['spec']['template']['spec']
    assert pod['automountServiceAccountToken'] is False
    claims = {v['persistentVolumeClaim']['claimName'] for v in pod['volumes'] if 'persistentVolumeClaim' in v}
    assert claims == {'stalwart-rehearsal-source-v01627-local', 'stalwart-rehearsal-migration-state-local'}
    assert pod['containers'][0]['securityContext']['capabilities'] == {'drop': ['ALL'], 'add': ['NET_BIND_SERVICE']}
    assert pod['nodeSelector']['kubernetes.io/hostname'] == 'overseas-flk'
