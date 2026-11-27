from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "clusters/re8ch/tenant-runtime-authority-resources.yaml"


def objects():
    return [item for item in yaml.safe_load_all(SOURCE.read_text()) if item]


def deployment(name):
    return next(item for item in objects() if item["kind"] == "Deployment" and item["metadata"]["name"] == name)


def test_tenant_api_uses_canonical_plugin_resource_and_bound_issuer():
    container = deployment("tenant-api")["spec"]["template"]["spec"]["containers"][0]
    env = {item["name"]: item for item in container["env"]}
    assert env["PUBLIC_MCP_URL"]["value"].endswith("/tenant-plugin/mcp")
    assert env["PUBLIC_RESOURCE_METADATA_URL"]["value"].endswith(
        "/.well-known/oauth-protected-resource/tenant-plugin/mcp"
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


def test_plugin_routes_are_canonical_and_native_routes_remain_compatibility_aliases():
    route = next(item for item in objects() if item["kind"] == "HTTPRoute" and item["metadata"]["name"] == "tenant-native-mcp")
    paths = {match["path"]["value"] for rule in route["spec"]["rules"] for match in rule["matches"]}
    assert {"/tenant-plugin/mcp", "/tenant-native/mcp"} <= paths
    assert {
        "/.well-known/oauth-protected-resource/tenant-plugin/mcp",
        "/.well-known/oauth-protected-resource/tenant-native/mcp",
    } <= paths
