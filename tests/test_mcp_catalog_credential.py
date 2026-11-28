from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "clusters/re8ch/tenant-runtime-authority-resources.yaml"


def documents(path=SOURCE):
    return [item for item in yaml.safe_load_all(path.read_text()) if item]


def test_catalog_runtime_uses_immutable_provider_and_metadata_only_projection():
    items = documents()
    deployment = next(item for item in items if item.get("kind") == "Deployment" and
                      item["metadata"]["name"] == "postgresql-provider")
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == (
        "registry.re8ch.com/image/re8ch-postgresql-provider@sha256:"
        "77f1fb1cc23e3d3db77573fb2a2e8c2e08c296c183c7e098ce9056fcc3ab0522"
    )
    assert not {"MCP_CATALOG_ADMIN_TOKEN", "MCP_CATALOG_ADMIN_URL"} & {
        value["name"] for value in container["env"]
    }
    secret = next(item for item in items if item.get("kind") == "Secret" and
                  item["metadata"]["name"] == "mcp-catalog-database")
    assert "data" not in secret and "stringData" not in secret


def test_catalog_runtime_profile_projection_and_network_are_bounded():
    items = documents()
    instance = next(item for item in items if item.get("kind") == "TenantServiceInstance" and
                    item["metadata"]["name"] == "mcp-catalog-runtime")
    assert instance["spec"]["parameters"] == {"profile": "mcp-catalog-runtime-v1"}
    assert instance["metadata"]["annotations"]["credentials.re8ch.com/rotation"] == "1"
    tenant_api = next(item for item in items if item.get("kind") == "Deployment" and
                      item["metadata"]["name"] == "tenant-api")
    env = {item["name"]: item for item in tenant_api["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert env["MCP_CATALOG_DATABASE_URL"]["valueFrom"]["secretKeyRef"] == {
        "name": "mcp-catalog-database", "key": "MCP_CATALOG_DATABASE_URL", "optional": False}
    policy = next(item for item in items if item.get("kind") == "CiliumNetworkPolicy" and
                  item["metadata"]["name"] == "postgresql-provider-egress")
    assert policy["spec"]["egress"][1]["toServices"][0]["k8sService"] == {
        "serviceName": "pg-re8ch-primary", "namespace": "pigsty-external"}


def test_catalog_projection_rbac_is_exact_and_broker_only_adds_patch():
    items = documents(ROOT / "clusters/re8ch/resources.yaml")
    projection = next(item for item in items if item.get("kind") == "Role" and
                      item["metadata"]["name"] == "postgresql-provider-catalog-projection")
    assert projection["rules"] == [{"apiGroups": [""], "resources": ["secrets"],
                                     "resourceNames": ["mcp-catalog-database"], "verbs": ["get", "patch"]}]
    broker = next(item for item in items if item.get("kind") == "Role" and
                  item["metadata"]["name"] == "postgresql-provider-credential-broker")
    assert broker["rules"] == [{"apiGroups": [""], "resources": ["secrets"],
                                 "verbs": ["get", "create", "patch"]}]
