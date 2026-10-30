from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_rehearsal_resources_cannot_mount_or_route_production():
    docs = list(yaml.safe_load_all((ROOT / 'operations/stalwart-self-service/rehearsal/resources.yaml').read_text()))
    assert {d['kind'] for d in docs} == {'Namespace', 'ResourceQuota', 'NetworkPolicy', 'PersistentVolumeClaim'}
    assert all(d['metadata'].get('namespace', 'stalwart-migration-rehearsal') == 'stalwart-migration-rehearsal' for d in docs)
    claims = [d for d in docs if d['kind'] == 'PersistentVolumeClaim']
    assert len(claims) == 5
    assert sum(int(d['spec']['resources']['requests']['storage'][:-2]) for d in claims) == 17
    assert all(d['spec']['storageClassName'] == 'rbd-r640' and 'dataSource' not in d['spec'] and 'volumeName' not in d['spec'] for d in claims)
    policy = next(d['spec'] for d in docs if d['kind'] == 'NetworkPolicy')
    assert policy == {'podSelector': {}, 'policyTypes': ['Ingress', 'Egress'], 'ingress': [], 'egress': []}
    root = yaml.safe_load((ROOT / 'clusters/re8ch/kustomization.yaml').read_text())
    assert all('rehearsal' not in path for path in root['resources'])


def test_workers_are_suspended_pinned_and_rehearsal_only():
    docs = list(yaml.safe_load_all((ROOT / 'operations/stalwart-self-service/rehearsal/workers.yaml').read_text()))
    jobs = [d for d in docs if d['kind'] == 'Job']
    assert len(jobs) == 5
    for job in jobs:
        assert job['metadata']['namespace'] == 'stalwart-migration-rehearsal'
        assert job['spec']['suspend'] is True
        assert job['spec']['backoffLimit'] == 0
        pod = job['spec']['template']['spec']
        assert pod['automountServiceAccountToken'] is False
        assert '@sha256:' in pod['containers'][0]['image']
        assert all(v.get('persistentVolumeClaim', {}).get('claimName') not in ['stalwart-flk-local-data', 'source-restore'] for v in pod['volumes'])
        source = next(v for v in pod['volumes'] if v['name'] == 'source')
        assert source['persistentVolumeClaim']['readOnly'] is True
        assert not any(a in ['--allow-errors', '--allow-mass-removal', '--force-after-final'] for a in pod['containers'][0]['args'])
