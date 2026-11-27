import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_toolhive_catalog_uses_canonical_openoauth_resource():
    documents = yaml.safe_load_all((ROOT / "clusters/re8ch/resources.yaml").read_text())
    catalog = next(
        document
        for document in documents
        if document
        and document.get("kind") == "ConfigMap"
        and document.get("metadata", {}).get("name") == "re8ch-approved-tool-catalog"
    )
    registry = json.loads(catalog["data"]["registry.json"])

    assert registry["data"]["servers"][0]["remotes"] == [{
        "type": "streamable-http",
        "url": "https://tools.service.re8ch.com/tenant-native/mcp",
    }]
