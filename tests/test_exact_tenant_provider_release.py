from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "agent-runtime-exact-tenant-provider-reconciler"
IMAGE = (
    "registry.re8ch.com/image/re8ch-ai-operations@sha256:"
    "07515ac19cebfbeedeb1dbc42cac237eea98952f8b47293120e19cd7fd30cd52"
)


def documents(path):
    return [item for item in yaml.safe_load_all((ROOT / path).read_text()) if item]


def test_exact_provider_release_has_one_digest_pinned_deployment():
    release = documents(
        "releases/agent-runtime-exact-tenant-provider-reconciler/tenant-provider-reconciler.yaml"
    )
    assert len(release) == 1
    deployment = release[0]
    assert (deployment["apiVersion"], deployment["kind"]) == ("apps/v1", "Deployment")
    assert deployment["metadata"] == {
        "name": "tenant-provider-reconciler",
        "namespace": "tenant-infrastructure",
    }
    assert deployment["spec"]["template"]["spec"]["containers"][0]["image"] == IMAGE
    pod_spec = deployment["spec"]["template"]["spec"]
    assert pod_spec["imagePullSecrets"] == []
    assert pod_spec["volumes"][0]["image"]["reference"] == (
        "ghcr.io/stalwartlabs/cli@sha256:"
        "5b70732cb69cdab3ff0894c501544cf0bfa180fa75bcd0eeba4eebe04c1064e1"
    )
    serialized = yaml.safe_dump(deployment)
    assert "tenant-api" not in serialized
    assert "HTTPRoute" not in serialized
    assert "postgresql-provider" not in serialized


def test_exact_provider_contract_and_access_are_single_object_bounded():
    contract = yaml.safe_load((ROOT / f"contracts/{RELEASE_ID}.yaml").read_text())
    authorization = contract["spec"]["authorization"]
    assert authorization["resources"] == ["apps/Deployment"]
    assert authorization["objectNames"] == ["tenant-provider-reconciler"]
    assert authorization["forceConflictObjects"] == [
        "apps/Deployment/tenant-infrastructure/tenant-provider-reconciler"
    ]
    assert authorization["requireExisting"] is True

    access = documents("operations/releases/tenant-provider-exact-release-access.yaml")
    assert [item["kind"] for item in access] == ["ConfigMap", "Role", "RoleBinding"]
    role = access[1]
    assert role["metadata"]["name"] == RELEASE_ID
    assert role["rules"] == [
        {
            "apiGroups": [""],
            "resources": ["configmaps"],
            "resourceNames": [f"ssa-state-{RELEASE_ID}"],
            "verbs": ["get", "patch", "update"],
        },
        {
            "apiGroups": ["apps"],
            "resources": ["deployments"],
            "resourceNames": ["tenant-provider-reconciler"],
            "verbs": ["get", "patch", "update"],
        },
    ]
