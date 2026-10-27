#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

root = Path(__file__).resolve().parents[1]
policy = yaml.safe_load((root / "policies/domain.yaml").read_text())
documents = [d for d in yaml.safe_load_all((root / "clusters/re8ch/resources.yaml").read_text()) if d]
seen = set()
errors = []
for doc in documents:
    meta = doc.get("metadata", {})
    identity = (doc.get("apiVersion"), doc.get("kind"), meta.get("namespace", ""), meta.get("name"))
    if identity in seen:
        errors.append(f"duplicate object: {identity}")
    seen.add(identity)
for item in policy.get("forbidden", []):
    identity = (item["apiVersion"], item["kind"], item.get("namespace", ""), item["name"])
    if identity in seen:
        errors.append(f"product-owned object is forbidden: {identity}")
toolhive = next(
    (d for d in documents if d.get("kind") == "HelmRelease" and d.get("metadata", {}).get("name") == "toolhive-operator"),
    None,
)
operator = (toolhive or {}).get("spec", {}).get("values", {}).get("operator", {})
if operator.get("replicaCount") != 1 or operator.get("nodeSelector") != {"kubernetes.io/hostname": "r640"}:
    errors.append("ToolHive must remain a single R640 replica until the cross-node API path is restored")
environment = {entry.get("name"): str(entry.get("value")) for entry in operator.get("env", [])}
if environment.get("KUBERNETES_SERVICE_HOST") != "10.250.0.128" or environment.get("KUBERNETES_SERVICE_PORT") != "6443":
    errors.append("ToolHive must use the R640-local API endpoint while the cross-node API path is degraded")
for name in ("re8ch-plugin-runtime", "toolhive-cloud-ui"):
    deployment = next(
        (d for d in documents if d.get("kind") == "Deployment" and d.get("metadata", {}).get("name") == name),
        None,
    )
    pod_spec = (deployment or {}).get("spec", {}).get("template", {}).get("spec", {})
    if pod_spec.get("nodeSelector") != {"kubernetes.io/hostname": "r640"}:
        errors.append(f"{name} must be pinned to R640")
    if pod_spec.get("affinity", {}).get("podAntiAffinity", {}).get("requiredDuringSchedulingIgnoredDuringExecution"):
        errors.append(f"{name} cannot require cross-node anti-affinity while ToolHive is R640-only")
for document in documents:
    if document.get("kind") != "ConfigMap":
        continue
    name = document.get("metadata", {}).get("name")
    restricted = {"ai-operations-inventory": "nodes.json", "ai-operations-ssh-config": "ssh-config"}.get(name)
    if restricted and (not document.get("sops", {}).get("age") or
                       not document.get("data", {}).get(restricted, "").startswith("ENC[AES256_GCM,")):
        errors.append("node inventory and SSH targets must remain SOPS encrypted")
for document in documents:
    keys = {"ops-mcp-server-code": ["app.py"], "cube-trial-values": ["values.yaml"]}.get(document.get("metadata", {}).get("name"), [])
    if document.get("kind") == "ConfigMap" and keys:
        if not document.get("sops", {}).get("age") or any(not document.get("data", {}).get(key, "").startswith("ENC[AES256_GCM,") for key in keys):
            errors.append("restricted endpoint configuration must remain encrypted")
if errors:
    print("\n".join(errors), file=sys.stderr)
    raise SystemExit(1)
print(f"validated {policy['domain']}: {len(documents)} objects")
