#!/usr/bin/env python3
"""Validate the Project -> Issue -> pull request requirement relationship."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.request import Request, urlopen


QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      closingIssuesReferences(first: 20) {
        nodes {
          number
          url
          labels(first: 100) { nodes { name } }
        }
      }
    }
  }
}
"""


def validate(policy: dict, response: dict) -> list[str]:
    allowed = {item["label"]: item for item in policy["requirementProjects"]}
    pull_request = response.get("data", {}).get("repository", {}).get("pullRequest")
    if not pull_request:
        return ["GitHub did not return the pull request"]
    issues = pull_request.get("closingIssuesReferences", {}).get("nodes", [])
    if not issues:
        return ["pull request must close at least one Issue (for example: Closes #171)"]

    errors = []
    for issue in issues:
        labels = [
            node["name"]
            for node in issue.get("labels", {}).get("nodes", [])
            if node.get("name") in allowed
        ]
        if len(labels) != 1:
            names = ", ".join(labels) or "none"
            errors.append(
                f'Issue #{issue["number"]} must have exactly one requirement Project '
                f"label; found: {names}"
            )
    return errors


def query_github(owner: str, name: str, number: int, token: str) -> dict:
    payload = json.dumps(
        {"query": QUERY, "variables": {"owner": owner, "name": name, "number": number}}
    ).encode()
    request = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "agent-gitops-context-validator",
        },
    )
    with urlopen(request, timeout=20) as result:
        response = json.load(result)
    if response.get("errors"):
        raise RuntimeError(json.dumps(response["errors"], sort_keys=True))
    return response


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--policy", type=Path, default=Path("governance/context.json"))
    args = parser.parse_args()

    event = json.loads(args.event.read_text())
    policy = json.loads(args.policy.read_text())
    repository = event["repository"]["full_name"]
    owner, name = repository.split("/", 1)
    number = int(event["pull_request"]["number"])
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("GH_TOKEN is required", file=sys.stderr)
        return 2

    try:
        response = query_github(owner, name, number, token)
    except Exception as error:
        print(f"unable to read pull request context: {error}", file=sys.stderr)
        return 2
    errors = validate(policy, response)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"validated requirement context for {repository}#{number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
