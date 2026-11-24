from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "clusters/re8ch/tenant-runtime-authority-resources.yaml"
EXACT = ROOT / "releases/agent-runtime-exact-tenant-api-manager/tenant-api.yaml"


def tenant_runtime_environment(path):
    deployment = next(
        item
        for item in yaml.safe_load_all(path.read_text())
        if item and item.get("kind") == "Deployment" and item["metadata"]["name"] == "tenant-api"
    )
    runtime = next(item for item in deployment["spec"]["template"]["spec"]["containers"] if item["name"] == "runtime")
    return runtime, {item["name"]: item.get("value") for item in runtime["env"]}


def test_tenant_stalwart_uses_publicedge_and_reviewed_oauth():
    for path in (SOURCE, EXACT):
        runtime, env = tenant_runtime_environment(path)
        assert runtime["image"] == "ghcr.io/re8ch/service-backend-tenant-mcp@sha256:7448cb80d91c0078e7480f2f9ca758356352a62a06857586ed46d7ea363695fb"
        assert env["STALWART_URL"] == "https://id.re8ch.com"
        assert "STALWART_CONNECT_URL" not in env
        assert env["STALWART_CLIENT_ID"] == "705c1168-43d8-4ec3-980a-0327a59c7fc6"
        assert env["STALWART_AUTHORIZATION_URL"] == "https://db-rw.re8ch.com/auth/v1/oauth/authorize"
        assert env["STALWART_TOKEN_URL"] == "https://db-rw.re8ch.com/auth/v1/oauth/token"
        for name in ("STALWART_URL", "STALWART_AUTHORIZATION_URL", "STALWART_TOKEN_URL"):
            assert ".svc" not in env[name] and ".cluster.local" not in env[name]
