import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RETIREMENTS = json.loads((ROOT / "operations/releases/retirements.json").read_text())["toolhive-system"]


def test_legacy_toolhive_retirement_is_exact_and_excludes_current_tools():
    assert len(RETIREMENTS) == 24
    assert len(set(RETIREMENTS)) == len(RETIREMENTS)
    assert not any(name.endswith(suffix) for name in RETIREMENTS for suffix in (
        "/re8ch-native", "/re8ch-native-issuer", "/tenant-api-backend",
        "/tenant-public", "/cloud-disk-mcp", "/stalwart-agent-tools-shadow",
    ))


def test_contract_prunes_only_the_reviewed_retirement_set():
    contract = yaml.safe_load((ROOT / "contracts/agent-runtime-domain-toolhive-system.yaml").read_text())
    lifecycle = contract["spec"]["lifecycle"]
    assert lifecycle["prune"] is True
    assert lifecycle["deletionAllowlist"] == sorted(RETIREMENTS)


def test_generated_role_has_exact_delete_permissions():
    access = list(yaml.safe_load_all((ROOT / "operations/releases/domain-access.yaml").read_text()))
    role = next(obj for obj in access if obj.get("kind") == "Role" and obj["metadata"]["name"] == "agent-runtime-domain-toolhive-system")
    delete_rules = [rule for rule in role["rules"] if rule["verbs"] == ["get", "delete"]]
    actual = {
        f"{rule['apiGroups'][0]}/{resource}/{name}"
        for rule in delete_rules
        for resource in rule["resources"]
        for name in rule["resourceNames"]
    }
    expected = set()
    plural = json.loads((ROOT / "operations/releases/resource-types.json").read_text())
    for identity in RETIREMENTS:
        api, kind, namespace, name = identity.split("/", 3)
        assert namespace == "toolhive-system"
        expected.add(f"{api}/{plural[f'{api}/{kind}']}/{name}")
    assert actual == expected
