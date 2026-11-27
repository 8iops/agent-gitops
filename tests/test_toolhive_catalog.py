import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_toolhive_catalog_uses_canonical_openoauth_resource():
    documents = yaml.safe_load_all((ROOT / "clusters/re8ch/resources.yaml").read_text())
    catalog = next(
        document
        for document in documents
        if document
        and document.get("kind") == "ConfigMap"
        and document.get("metadata", {}).get("name") == "re8ch-approved-tool-catalog"
    )
    registry = json.loads(catalog["data"]["registry.json"])

    assert registry["data"]["servers"][0]["remotes"] == [{
        "type": "streamable-http",
        "url": "https://tools.service.re8ch.com/tenant-native/mcp",
    }]


def test_native_toolhive_instance_matches_pg_identity_oauth_chain():
    documents = [item for item in yaml.safe_load_all((ROOT / "clusters/re8ch/resources.yaml").read_text()) if item]
    by_identity = {(item["kind"], item["metadata"]["name"]): item for item in documents}
    group = by_identity[("MCPGroup", "tenant-public")]
    issuer = by_identity[("MCPOIDCConfig", "re8ch-native-issuer")]
    native = by_identity[("VirtualMCPServer", "re8ch-native")]

    assert group["metadata"]["namespace"] == "toolhive-system"
    assert issuer["spec"]["inline"] == {
        "issuer": "https://db-rw.re8ch.com/auth/v1",
        "clientId": "2981225a-da08-5aaa-9e84-8fd151696113",
        "jwksAllowPrivateIP": True,
    }
    oidc = native["spec"]["incomingAuth"]["oidcConfigRef"]
    assert oidc["name"] == "re8ch-native-issuer"
    assert oidc["audience"] == issuer["spec"]["inline"]["clientId"]
    assert oidc["resourceUrl"] == "https://tools.service.re8ch.com/tenant-native/mcp"
    assert native["spec"]["config"]["aggregation"]["tools"] == [{"workload": "tenant-api-backend"}]
    assert native["spec"]["outgoingAuth"]["default"]["externalAuthConfigRef"]["name"] == "tenant-vmcp-backend-auth"


def test_toolhive_release_can_create_only_reviewed_native_crs():
    contract = yaml.safe_load((ROOT / "contracts/agent-runtime-domain-toolhive-system.yaml").read_text())
    assert contract["spec"]["authorization"]["requireExisting"] is False
    assert {"tenant-public", "re8ch-native-issuer", "re8ch-native"}.issubset(
        contract["spec"]["authorization"]["objectNames"]
    )
    access = [item for item in yaml.safe_load_all((ROOT / "operations/releases/domain-access.yaml").read_text()) if item]
    role = next(item for item in access if item["kind"] == "Role" and item["metadata"]["name"] == "agent-runtime-domain-toolhive-system")
    create_rules = [rule for rule in role["rules"] if "create" in rule["verbs"]]
    assert {rule["resources"][0] for rule in create_rules} == {"mcpgroups", "mcpoidcconfigs", "virtualmcpservers"}
