"""Availability boundary for optional Admin GitHub capability credentials."""
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'releases/agent-runtime-exact-tenant-api-manager'


def runtime():
    documents = yaml.safe_load_all(subprocess.check_output(
        ['kubectl', 'kustomize', str(SOURCE)], text=True))
    deployment = next(item for item in documents
                      if item['kind'] == 'Deployment' and item['metadata']['name'] == 'tenant-api')
    return next(container for container in deployment['spec']['template']['spec']['containers']
                if container['name'] == 'runtime')


def test_unprovisioned_additional_capabilities_do_not_block_the_shared_login_runtime():
    env = {item['name']: item for item in runtime()['env']}
    roles = {'DELIVERY': 'delivery', 'SECURITY': 'security',
             'COLLABORATION': 'collaboration', 'DEVELOPER_AI': 'developer-ai',
             'IDENTITY': 'identity', 'BILLING': 'billing'}
    for variable, role in roles.items():
        for suffix, key in [('APP_ID', 'app-id'), ('PRIVATE_KEY', 'private-key')]:
            ref = env[f'GITHUB_{variable}_{suffix}']['valueFrom']['secretKeyRef']
            assert ref == {'name': f'github-enterprise-{role}-app', 'key': key, 'optional': True}


def test_primary_governance_and_claim_credentials_remain_required():
    container = runtime()
    env = {item['name']: item for item in container['env']}
    for variable in ['GITHUB_GOVERNANCE_APP_ID', 'GITHUB_GOVERNANCE_PRIVATE_KEY']:
        ref = env[variable]['valueFrom']['secretKeyRef']
        assert ref['name'] == 'github-enterprise-governance-app'
        assert ref.get('optional', False) is False
    claim = next(item['secretRef'] for item in container['envFrom']
                 if item.get('secretRef', {}).get('name') == 'tenant-claim-internal-auth')
    assert claim.get('optional', False) is False
