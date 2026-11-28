import json
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
PATCH = ROOT / "clusters/re8ch/tenant-service-api-current-runtime-patch.yaml"
EXACT = ROOT / "releases/agent-runtime-exact-tenant-service-api-manager/tenant-service-api.yaml"


def test_tenant_service_api_uses_reviewed_image_and_runtime_discovery_registry():
    config = yaml.safe_load(PATCH.read_text())
    deployment = next(
        item for item in yaml.safe_load_all(EXACT.read_text())
        if item and item.get("kind") == "Deployment" and item["metadata"]["name"] == "tenant-service-api"
    )
    container = next(
        item for item in deployment["spec"]["template"]["spec"]["containers"]
        if item["name"] == "runtime"
    )
    assert "imagePullSecrets" not in deployment["spec"]["template"]["spec"]
    assert container["image"] == "ghcr.io/re8ch/service-backend-tenant-mcp@sha256:9627dec87e6f4217693dae060b6324fa1481bddc612faca984c3fba9ee427ecb"
    release = next(item for item in container["env"] if item["name"] == "SENTRY_RELEASE")
    assert release["value"] == "tenant-mcp@296a404a14f6556a30553be9e8b14e88f40d1c0c"
    assert not any(item["name"] == "MCP_CATALOG_DATABASE_URL" for item in container["env"])

    registry = json.loads(config["data"]["modules.json"])
    assert set(registry["backends"]) == {
        "grafana", "native", "pg_billing", "pg_identity", "pg_re8ch", "ssh", "tenant_admin",
    }
    assert all("allowed" not in backend for backend in registry["backends"].values())
    assert not {"cloud", "infra", "admin"} & set(registry["backends"])
