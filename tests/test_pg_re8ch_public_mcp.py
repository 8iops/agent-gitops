import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "agent-runtime-exact-pg-re8ch-mcp"
PUBLIC_URL = "https://pg-re8ch-mcp.service.re8ch.com/mcp"
METADATA_URL = "https://pg-re8ch-mcp.service.re8ch.com/.well-known/oauth-protected-resource/mcp"
IMAGE = "ghcr.io/re8ch/service-backend-tenant-mcp@sha256:f6344bf787b425586b23f371c4128b4eb4f3655a6ce10402fe866d6871c50974"


def documents(path):
    return [item for item in yaml.safe_load_all((ROOT / path).read_text()) if item]


def test_facade_uses_immutable_product_image_and_private_studio_backend():
    items = documents(f"releases/{RELEASE_ID}/resources.yaml")
    deployment = next(item for item in items if item["kind"] == "Deployment")
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == IMAGE
    env = {item["name"]: item for item in container["env"]}
    assert env["PG_RE8CH_PUBLIC_MCP_URL"]["value"] == PUBLIC_URL
    assert env["PG_RE8CH_RESOURCE_METADATA_URL"]["value"] == METADATA_URL
    assert env["MCP_CATALOG_DATABASE_URL"]["valueFrom"]["secretKeyRef"]["name"] == "mcp-catalog-database"
    assert env["TENANT_CLAIM_SERVICE_TOKEN"]["valueFrom"]["secretKeyRef"]["name"] == "tenant-claim-internal-auth"
    modules = next(item for item in items if item["kind"] == "ConfigMap")
    registry = json.loads(modules["data"]["modules.json"])
    assert registry["version"] == 1
    backends = registry["backends"]
    assert set(backends) == {"pg_re8ch"}
    assert backends["pg_re8ch"] == {
        "url": "https://supabase.service.re8ch.com/api/mcp",
        "authMode": "basic",
        "namespace": "supabase-pg-re8ch",
        "secret": "supabase-pg-re8ch-secrets",
        "usernameSecretKey": "DASHBOARD_USERNAME",
        "passwordSecretKey": "DASHBOARD_PASSWORD",
    }
    assert ".svc" not in modules["data"]["modules.json"]
    assert "Basic " not in yaml.safe_dump(items)


def test_publicedge_publishes_only_fixed_https_contract():
    items = documents(f"releases/{RELEASE_ID}/resources.yaml")
    routes = {item["metadata"]["name"]: item for item in items if item["kind"] == "HTTPRoute"}
    secure = routes["pg-re8ch-mcp-https"]
    assert secure["spec"]["hostnames"] == ["pg-re8ch-mcp.service.re8ch.com"]
    assert secure["spec"]["parentRefs"] == [{
        "name": "re8ch-gateway-canary",
        "namespace": "kube-system",
        "sectionName": "service-wildcard-https",
    }]
    paths = [rule["matches"][0]["path"]["value"] for rule in secure["spec"]["rules"]]
    assert paths == ["/mcp", "/.well-known/oauth-protected-resource/mcp"]
    public_objects = yaml.safe_dump([routes["pg-re8ch-mcp-https"], routes["pg-re8ch-mcp-http"]])
    assert ".svc" not in public_objects
    assert "basic" not in public_objects.lower()
    dns = next(item for item in items if item["kind"] == "Ingress")
    assert dns["metadata"]["labels"]["networking.re8ch.com/dns-authority"] == "public-edge"
    assert dns["metadata"]["annotations"]["external-dns.alpha.kubernetes.io/target"] == "tools.service.re8ch.com"
    assert dns["spec"]["ingressClassName"] == "external-dns-only"


def test_exact_release_and_executor_access_are_name_bounded():
    contract = yaml.safe_load((ROOT / f"contracts/{RELEASE_ID}.yaml").read_text())
    auth = contract["spec"]["authorization"]
    assert auth["fieldManager"] == f"re8ch-release/{RELEASE_ID}"
    assert auth["forceConflictObjects"] == []
    assert set(auth["objectNames"]) == {
        "pg-re8ch-mcp", "pg-re8ch-mcp-dns-authority", "pg-re8ch-mcp-egress", "pg-re8ch-mcp-http",
        "pg-re8ch-mcp-https", "pg-re8ch-mcp-modules",
    }
    access = documents("clusters/re8ch/pg-re8ch-mcp-exact-release-access.yaml")
    assert [item["kind"] for item in access] == ["ConfigMap", "Role", "RoleBinding", "Role", "RoleBinding"]
    role = access[1]
    assert role["metadata"]["name"] == RELEASE_ID
    serialized = yaml.safe_dump(role)
    assert "*" not in serialized
    credential_role = access[3]
    assert credential_role["metadata"] == {
        "name": "pg-re8ch-mcp-upstream-credential", "namespace": "supabase-pg-re8ch",
    }
    assert credential_role["rules"] == [{
        "apiGroups": [""], "resources": ["secrets"],
        "resourceNames": ["supabase-pg-re8ch-secrets"], "verbs": ["get"],
    }]
