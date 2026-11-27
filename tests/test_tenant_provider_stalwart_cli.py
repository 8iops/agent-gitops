from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def documents(path):
    return [item for item in yaml.safe_load_all(path.read_text()) if item]


def test_tenant_provider_mounts_pinned_stalwart_cli_image():
    items = documents(ROOT / "clusters/re8ch/tenant-runtime-authority-resources.yaml")
    deployment = next(
        item
        for item in items
        if item.get("kind") == "Deployment"
        and item["metadata"]["name"] == "tenant-provider-reconciler"
    )
    pod = deployment["spec"]["template"]["spec"]
    container = next(item for item in pod["containers"] if item["name"] == "reconciler")
    assert container["volumeMounts"] == [{
        "name": "stalwart-cli",
        "mountPath": "/cli",
        "readOnly": True,
    }]
    assert pod["volumes"] == [{
        "name": "stalwart-cli",
        "image": {
            "reference": "ghcr.io/stalwartlabs/cli@sha256:5b70732cb69cdab3ff0894c501544cf0bfa180fa75bcd0eeba4eebe04c1064e1",
            "pullPolicy": "IfNotPresent",
        },
    }]
