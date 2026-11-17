from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_PAGES_SHA = "d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e"


def test_pages_uses_verified_deploy_action_and_static_scope():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text()

    assert f"actions/deploy-pages@{DEPLOY_PAGES_SHA}" in workflow
    assert 'paths: ["site/**", ".github/workflows/pages.yml"]' in workflow


def test_runtime_reconcile_has_no_push_trigger():
    workflow = (ROOT / ".github/workflows/agent-runtime-reconcile.yml").read_text()
    event_block = workflow.split("permissions:", 1)[0]

    assert "schedule:" in event_block
    assert "workflow_dispatch:" in event_block
    assert "push:" not in event_block
