from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "clusters/re8ch/tenant-runtime-authority-resources.yaml"
RELEASE = ROOT / "releases/agent-runtime-exact-catalog-runtime-manager/resources.yaml"
CONTRACT = ROOT / "contracts/agent-runtime-exact-catalog-runtime-manager.yaml"
ACCESS = ROOT / "operations/releases/catalog-runtime-exact-release-access.yaml"


def test_catalog_runtime_has_independent_identity_and_database_contract():
    objects = [item for item in yaml.safe_load_all(RELEASE.read_text()) if item]
    by_identity = {(item["kind"], item["metadata"]["name"]): item for item in objects}
    deployment = by_identity[("Deployment", "re8ch-catalog-runtime")]
    assert deployment["spec"]["replicas"] == 2
    assert deployment["spec"]["strategy"] == {
        "type": "RollingUpdate",
        "rollingUpdate": {"maxUnavailable": 0, "maxSurge": 1},
    }
    assert deployment["spec"]["template"]["spec"]["serviceAccountName"] == "re8ch-catalog-runtime"
    assert deployment["spec"]["template"]["spec"]["imagePullSecrets"] == []
    containers = deployment["spec"]["template"]["spec"]["containers"]
    assert [item["name"] for item in containers] == ["runtime"]
    env = {item["name"]: item for item in containers[0]["env"]}
    assert containers[0]["image"] == (
        "ghcr.io/re8ch/service-backend-tenant-mcp@sha256:"
        "f2ea38a7b54587c25da579fbe664bb4d30c41aa8b3decb4049c6c4555e6020d2"
    )
    assert env["MCP_CATALOG_DATABASE_URL"]["valueFrom"]["secretKeyRef"] == {
        "key": "MCP_CATALOG_DATABASE_URL",
        "name": "mcp-catalog-database",
        "optional": False,
    }
    assert env["TENANT_MCP_HERMETIC_SQLITE"]["value"] == "0"
    assert not {"TENANT_SERVICE_DB", "DEVICE_REGISTRY_PATH", "DYNAMIC_SKILL_DB"} & set(env)
    assert env["PUBLIC_MCP_URL"]["value"] == "https://catalog-runtime.service.re8ch.com/mcp"
    assert env["PUBLIC_RESOURCE_METADATA_URL"]["value"] == (
        "https://catalog-runtime.service.re8ch.com/.well-known/oauth-protected-resource/mcp"
    )
    assert env["AUTH_DISCOVERY_URL"]["value"].endswith("/.well-known/oauth-authorization-server")
    pod = deployment["spec"]["template"]["spec"]
    assert [item["name"] for item in containers[0]["volumeMounts"]] == ["platform-modules"]
    assert [item["name"] for item in pod["volumes"]] == ["platform-modules"]
    assert containers[0]["readinessProbe"]["httpGet"] == {"path": "/readyz", "port": "http"}
    pvc = by_identity[("PersistentVolumeClaim", "re8ch-catalog-runtime-state-rbd")]
    assert pvc["spec"]["storageClassName"] == "rbd-r640"
    assert ("PersistentVolumeClaim", "re8ch-catalog-runtime-state") in by_identity
    route = by_identity[("HTTPRoute", "catalog-runtime-mcp")]
    assert route["metadata"]["annotations"] == {
        "external-dns.alpha.kubernetes.io/cloudflare-proxied": "false",
        "external-dns.alpha.kubernetes.io/hostname": "catalog-runtime.service.re8ch.com",
        "external-dns.alpha.kubernetes.io/ttl": "60",
    }
    assert route["metadata"]["labels"] == {"public.re8ch.com/external-dns": "enabled"}
    assert route["spec"]["parentRefs"] == [{
        "name": "re8ch-gateway-canary", "namespace": "kube-system",
        "sectionName": "service-wildcard-https",
    }]
    assert route["spec"]["hostnames"] == ["catalog-runtime.service.re8ch.com"]
    rules = {item["matches"][0]["path"]["value"]: item for item in route["spec"]["rules"]}
    assert set(rules) == {"/mcp", "/.well-known/oauth-protected-resource/mcp"}
    assert all(item["backendRefs"] == [{"name": "re8ch-catalog-runtime", "port": 19448}]
               for item in rules.values())
    dns = by_identity[("Ingress", "catalog-runtime-dns-authority")]
    assert dns["metadata"]["labels"] == {
        "networking.re8ch.com/dns-authority": "public-edge",
    }
    assert dns["metadata"]["annotations"] == {
        "external-dns.alpha.kubernetes.io/cloudflare-proxied": "false",
        "external-dns.alpha.kubernetes.io/hostname": "catalog-runtime.service.re8ch.com",
        "external-dns.alpha.kubernetes.io/target": "tools.service.re8ch.com",
        "external-dns.alpha.kubernetes.io/ttl": "60",
    }
    assert dns["spec"]["ingressClassName"] == "external-dns-only"
    policy = by_identity[("NetworkPolicy", "re8ch-catalog-runtime")]
    namespaces = {
        source["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"]
        for rule in policy["spec"]["ingress"]
        for source in rule.get("from", [])
        if "namespaceSelector" in source
    }
    assert {"toolhive-system", "kube-system"} <= namespaces
    assert "tenant-api" not in {item["metadata"]["name"] for item in objects}


