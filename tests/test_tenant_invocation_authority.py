from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "clusters/re8ch/tenant-runtime-authority-resources.yaml"


def objects():
    return [item for item in yaml.safe_load_all(SOURCE.read_text()) if item]


def deployment(name):
    return next(item for item in objects() if item["kind"] == "Deployment" and item["metadata"]["name"] == name)


def test_tenant_api_uses_native_resource_and_bound_issuer():
    container = deployment("tenant-api")["spec"]["template"]["spec"]["containers"][0]
    env = {item["name"]: item for item in container["env"]}
    assert env["PUBLIC_MCP_URL"]["value"].endswith("/tenant-native/mcp")
    assert env["PUBLIC_RESOURCE_METADATA_URL"]["value"].endswith(
        "/.well-known/oauth-protected-resource/tenant-native/mcp"
    )
    assert env["INVOCATION_TOKEN_ISSUER"]["value"] == "https://tools.service.re8ch.com/invocation"
    assert env["TENANT_CLAIM_SERVICE_TOKEN"]["valueFrom"]["secretKeyRef"] == {
        "name": "tenant-claim-internal-auth",
        "key": "TENANT_CLAIM_SERVICE_TOKEN",
        "optional": False,
    }


def test_issuer_reads_only_managed_secret_refs_and_binding_authority():
    pod = deployment("tenant-control-controller")["spec"]["template"]["spec"]
    container = pod["containers"][0]
    env = {item["name"]: item for item in container["env"]}
    assert env["BINDING_AUTHORITY_URL"]["value"].endswith("/rpc/resolve_tool_invocation")
    assert {item["secretRef"]["name"] for item in container["envFrom"]} >= {
        "tenant-invocation-authority"
    }
    volume = next(item for item in pod["volumes"] if item["name"] == "invocation-signing")
    assert volume["secret"] == {"secretName": "tenant-invocation-signing", "optional": True}


def test_native_mcp_is_the_only_tenant_tool_publication_route():
    route = next(item for item in objects() if item["kind"] == "HTTPRoute" and item["metadata"]["name"] == "tenant-native-mcp")
    paths = {match["path"]["value"] for rule in route["spec"]["rules"] for match in rule["matches"]}
    assert "/tenant-native/mcp" in paths
    assert "/.well-known/oauth-protected-resource/tenant-native/mcp" in paths
    assert "/tenant-plugin/mcp" not in paths
    assert "/.well-known/oauth-protected-resource/tenant-plugin/mcp" not in paths
