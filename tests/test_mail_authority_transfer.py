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
    # Reviewed production migration phase: start the verified v1 target after
    # the official converter completed and the marker was written.
    source_upgrade = yaml.safe_load((ROOT / 'clusters/re8ch/stalwart-v01627-production-patch.yaml').read_text())
    stalwart = next(obj for obj in expected if obj['kind'] == 'StatefulSet' and obj['metadata']['name'] == 'stalwart-flk')
    stalwart['spec']['replicas'] = source_upgrade['spec']['replicas']
    stalwart['spec']['template']['metadata']['annotations'].update(
        source_upgrade['spec']['template']['metadata']['annotations'])
    stalwart['spec']['template']['spec']['containers'][0]['image'] = (
        source_upgrade['spec']['template']['spec']['containers'][0]['image'])
    next(item for item in stalwart['spec']['template']['spec']['initContainers']
         if item['name'] == 'wait-for-migration')['args'] = (
             source_upgrade['spec']['template']['spec']['initContainers'][0]['args'])
    volumes = stalwart['spec']['template']['spec']['volumes']
    data_index = next(i for i, item in enumerate(volumes) if item['name'] == 'data')
    data_volume = volumes.pop(data_index)
    data_volume['persistentVolumeClaim'] = (
        source_upgrade['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim'])
    volumes.insert(0, data_volume)
    config_patch = yaml.safe_load((ROOT / 'clusters/re8ch/stalwart-v1-config-patch.yaml').read_text())
    config = next(obj for obj in expected if obj['kind'] == 'ConfigMap' and obj['metadata']['name'] == 'stalwart-config')
    config['data'].update(config_patch['data'])
    for patch_name in (
        'stalwart-unified-identity-trust-patch.yaml',
        'stalwart-userhub-trust-patch.yaml',
    ):
        trust_patch = yaml.safe_load((ROOT / 'clusters/re8ch' / patch_name).read_text())
        trust_config = next(
            obj for obj in expected
            if obj['kind'] == 'ConfigMap'
            and obj['metadata']['name'] == trust_patch['metadata']['name']
        )
        trust_config['data'].update(trust_patch['data'])
    device_route_patch = yaml.safe_load((ROOT / 'clusters/re8ch/stalwart-device-route-patch.yaml').read_text())
    assert device_route_patch == [{
        'op': 'add',
        'path': '/spec/rules/1/matches/3',
        'value': {'path': {'type': 'PathPrefix', 'value': '/device'}},
    }]
    route = next(obj for obj in expected if obj['kind'] == 'HTTPRoute' and obj['metadata']['name'] == 'stalwart-idp-public')
    route['spec']['rules'][1]['matches'].insert(3, device_route_patch[0]['value'])
    assert target == expected
    assert stalwart['spec']['replicas'] == 1
    assert 'v1.0.1@sha256:' in stalwart['spec']['template']['spec']['containers'][0]['image']
    assert config['data']['config.json'] == '{"@type":"RocksDb","path":"/var/lib/stalwart/database"}'
    for name in ('stalwart-unified-identity-bootstrap-plan-v2', 'stalwart-userhub-oauth-plan-v1'):
        plan = next(obj for obj in target if obj['kind'] == 'ConfigMap' and obj['metadata']['name'] == name)['data']['plan.ndjson']
        assert '"issuerUrl":"https://auth.re8ch.com"' in plan
        assert '"requireAudience":"stalwart-webui"' in plan
        assert 'https://db-rw.re8ch.com/auth/v1' not in plan
    assert len(target) == 45
    assert not {'Secret', 'Role', 'RoleBinding', 'Job'} & {obj['kind'] for obj in target}
    contract = yaml.safe_load((ROOT / 'contracts/agent-runtime-domain-mail-system.yaml').read_text())['spec']
    assert contract['authorization']['fieldManager'] == 're8ch-release/identity-access-domain-mail-system'
    assert contract['authorization']['requireExisting'] is True
    assert contract['authorization']['forceConflictObjects'] == [
        'apps/Deployment/mail-system/stalwart-webmail',
        'apps/StatefulSet/mail-system/stalwart-flk',
        'core/ConfigMap/mail-system/stalwart-bot-access-contract',
        'core/ConfigMap/mail-system/stalwart-config',
    ]
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
