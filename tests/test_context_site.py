import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_cross_org_context_and_pages_are_public_safe():
    context = json.loads((ROOT / "governance/cross-org-context.json").read_text())
    html = (ROOT / "site/index.html").read_text()
    assert context["repository"] == "8iops/agent-gitops"
    assert len(context["relatedRepositories"]) >= 3
    for value in ("canonical", "application/ld+json", "https://re8ch.com/", "Observability Wiki"):
        assert value in html
    for value in ("kubectl get", "Secret/data", "10.251.", "223.159."):
        assert value not in html
