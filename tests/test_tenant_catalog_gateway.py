from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_gateway_ingress_allows_tenant_core_and_catalog_ports():
    documents = yaml.safe_load_all(
        (ROOT / "clusters/re8ch/tenant-runtime-authority-resources.yaml").read_text()
    )
    policy = next(
        document
        for document in documents
        if document
        and document.get("kind") == "CiliumNetworkPolicy"
        and document["metadata"]["name"] == "tenant-api-gateway"
    )
    ports = {
        port["port"]
        for rule in policy["spec"]["ingress"]
        for group in rule["toPorts"]
        for port in group["ports"]
    }
    assert ports == {"19448", "19449"}
