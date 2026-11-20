#!/usr/bin/env python3
"""Validate the bounded agent-runtime release profile."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "contracts"
REPOSITORY = "8iops/agent-gitops"
WORKFLOW = ".github/workflows/static-release.yml"
ENVIRONMENT = "release-executor-agent-runtime"
AUDIENCE = "https://kube-api.re8ch.com/release-executor-agent-runtime"
GROUP = "re8ch:release-executor:agent-runtime"
SIGNER = f"https://github.com/{REPOSITORY}/{WORKFLOW}@refs/heads/main"
EXECUTION_PROFILES = {
    "re8ch": {"environment": ENVIRONMENT, "audience": AUDIENCE},
    "re8ch-atlantic": {
        "environment": "release-executor-agent-runtime-atlantic",
        "audience": "https://kube-api.re8ch.com/release-executor-agent-runtime-atlantic",
    },
}
REPLAY_WORKFLOW = ".github/workflows/agent-runtime-reconcile.yml"
REPLAY_ENVIRONMENT = "release-reconciler-agent-runtime"
REPLAY_AUDIENCE = "https://kube-api.re8ch.com/release-reconciler-agent-runtime"
SCHEDULED_RECONCILE_SCOPE = ROOT / "operations/releases/scheduled-reconcile.yaml"


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def validate_contract(path: Path) -> dict[str, str]:
    resolved = path.resolve()
    if CONTRACT_ROOT.resolve() not in resolved.parents or resolved.suffix not in {".yaml", ".yml"}:
        raise ValueError("contract must be a YAML file under contracts")
    contract = yaml.safe_load(resolved.read_text())
    spec = contract["spec"]
    if spec.get("authorityDomain") != "agent-runtime":
        raise ValueError("contract authorityDomain must be agent-runtime")
    if not contract["metadata"]["name"].startswith("agent-runtime-"):
        raise ValueError("contract name is outside agent-runtime")
    cluster = spec["target"].get("cluster")
    if cluster not in EXECUTION_PROFILES:
        raise ValueError("unsupported agent-runtime target cluster")
    execution = EXECUTION_PROFILES[cluster]
    expected = {
        "repository": REPOSITORY,
        "workflow": WORKFLOW,
        "ref": "refs/heads/main",
        "environment": execution["environment"],
        "audience": execution["audience"],
        "signer": SIGNER,
    }
    for field, value in expected.items():
        if spec["provenance"].get(field) != value:
            raise ValueError(f"contract provenance {field} must be {value}")
    source = spec["source"]
    source_path = source.get("path", "")
    if source.get("repository") != REPOSITORY or not source_path.startswith("releases/"):
        raise ValueError("contract source must resolve inside this repository")
    if source.get("revision") == "github-main-reviewed":
        generated_prefix = "releases/" + ("observability" if spec["authorityDomain"] == "observability-metering" else spec["authorityDomain"]) + "-domain-"
        authorization = spec.get("authorization", {})
        exact_crd_authority = (
            authorization.get("allowClusterScoped") is True
            and authorization.get("resources") == ["apiextensions.k8s.io/CustomResourceDefinition"]
            and source_path.startswith("releases/agent-runtime-")
        )
        exact_object_authority = (
            authorization.get("requireExisting") is True
            and spec.get("lifecycle", {}).get("prune") is False
            and source_path.startswith("releases/agent-runtime-exact-")
        )
        if source.get("renderer") != "kustomize" or not (source_path.startswith(generated_prefix) or exact_crd_authority or exact_object_authority):
            raise ValueError("static domain source must use its generated namespace cohort")
    else:
        if source.get("renderer") != "kustomize" or "@sha256:" not in source.get("chartOCI", ""):
            raise ValueError("shadow source must bind a digest-pinned Helm chart and reviewed Kustomize render")
        for value in source.get("values", []):
            value_path = (ROOT / value["path"]).resolve()
            if ROOT.resolve() not in value_path.parents or sha256(value_path) != value["digest"]:
                raise ValueError(f"values digest mismatch: {value['path']}")
        locked = yaml.safe_load((ROOT / source_path / "source.yaml").read_text())["spec"]
        if locked["chart"] != source["chartOCI"]:
            raise ValueError("locked render chart differs from contract")
        if locked["valuesDigest"] != sha256(ROOT / source_path / locked["values"]):
            raise ValueError("locked render values digest mismatch")
        if locked["renderedResourcesDigest"] != sha256(ROOT / source_path / locked["renderedResources"]):
            raise ValueError("locked rendered resources digest mismatch")
    return {
        "release-id": contract["metadata"]["name"],
        "namespace": spec["target"]["namespace"],
        "cluster": cluster,
        "domain": "agent-runtime",
        "environment": execution["environment"],
        "audience": execution["audience"],
        "kubernetes-group": GROUP,
        "signer": SIGNER,
    }


def replay_provenance(contract: dict) -> dict[str, str] | None:
    spec = contract["spec"]
    expected = {"repository": REPOSITORY, "workflow": WORKFLOW, "ref": "refs/heads/main",
                "environment": ENVIRONMENT, "audience": AUDIENCE, "signer": SIGNER}
    if spec.get("authorityDomain") != "agent-runtime" or any(spec.get("provenance", {}).get(k) != v for k, v in expected.items()):
        return None
    return {"repository": REPOSITORY, "workflow": REPLAY_WORKFLOW, "ref": "refs/heads/main",
            "environment": REPLAY_ENVIRONMENT, "audience": REPLAY_AUDIENCE}


def replay_matrix() -> list[dict[str, str]]:
    result = []
    for path in sorted(CONTRACT_ROOT.glob("agent-runtime-*.yaml")):
        profile = validate_contract(path.relative_to(ROOT))
        # The scheduled reconciler is intentionally bound to the main-cluster
        # replay identity. Atlantic releases are explicit, protected dispatches
        # until a separate Atlantic reconciler contract is reviewed.
        if profile["cluster"] != "re8ch":
            continue
        result.append({**profile, "contract": str(path.relative_to(ROOT)),
                       "environment": REPLAY_ENVIRONMENT, "audience": REPLAY_AUDIENCE})
    return result


def scheduled_replay_matrix(matrix: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    matrix = replay_matrix() if matrix is None else matrix
    configured = yaml.safe_load(SCHEDULED_RECONCILE_SCOPE.read_text())["spec"]["releases"]
    if not isinstance(configured, list) or not configured or len(configured) != len(set(configured)):
        raise ValueError("scheduled reconcile releases must be a non-empty unique list")
    by_id = {entry["release-id"]: entry for entry in matrix}
    unknown = sorted(set(configured) - set(by_id))
    if unknown:
        raise ValueError("scheduled reconcile contains unknown releases: " + ", ".join(unknown))
    return [by_id[release_id] for release_id in configured]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--replay-matrix", action="store_true")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    if args.replay_matrix:
        print(json.dumps({"include": replay_matrix()}, separators=(",", ":")))
        return 0
    if args.contract is None:
        parser.error("--contract is required unless --replay-matrix is used")
    result = validate_contract(args.contract)
    if args.github_output:
        with args.github_output.open("a") as output:
            for key, value in result.items():
                output.write(f"{key}={value}\n")
    else:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
