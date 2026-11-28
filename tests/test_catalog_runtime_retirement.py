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
    assert "tenant-api" not in {item["metadata"]["name"] for item in objects}


def test_catalog_runtime_exact_deployment_matches_reviewed_source():
    def deployment(path):
        return next(
            item for item in yaml.safe_load_all(path.read_text())
            if item and item.get("kind") == "Deployment"
            and item["metadata"]["name"] == "re8ch-catalog-runtime"
        )

    assert deployment(RELEASE) == deployment(SOURCE)


def test_catalog_runtime_release_is_create_capable_and_bounded():
    contract = yaml.safe_load(CONTRACT.read_text())
    auth = contract["spec"]["authorization"]
    assert auth["requireExisting"] is False
    assert auth["allowClusterScoped"] is False
    assert contract["spec"]["lifecycle"]["prune"] is True
    assert contract["spec"]["lifecycle"]["deletionAllowlist"] == []
    assert set(auth["objectNames"]) == {
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
    delete_rules = [rule for rule in role["rules"] if "delete" in rule.get("verbs", [])]
    assert delete_rules == []
