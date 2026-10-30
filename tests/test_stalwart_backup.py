from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / 'operations/stalwart-self-service/backup'


def test_backup_grants_only_named_secret_patch_and_keeps_data_off_api():
    docs = list(yaml.safe_load_all((BACKUP / 'resources.yaml').read_text()))
    role = next(d for d in docs if d['kind'] == 'Role')
    assert role['rules'] == [{'apiGroups': [''], 'resources': ['secrets'], 'resourceNames': ['stalwart-migration-backup-key'], 'verbs': ['patch']}]
    secret = next(d for d in docs if d['kind'] == 'Secret')
    assert 'data' not in secret and 'stringData' not in secret
    key_script = (BACKUP / 'key-init.sh').read_text()
    assert '"op":"test"' in key_script and '"value":"pending"' in key_script
    assert '"path":"/immutable","value":true' in key_script
    assert '--data-binary @/work/request.json --output /dev/null' in key_script
    for job in (d for d in docs if d['kind'] == 'Job'):
        assert job['spec']['suspend'] is True
        assert job['spec']['backoffLimit'] == 0
        pod = job['spec']['template']['spec']
        assert pod['nodeSelector'] == {'kubernetes.io/hostname': 'overseas-flk'}
        assert pod['automountServiceAccountToken'] is False
        assert '@sha256:' in pod['containers'][0]['image']
    cold = next(d for d in docs if d['metadata']['name'] == 'stalwart-cold-backup')
    pod = cold['spec']['template']['spec']
    assert 'serviceAccountName' not in pod
    assert 'fsGroup' not in pod['securityContext']  # never chown the source PVC
    volumes = {v['name']: v for v in pod['volumes']}
    assert volumes['source']['persistentVolumeClaim'] == {'claimName': 'stalwart-flk-local-data', 'readOnly': True}
    assert volumes['work']['emptyDir']['medium'] == 'Memory'
    assert not any('projected' in v for v in volumes.values())
    script = (BACKUP / 'archive.sh').read_text()
    assert 'openssl cms -encrypt -aes-256-gcm' in script
    assert 'cmp /work/source.tar /work/restored.tar' in script
    assert script.index('cmp /work/source.tar') < script.index('/backup/baseline/ACCEPTED')
