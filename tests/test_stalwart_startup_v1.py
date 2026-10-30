from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parents[1] / 'operations/stalwart-self-service/rehearsal/startup-v1'


def test_v1_startup_is_isolated_and_stopped_after_loopback_probe():
    job = yaml.safe_load((BASE / 'job.yaml').read_text())
    pod = job['spec']['template']['spec']
    assert job['spec']['suspend'] is True
    assert pod['automountServiceAccountToken'] is False
    assert pod.get('hostNetwork') is not True
    claims = {v['name']: v['persistentVolumeClaim']['claimName'] for v in pod['volumes'] if 'persistentVolumeClaim' in v}
    assert claims == {'target': 'stalwart-rehearsal-target-v1-local',
                      'state': 'stalwart-rehearsal-migration-state-local'}
    image = pod['containers'][0]['image']
    assert image.startswith('ghcr.io/stalwartlabs/stalwart:v1.0.1@sha256:')
    script = (BASE / 'startup.sh').read_text()
    assert 'post-final-full-verify-v1/native-exit' in script
    assert '--config /work/config.json' in script
    assert '127.0.0.1:443/healthz/ready' in script
    assert 'kill -TERM "$server_pid"' in script
