import json
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
PATCH = ROOT / "clusters/re8ch/tenant-api-current-runtime-patch.yaml"


def test_tenant_api_uses_reviewed_image_and_runtime_discovery_registry():
    deployment, config = list(yaml.safe_load_all(PATCH.read_text()))
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container == {
        "name": "runtime",
        "image": "ghcr.io/re8ch/service-backend-tenant-mcp@sha256:9627dec87e6f4217693dae060b6324fa1481bddc612faca984c3fba9ee427ecb",
    }

    registry = json.loads(config["data"]["modules.json"])
    assert set(registry["backends"]) == {
        "grafana", "native", "pg_billing", "pg_identity", "pg_re8ch", "ssh", "tenant_admin",
    }
    assert all("allowed" not in backend for backend in registry["backends"].values())
    assert not {"cloud", "infra", "admin"} & set(registry["backends"])
