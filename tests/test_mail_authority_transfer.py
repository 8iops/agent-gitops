import hashlib
import json
import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_mail_transfer_preserves_exact_accepted_objects_and_manager():
    transfer = json.loads((ROOT / 'operations/releases/authority-transfers.json').read_text())['mail-system']
    source = (ROOT / transfer['sourcePath']).read_bytes()
    assert 'sha256:' + hashlib.sha256(source).hexdigest() == transfer['sourceDigest']
    original = list(yaml.safe_load_all(source))
    target = list(yaml.safe_load_all((ROOT / 'releases/agent-runtime-domain-mail-system/resources.yaml').read_text()))
    expected = copy.deepcopy(original)
    webmail = next(obj for obj in expected if obj['kind'] == 'Deployment' and obj['metadata']['name'] == 'stalwart-webmail')
    env = webmail['spec']['template']['spec']['containers'][0]['env']
    env.insert(0, env.pop(next(i for i, item in enumerate(env) if item['name'] == 'OAUTH_ONLY')))
    env.insert(1, {'name': 'SESSION_SECRET', 'valueFrom': {'secretKeyRef': {
        'name': 'stalwart-webmail-session', 'key': 'session-secret'}}})
    # Reviewed post-transfer change: keep SSO and expose app-password login.
    next(item for item in env if item['name'] == 'OAUTH_ONLY')['value'] = 'false'
    # Reviewed post-transfer contract correction: use authenticated DAV discovery,
    # not a mailbox local part that may refer to a different provider account.
    discovery = yaml.safe_load((ROOT / 'clusters/re8ch/stalwart-client-discovery-patch.yaml').read_text())
    access = next(obj for obj in expected if obj['kind'] == 'ConfigMap' and obj['metadata']['name'] == 'stalwart-bot-access-contract')
    access['data'].update(discovery['data'])
    assert target == expected
    assert len(target) == 45
    assert not {'Secret', 'Role', 'RoleBinding', 'Job'} & {obj['kind'] for obj in target}
    contract = yaml.safe_load((ROOT / 'contracts/agent-runtime-domain-mail-system.yaml').read_text())['spec']
    assert contract['authorization']['fieldManager'] == 're8ch-release/identity-access-domain-mail-system'
    assert contract['authorization']['requireExisting'] is True
    assert contract['authorization']['forceConflictObjects'] == ['apps/Deployment/mail-system/stalwart-webmail']
    assert contract['lifecycle']['prune'] is False


def test_collaboration_contract_uses_provider_discovery_without_new_authority():
    documents = list(yaml.safe_load_all((ROOT / 'releases/agent-runtime-domain-mail-system/resources.yaml').read_text()))
    data = next(obj['data'] for obj in documents if obj['kind'] == 'ConfigMap' and obj['metadata']['name'] == 'stalwart-bot-access-contract')
    assert data['caldav'] == data['baseUrl'] + '/.well-known/caldav'
    assert data['carddav'] == data['baseUrl'] + '/.well-known/carddav'
    assert data['webdav'] == data['baseUrl'] + '/dav/file/{account}'
    assert all('email-local-part' not in value for value in data.values())
    assert 'cross-origin' in data['discoveryContract']
    # This patch is an existing ConfigMap contract correction, not a new
    # workload, token, credential provisioning mechanism or public listener.
    patch = yaml.safe_load((ROOT / 'clusters/re8ch/stalwart-client-discovery-patch.yaml').read_text())
    assert set(patch) == {'apiVersion', 'kind', 'metadata', 'data'}
    assert patch['kind'] == 'ConfigMap'
    assert set(patch['data']) == {'caldav', 'carddav', 'webdav', 'accountContract', 'discoveryContract'}
