#!/usr/bin/env python3
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CLUSTER = ROOT / "clusters/re8ch"


def documents(path):
    return [item for item in yaml.safe_load_all(path.read_text()) if item]


def named(items, kind, name):
    return next(item for item in items if item["kind"] == kind and item["metadata"]["name"] == name)


baseline = json.loads((Path(__file__).parent / "baseline.json").read_text())
shadow = documents(CLUSTER / "stalwart-agent-tools-shadow.yaml")
server = named(shadow, "MCPServer", "stalwart-agent-tools-shadow")
account = named(shadow, "ServiceAccount", "stalwart-agent-tools")
policy = named(shadow, "NetworkPolicy", "stalwart-agent-tools-shadow")

assert server["spec"]["image"] == baseline["image"]
annotations = server["metadata"]["annotations"]
assert annotations["re8ch.com/provider-contract-sha256"] == baseline["providerContractSha256"]
assert annotations["re8ch.com/tool-catalog-sha256"] == baseline["toolCatalogSha256"]
assert annotations["re8ch.com/rollback-mode"] == "remove-shadow-preserve-tenant-mcp"
assert server["metadata"]["labels"]["re8ch.com/publication-stage"] == "shadow"
assert server["spec"]["backendReplicas"] == 1
assert server["spec"]["serviceAccount"] == account["metadata"]["name"]

pod = server["spec"]["podTemplateSpec"]["spec"]
assert pod["automountServiceAccountToken"] is False
token = pod["volumes"][0]["projected"]["sources"][0]["serviceAccountToken"]
assert token == {"audience": "stalwart-binding-broker", "expirationSeconds": 600, "path": "stalwart-binding-broker"}
assert {entry["name"] for entry in server["spec"]["env"]} == {
    "LISTEN_ADDRESS", "BINDING_BROKER_URL", "BINDING_BROKER_TOKEN_FILE"
}
assert policy["spec"]["policyTypes"] == ["Ingress", "Egress"]
assert policy["spec"]["ingress"] == [{
    "from": [{
        "namespaceSelector": {
            "matchLabels": {"kubernetes.io/metadata.name": "tenant-infrastructure"}
        },
        "podSelector": {"matchLabels": {"app": "tenant-api"}},
    }],
    "ports": [{"protocol": "TCP", "port": 8088}],
}]

broker = named(documents(CLUSTER / "stalwart-agent-tools-broker-patch.yaml"), "Deployment", "tenant-api")
broker_env = broker["spec"]["template"]["spec"]["containers"][0]["env"]
assert {entry["name"] for entry in broker_env} == {
    "STALWART_TOOL_CLIENT", "STALWART_TOOL_REF", "STALWART_TOOL_OWNER_ORG_REF", "STALWART_TOOL_AUDIENCE"
}

# The migration is additive: the established collaboration runtime and route
# remain a required part of every render until parity, soak, and rollback close.
legacy = (CLUSTER / "tenant-runtime-authority-resources.yaml").read_text()
assert "name: COLLABORATION_ENABLED\n          value: 'true'" in legacy
assert "name: tenant-mcp-publication-resources.yaml" not in legacy
assert (CLUSTER / "tenant-mcp-publication-resources.yaml").exists()
kustomization = yaml.safe_load((CLUSTER / "kustomization.yaml").read_text())
assert "tenant-mcp-publication-resources.yaml" in kustomization["resources"]
assert "stalwart-agent-tools-shadow.yaml" in kustomization["resources"]

assert len(baseline["userOperations"]) == 9
assert len(baseline["requiredScopes"]) == 6
print("validated additive Stalwart shadow baseline: 9 tools, 6 scopes, legacy runtime preserved")
