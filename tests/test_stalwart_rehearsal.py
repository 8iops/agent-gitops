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
