import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_mail_transfer_preserves_exact_accepted_objects_and_manager():
    transfer = json.loads((ROOT / 'operations/releases/authority-transfers.json').read_text())['mail-system']
    source = (ROOT / transfer['sourcePath']).read_bytes()
    assert 'sha256:' + hashlib.sha256(source).hexdigest() == transfer['sourceDigest']
    original = list(yaml.safe_load_all(source))
    target = list(yaml.safe_load_all((ROOT / 'releases/agent-runtime-domain-mail-system/resources.yaml').read_text()))
    assert target == original
    assert len(target) == 45
    assert not {'Secret', 'Role', 'RoleBinding', 'Job'} & {obj['kind'] for obj in target}
    contract = yaml.safe_load((ROOT / 'contracts/agent-runtime-domain-mail-system.yaml').read_text())['spec']
    assert contract['authorization']['fieldManager'] == 're8ch-release/identity-access-domain-mail-system'
    assert contract['authorization']['requireExisting'] is True
    assert contract['authorization']['forceConflictObjects'] == []
    assert contract['lifecycle']['prune'] is False
