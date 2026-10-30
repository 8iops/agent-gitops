"""Exercise the acceptance boundary without running a server or touching data."""
from pathlib import Path
import os
import subprocess
import yaml
import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'operations/stalwart-self-service/rehearsal/startup-v2'

@pytest.mark.parametrize('status,shutdown,expected', [('200', 0, 0), ('503', 0, 1), ('302', 0, 1), ('200', 7, 1)])
def test_startup_requires_ready_and_clean_shutdown(tmp_path, status, shutdown, expected):
    ready = status == '200' and shutdown == 0
    state = tmp_path / 'state'
    (state / 'native-v01618-v2').mkdir(parents=True)
    (state / 'native-v01618-v2/ACCEPTED').touch()
    baseline = tmp_path / 'baseline'
    baseline.mkdir()
    database = baseline / 'database'
    database.mkdir()
    (database / 'CURRENT').write_text('MANIFEST-1')
    (database / 'MANIFEST-1').touch()
    working = tmp_path / 'working'
    working.mkdir()
    (working / 'database').mkdir()
    (working / 'database/failed-evidence').write_text('preserve-previous-attempt')
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
    network = tmp_path / 'tcp'
    network.write_text('sl local_address rem_address st\n')
    script = (PROBE / 'startup.sh').read_text().replace('/state', str(state)).replace('/baseline', str(baseline)).replace('/work', str(work)).replace('/var/lib/stalwart', str(working)).replace('/scripts', str(PROBE)).replace('/usr/local/bin/stalwart', str(server)).replace('start + 180', 'start + 2').replace('/proc/net/tcp6', str(network)).replace('/proc/net/tcp', str(network))
    result = subprocess.run(['sh', '-c', script], capture_output=True, text=True, timeout=10,
                            env={**os.environ, 'PATH': str(binaries) + ':' + os.environ['PATH'], 'CONFIG_PATH': '/should-be-unset'})
    assert result.returncode == expected, result.stderr
    assert (working / 'database/failed-evidence').read_text() == 'preserve-previous-attempt'
    assert (database / 'CURRENT').read_text() == 'MANIFEST-1'
    assert (state / 'startup-v01627-v2/ACCEPTED').exists() == ready
    assert ('"normalStartup":"pass"' in result.stdout) == ready
    assert 'MANIFEST' not in result.stdout


def test_startup_preserves_production_and_readonly_baseline():
    job = yaml.safe_load((PROBE / 'job.yaml').read_text())
    assert job['spec']['suspend'] is True
    assert job['spec']['backoffLimit'] == 0
    pod = job['spec']['template']['spec']
    assert pod['automountServiceAccountToken'] is False
    claims = {v['persistentVolumeClaim']['claimName'] for v in pod['volumes'] if 'persistentVolumeClaim' in v}
    assert claims == {'stalwart-rehearsal-source-v01627-local', 'stalwart-rehearsal-migration-state-local', 'stalwart-rehearsal-source-restore-local'}
    assert next(v for v in pod['volumes'] if v['name'] == 'baseline')['persistentVolumeClaim']['readOnly'] is True
    assert job['spec']['activeDeadlineSeconds'] == 600
    assert pod['containers'][0]['securityContext']['capabilities'] == {'drop': ['ALL'], 'add': ['NET_BIND_SERVICE']}
    assert pod['nodeSelector']['kubernetes.io/hostname'] == 'overseas-flk'


def test_network_observation_never_returns_addresses():
    import json
    sample = '  sl local_address rem_address st\n0: 0100007F:01BB 00000000:0000 0A\n1: 0100007F:1F90 00000000:0000 0A\n2: DEADBEEF:4321 CAFEBABE:01BB 02\n'
    result = subprocess.run(['awk', '-f', str(PROBE / 'network.awk')], input=sample, capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {'listen443': 1, 'listen8080': 1, 'synSent': 1}
    assert 'DEADBEEF' not in result.stdout and 'CAFEBABE' not in result.stdout


def test_http_observation_only_numeric_codes():
    import json
    result = subprocess.run(['awk', '-f', str(PROBE / 'http.awk')], input='000\n302\n200\nSENTINEL_PRIVATE\n', capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == {'000': 1, '302': 1, '200': 1}
