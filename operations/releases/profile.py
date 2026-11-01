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
REPLAY_WORKFLOW = ".github/workflows/agent-runtime-reconcile.yml"
REPLAY_ENVIRONMENT = "release-reconciler-agent-runtime"
REPLAY_AUDIENCE = "https://kube-api.re8ch.com/release-reconciler-agent-runtime"


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
    expected = {
        "repository": REPOSITORY,
        "workflow": WORKFLOW,
        "ref": "refs/heads/main",
        "environment": ENVIRONMENT,
        "audience": AUDIENCE,
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
        if source.get("renderer") != "kustomize" or not source_path.startswith("releases/" + ("observability" if spec["authorityDomain"] == "observability-metering" else spec["authorityDomain"]) + "-domain-"):
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
        "domain": "agent-runtime",
        "environment": ENVIRONMENT,
        "audience": AUDIENCE,
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
        result.append({**profile, "contract": str(path.relative_to(ROOT)),
                       "environment": REPLAY_ENVIRONMENT, "audience": REPLAY_AUDIENCE})
    return result


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