def test_catalog_runtime_exact_objects_match_reviewed_source():
    def object_named(path, kind, name):
        return next(
            item for item in yaml.safe_load_all(path.read_text())
            if item and item.get("kind") == kind and item["metadata"]["name"] == name
        )

    for identity in (
        ("Deployment", "re8ch-catalog-runtime"),
        ("HTTPRoute", "catalog-runtime-mcp"),
        ("Ingress", "catalog-runtime-dns-authority"),
        ("NetworkPolicy", "re8ch-catalog-runtime"),
    ):
        assert object_named(RELEASE, *identity) == object_named(SOURCE, *identity)


def test_catalog_runtime_release_is_create_capable_and_bounded():
    contract = yaml.safe_load(CONTRACT.read_text())
    auth = contract["spec"]["authorization"]
    assert auth["requireExisting"] is False
    assert auth["allowClusterScoped"] is False
    assert contract["spec"]["lifecycle"]["prune"] is True
    assert contract["spec"]["lifecycle"]["deletionAllowlist"] == []
    assert set(auth["objectNames"]) == {
        "catalog-runtime-dns-authority",
        "catalog-runtime-mcp",
        "postgresql-provider-catalog-runtime",
        "re8ch-catalog-runtime",
        "re8ch-catalog-runtime-state",
        "re8ch-catalog-runtime-state-rbd",
    }


def test_catalog_runtime_exact_access_tracks_rbd_claim():
    objects = [item for item in yaml.safe_load_all(ACCESS.read_text()) if item]
    role = next(item for item in objects if item["kind"] == "Role")
    update_names = {
        name
        for rule in role["rules"]
        if "update" in rule.get("verbs", [])
        for name in rule.get("resourceNames", [])
    }
    assert "re8ch-catalog-runtime-state-rbd" in update_names
    assert "re8ch-catalog-runtime-state" in update_names
    route_rules = [rule for rule in role["rules"]
                   if rule.get("apiGroups") == ["gateway.networking.k8s.io"]]
    assert route_rules == [
        {"apiGroups": ["gateway.networking.k8s.io"], "resources": ["httproutes"],
         "verbs": ["create"]},
        {"apiGroups": ["gateway.networking.k8s.io"], "resources": ["httproutes"],
         "resourceNames": ["catalog-runtime-mcp"], "verbs": ["get", "patch", "update"]},
    ]
    ingress_rules = [rule for rule in role["rules"]
                     if rule.get("apiGroups") == ["networking.k8s.io"]
                     and rule.get("resources") == ["ingresses"]]
    assert ingress_rules == [
        {"apiGroups": ["networking.k8s.io"], "resources": ["ingresses"],
         "verbs": ["create"]},
        {"apiGroups": ["networking.k8s.io"], "resources": ["ingresses"],
         "resourceNames": ["catalog-runtime-dns-authority"],
         "verbs": ["get", "patch", "update"]},
    ]
    delete_rules = [rule for rule in role["rules"] if "delete" in rule.get("verbs", [])]
    assert delete_rules == []
