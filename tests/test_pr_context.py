import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_pr_context", ROOT / "operations/github/validate_pr_context.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
POLICY = json.loads((ROOT / "governance/context.json").read_text())


def response(issues):
    return {
        "data": {
            "repository": {
                "pullRequest": {"closingIssuesReferences": {"nodes": issues}}
            }
        }
    }


def issue(number, labels):
    return {
        "number": number,
        "url": f"https://github.com/8iops/agent-gitops/issues/{number}",
        "labels": {"nodes": [{"name": label} for label in labels]},
    }


def test_requires_a_closing_issue():
    assert MODULE.validate(POLICY, response([]))


def test_accepts_exactly_one_requirement_project():
    label = POLICY["requirementProjects"][1]["label"]
    assert MODULE.validate(POLICY, response([issue(171, [label])])) == []


def test_rejects_ambiguous_requirement_projects():
    labels = [item["label"] for item in POLICY["requirementProjects"][:2]]
    errors = MODULE.validate(POLICY, response([issue(171, labels)]))
    assert "exactly one" in errors[0]
