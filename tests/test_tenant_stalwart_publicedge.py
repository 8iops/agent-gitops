from pathlib import Path
import subprocess

import yaml


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "clusters/re8ch/tenant-runtime-authority-resources.yaml"
EXACT = ROOT / "releases/agent-runtime-exact-tenant-service-api-manager/tenant-service-api.yaml"


def tenant_runtime_environment(path):
    deployment = next(
        item
        for item in yaml.safe_load_all(path.read_text())
        if item and item.get("kind") == "Deployment" and item["metadata"]["name"] == "tenant-service-api"
    )
    runtime = next(item for item in deployment["spec"]["template"]["spec"]["containers"] if item["name"] == "runtime")
    return runtime, {item["name"]: item.get("value") for item in runtime["env"]}


def test_tenant_stalwart_uses_publicedge_and_reviewed_oauth():
    for path in (SOURCE, EXACT):
        runtime, env = tenant_runtime_environment(path)
        expected_digest = (
            "9627dec87e6f4217693dae060b6324fa1481bddc612faca984c3fba9ee427ecb"
            if path == EXACT
            else "b6d5e3f4d568801e448f0269171895d2a33a2345f3bba8a0e38959174a59d589"
        )
        assert runtime["image"] == f"ghcr.io/re8ch/service-backend-tenant-mcp@sha256:{expected_digest}"
        assert env["LITELLM_GATEWAY_URL"] == "https://litellm.service.re8ch.com/v1"
        assert env["STALWART_URL"] == "https://id.re8ch.com"
        assert "STALWART_CONNECT_URL" not in env
        assert env["STALWART_CLIENT_ID"] == "705c1168-43d8-4ec3-980a-0327a59c7fc6"
        assert env["STALWART_AUTHORIZATION_URL"] == "https://db-rw.re8ch.com/auth/v1/oauth/authorize"
        assert env["STALWART_TOKEN_URL"] == "https://db-rw.re8ch.com/auth/v1/oauth/token"
        for name in ("STALWART_URL", "STALWART_AUTHORIZATION_URL", "STALWART_TOKEN_URL"):
            assert ".svc" not in env[name] and ".cluster.local" not in env[name]

    _, exact_env = tenant_runtime_environment(EXACT)
    assert exact_env["STALWART_TOOL_CLIENT"] == "system:serviceaccount:toolhive-system:stalwart-agent-tools"
    assert exact_env["STALWART_TOOL_REF"] == "tool://8iops/stalwart-agent-tools"
    assert exact_env["STALWART_TOOL_OWNER_ORG_REF"] == "publisher"
    assert exact_env["STALWART_TOOL_AUDIENCE"] == "re8ch-tenant-tool"
    assert exact_env["STALWART_TOOL_ENDPOINT"] == (
        "http://mcp-stalwart-agent-tools-shadow.toolhive-system.svc.cluster.local:8088/mcp"
    )


def test_tenant_provider_admin_uses_publicedge():
    rendered = subprocess.check_output(
        ["kubectl", "kustomize", str(ROOT / "clusters/re8ch")], text=True
    )
    deployment = next(
        item
        for item in yaml.safe_load_all(rendered)
        if item and item.get("kind") == "Deployment"
        and item["metadata"]["name"] == "tenant-provider-reconciler"
    )
    container = next(
        item for item in deployment["spec"]["template"]["spec"]["containers"]
        if item["name"] == "reconciler"
    )
    assert container["image"] == "registry.re8ch.com/image/re8ch-ai-operations@sha256:cd47325ab6f192e7d2d0960e709cac3048b5920d8fb1212d4384967f979ac655"
    env = {item["name"]: item.get("value") for item in container["env"]}
    assert env["STALWART_URL"] == "https://stalwart-admin.service.re8ch.com"
    assert ".svc" not in env["STALWART_URL"] and ".cluster.local" not in env["STALWART_URL"]
