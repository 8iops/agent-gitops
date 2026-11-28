from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "clusters/re8ch/tenant-runtime-authority-resources.yaml"
EXACT_TENANT_API = ROOT / "releases/agent-runtime-exact-tenant-service-api-manager/tenant-service-api.yaml"


def objects():
    return [item for item in yaml.safe_load_all(SOURCE.read_text()) if item]


def deployment(name):
    return next(item for item in objects() if item["kind"] == "Deployment" and item["metadata"]["name"] == name)


def test_tenant_service_api_keeps_invocation_auth_but_not_mcp_publication():
    container = deployment("tenant-service-api")["spec"]["template"]["spec"]["containers"][0]
    env = {item["name"]: item for item in container["env"]}
    assert "PUBLIC_MCP_URL" not in env
    assert "PUBLIC_RESOURCE_METADATA_URL" not in env
    assert env["INVOCATION_TOKEN_ISSUER"]["value"] == "https://tools.service.re8ch.com/invocation"
    assert env["TENANT_CLAIM_SERVICE_TOKEN"]["valueFrom"]["secretKeyRef"] == {
        "name": "tenant-claim-internal-auth",
        "key": "TENANT_CLAIM_SERVICE_TOKEN",
        "optional": False,
    }


def test_exact_tenant_service_release_has_no_mcp_gateway_sidecar():
    exact = yaml.safe_load(EXACT_TENANT_API.read_text())
    containers = exact["spec"]["template"]["spec"]["containers"]
    assert [item["name"] for item in containers] == ["runtime"]
    container = containers[0]
    env = {item["name"]: item for item in container["env"]}
    assert "PUBLIC_MCP_URL" not in env
    assert "PUBLIC_RESOURCE_METADATA_URL" not in env


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
    mcp_paths = {path for path in paths if path.endswith("/mcp")}
    assert mcp_paths == {
        "/tenant-native/mcp",
        "/.well-known/oauth-protected-resource/tenant-native/mcp",
    }


def test_canonical_native_mcp_and_metadata_route_to_toolhive():
    route = next(item for item in objects()
                 if item["kind"] == "HTTPRoute" and item["metadata"]["name"] == "tenant-native-mcp")
    rules = {
        rule["matches"][0]["path"]["value"]: rule
        for rule in route["spec"]["rules"]
    }
    for path in (
        "/tenant-native/mcp",
        "/.well-known/oauth-protected-resource/tenant-native/mcp",
    ):
        assert rules[path]["backendRefs"] == [{
            "group": "",
            "kind": "Service",
            "name": "vmcp-re8ch-native",
            "namespace": "toolhive-system",
            "port": 4483,
        }]
