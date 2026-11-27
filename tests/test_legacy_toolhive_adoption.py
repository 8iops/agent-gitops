from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ADOPTION = ROOT / "clusters/re8ch/legacy-toolhive-adoption.yaml"

EXPECTED = {
    *(f"VirtualMCPServer/{name}" for name in ("re8ch-admin-vmcp", "re8ch-operate-vmcp", "re8ch-tools-vmcp", "tenant-vmcp")),
    *(f"MCPOIDCConfig/{name}" for name in (
        "admin-workload-identity", "external-admin-oidc", "external-observe-oidc",
        "external-operate-oidc", "observe-workload-identity", "operate-workload-identity",
        "re8ch-admin-vmcp-issuer", "re8ch-operate-vmcp-issuer",
        "re8ch-tools-vmcp-issuer", "tenant-vmcp-issuer",
    )),
    *(f"MCPServerEntry/{name}" for name in (
        "admin-api-backend", "ops-admin-vmcp-backend",
        "ops-observe-vmcp-backend", "ops-operate-vmcp-backend",
    )),
    *(f"MCPGroup/{name}" for name in ("platform-admin", "platform-observe", "platform-operate")),
    "MCPToolConfig/ops-observe-tools",
    "MCPExternalAuthConfig/admin-vmcp-backend-auth",
    "MCPExternalAuthConfig/vmcp-internal-backend",
}


def test_legacy_toolhive_adoption_is_exact_and_status_free():
    objects = list(yaml.safe_load_all(ADOPTION.read_text()))
    assert {f"{obj['kind']}/{obj['metadata']['name']}" for obj in objects} == EXPECTED
    assert all(obj["metadata"]["namespace"] == "toolhive-system" for obj in objects)
    assert all(obj["metadata"]["labels"]["delivery.re8ch.com/retirement-phase"] == "adoption" for obj in objects)
    assert all("status" not in obj for obj in objects)


def test_current_native_publication_is_not_adopted_for_retirement():
    assert EXPECTED.isdisjoint({
        "VirtualMCPServer/re8ch-native",
        "MCPOIDCConfig/re8ch-native-issuer",
        "MCPServerEntry/tenant-api-backend",
        "MCPGroup/tenant-public",
        "MCPServer/cloud-disk-mcp",
        "MCPServer/stalwart-agent-tools-shadow",
    })


def test_mcp_server_entries_enter_the_bounded_release_and_rbac():
    contract = yaml.safe_load((ROOT / "contracts/agent-runtime-domain-toolhive-system.yaml").read_text())
    assert "toolhive.stacklok.dev/MCPServerEntry" in contract["spec"]["authorization"]["resources"]

    access = list(yaml.safe_load_all((ROOT / "operations/releases/domain-access.yaml").read_text()))
    role = next(obj for obj in access if obj.get("kind") == "Role" and obj["metadata"]["name"] == "agent-runtime-domain-toolhive-system")
    rule = next(item for item in role["rules"] if item["resources"] == ["mcpserverentries"])
    assert set(rule["resourceNames"]) == {
        "admin-api-backend",
        "ops-admin-vmcp-backend",
        "ops-observe-vmcp-backend",
        "ops-operate-vmcp-backend",
    }
