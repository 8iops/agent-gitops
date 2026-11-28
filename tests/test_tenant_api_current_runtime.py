import json
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
PATCH = ROOT / "clusters/re8ch/tenant-api-current-runtime-patch.yaml"
EXACT = ROOT / "releases/agent-runtime-exact-tenant-api-manager/tenant-api.yaml"


def test_tenant_api_uses_reviewed_image_and_runtime_discovery_registry():
    config = yaml.safe_load(PATCH.read_text())
    deployment = next(
        item for item in yaml.safe_load_all(EXACT.read_text())
        if item and item.get("kind") == "Deployment" and item["metadata"]["name"] == "tenant-api"
    )
    container = next(
        item for item in deployment["spec"]["template"]["spec"]["containers"]
        if item["name"] == "runtime"
    )
    assert container["image"] == "ghcr.io/re8ch/service-backend-tenant-mcp@sha256:95d4b7924153cb4cf68a17c4eac094ac4c5370af95f28250693316e3c59b99bb"
    catalog_database = next(item for item in container["env"] if item["name"] == "MCP_CATALOG_DATABASE_URL")
    assert catalog_database["valueFrom"]["secretKeyRef"] == {
        "name": "mcp-catalog-database",
        "key": "MCP_CATALOG_DATABASE_URL",
        "optional": False,
    }

    registry = json.loads(config["data"]["modules.json"])
    assert set(registry["backends"]) == {
        "grafana", "native", "pg_billing", "pg_identity", "pg_re8ch", "ssh", "tenant_admin",
    }
    assert all("allowed" not in backend for backend in registry["backends"].values())
    assert not {"cloud", "infra", "admin"} & set(registry["backends"])
