from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_rehearsal_resources_cannot_mount_or_route_production():
    docs = list(yaml.safe_load_all((ROOT / 'operations/stalwart-self-service/rehearsal/resources.yaml').read_text()))
    assert {d['kind'] for d in docs} == {'NetworkPolicy', 'PersistentVolumeClaim'}
    assert all(d['metadata']['namespace'] == 'mail-system' for d in docs)
    claims = [d for d in docs if d['kind'] == 'PersistentVolumeClaim']
    assert len(claims) == 5
    assert sum(int(d['spec']['resources']['requests']['storage'][:-2]) for d in claims) == 9
    assert all(d['spec']['storageClassName'] == 'local-path' and 'dataSource' not in d['spec'] and 'volumeName' not in d['spec'] for d in claims)
    policy = next(d['spec'] for d in docs if d['kind'] == 'NetworkPolicy')
    assert policy == {'podSelector': {'matchLabels': {'re8ch.com/stalwart-rehearsal': 'true'}}, 'policyTypes': ['Ingress', 'Egress'], 'ingress': [], 'egress': []}
    root = yaml.safe_load((ROOT / 'clusters/re8ch/kustomization.yaml').read_text())
    assert all('rehearsal' not in path for path in root['resources'])


def test_workers_are_suspended_pinned_and_rehearsal_only():
    docs = list(yaml.safe_load_all((ROOT / 'operations/stalwart-self-service/rehearsal/workers.yaml').read_text()))
    jobs = [d for d in docs if d['kind'] == 'Job']
    assert len(jobs) == 5
    for job in jobs:
        assert job['metadata']['namespace'] == 'mail-system'
        assert job['spec']['suspend'] is True
        assert job['spec']['backoffLimit'] == 0
        pod = job['spec']['template']['spec']
        assert pod['nodeSelector'] == {'kubernetes.io/hostname': 'overseas-flk'}
        assert pod['containers'][0]['resources']['limits']['memory'] == '1536Mi'
        assert pod['automountServiceAccountToken'] is False
        assert '@sha256:' in pod['containers'][0]['image']
        assert all(v.get('persistentVolumeClaim', {}).get('claimName') not in ['stalwart-flk-local-data', 'stalwart-rehearsal-source-restore-local'] for v in pod['volumes'])
        source = next(v for v in pod['volumes'] if v['name'] == 'source')
        assert source['persistentVolumeClaim']['readOnly'] is True
        assert not any(a in ['--allow-errors', '--allow-mass-removal', '--force-after-final'] for a in pod['containers'][0]['args'])


def test_worker_arguments_bind_the_expected_stores_and_full_verification():
    docs = list(yaml.safe_load_all((ROOT / 'operations/stalwart-self-service/rehearsal/workers.yaml').read_text()))
    expected = {
        'prepare': ['prepare', '--non-interactive'],
        'run': ['run'],
        'final': ['run', '--final', '--yes'],
        'verify': ['verify', '--full'],
        'rollback': ['rollback', '--verify-full', '--yes'],
    }
    for job in (d for d in docs if d['kind'] == 'Job'):
        phase = job['metadata']['name'].removeprefix('stalwart-rehearsal-migrate-').removesuffix('-local')
        pod = job['spec']['template']['spec']
        args = expected[phase] + ['--source', '/config/target.json' if phase == 'rollback' else '/config/source.json']
        if phase != 'prepare':
            args += ['--target', '/config/rollback.json' if phase == 'rollback' else '/config/target.json']
        args += ['--state', '/state/rollback' if phase == 'rollback' else '/state/forward']
        if phase == 'rollback':
            args += ['--forward-state', '/state/forward']
        assert pod['containers'][0]['args'] == args
        claims = {v['name']: v['persistentVolumeClaim'] for v in pod['volumes'] if 'persistentVolumeClaim' in v}
        assert claims['source'] == {'claimName': 'stalwart-rehearsal-source-v01627-local', 'readOnly': True}
        assert claims['target'] == {'claimName': 'stalwart-rehearsal-target-v1-local', 'readOnly': phase in ['verify', 'rollback']}
        assert claims['state'] == {'claimName': 'stalwart-rehearsal-migration-state-local', 'readOnly': False}
        assert set(claims) == ({'source', 'target', 'state', 'rollback'} if phase == 'rollback' else {'source', 'target', 'state'})


def test_restore_uses_only_accepted_backup_and_distinct_baseline():
    job = yaml.safe_load((ROOT / 'operations/stalwart-self-service/rehearsal/restore-job.yaml').read_text())
    assert job['metadata']['namespace'] == 'mail-system'
    assert job['spec']['suspend'] is True
    pod = job['spec']['template']['spec']
    assert pod['automountServiceAccountToken'] is False
    volumes = {v['name']: v for v in pod['volumes']}
    assert volumes['backup']['persistentVolumeClaim'] == {'claimName': 'stalwart-migration-backup-overseas', 'readOnly': True}
    assert volumes['restore']['persistentVolumeClaim']['claimName'] == 'stalwart-rehearsal-source-restore-local'
    assert all(v.get('persistentVolumeClaim', {}).get('claimName') != 'stalwart-flk-local-data' for v in volumes.values())
    script = (ROOT / 'operations/stalwart-self-service/rehearsal/restore.sh').read_text()
    assert script.index('[ "$actual_plain" = "$expected_plain" ]') < script.index('tar --no-same-owner')
