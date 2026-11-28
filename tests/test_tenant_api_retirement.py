import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/agent-runtime-exact-tenant-service-api-manager.yaml"
RELEASE = ROOT / "releases/agent-runtime-exact-tenant-service-api-manager"


def documents(path):
    return [item for item in yaml.safe_load_all(path.read_text()) if item]


def test_legacy_tenant_api_runtime_is_only_in_the_reviewed_retirement_set():
    retirement = yaml.safe_load(
        (ROOT / "contracts/agent-runtime-exact-tenant-api-manager.yaml").read_text()
    )
    assert retirement["spec"]["authorization"]["objectNames"] == [
        "ssa-state-agent-runtime-exact-tenant-api-manager"
    ]
    assert retirement["spec"]["lifecycle"]["deletionAllowlist"] == [
        "apps/Deployment/tenant-infrastructure/tenant-api"
    ]
    scheduled = yaml.safe_load(
        (ROOT / "operations/releases/scheduled-reconcile.yaml").read_text()
    )["spec"]["releases"]
    assert "agent-runtime-exact-tenant-api-manager" not in scheduled
    retirements = set(json.loads(
        (ROOT / "operations/releases/retirements.json").read_text()
    )["tenant-infrastructure"])
    assert retirements == {
        "apps/Deployment/tenant-infrastructure/tenant-api",
        "cilium.io/CiliumNetworkPolicy/tenant-infrastructure/tenant-api-gateway",
        "core/Service/tenant-infrastructure/tenant-api",
        "core/Service/tenant-infrastructure/tenant-infrastructure",
        "core/ServiceAccount/tenant-infrastructure/tenant-api",
        "networking.k8s.io/NetworkPolicy/tenant-infrastructure/tenant-api",
    }


def test_non_mcp_surfaces_have_an_independent_create_capable_release():
    contract = yaml.safe_load(CONTRACT.read_text())["spec"]
    assert contract["authorization"]["requireExisting"] is False
    assert contract["lifecycle"]["prune"] is True
    rendered = documents(RELEASE / "public-surfaces.yaml")
    names = {item["metadata"]["name"] for item in rendered}
    assert names == {
        "tenant-service-api",
        "tenant-service-api-gateway",
    }
    serialized = yaml.safe_dump_all(rendered)
    assert "/tenant-self-service/mcp" not in serialized
    assert "tenant-api" not in names


def test_domain_prunes_legacy_runtime_without_owning_the_replacement():
    contract = yaml.safe_load(
        (ROOT / "contracts/agent-runtime-domain-tenant-infrastructure.yaml").read_text()
    )["spec"]
    assert contract["lifecycle"]["prune"] is True
    assert set(contract["lifecycle"]["deletionAllowlist"]) == set(json.loads(
        (ROOT / "operations/releases/retirements.json").read_text()
    )["tenant-infrastructure"])
    assert "tenant-service-api" not in contract["authorization"]["objectNames"]
    assert {
        "tenant-billing-auth-center",
        "tenant-billing-read",
        "tenant-credential-redemption",
        "tenant-native-mcp",
        "tenant-self-service-capabilities",
    } <= set(contract["authorization"]["objectNames"])
