from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_KEY = "operations/releases/keys/static-release-cosign.pub"


def test_static_release_uses_repository_controlled_key_without_public_transparency_log():
    workflow = yaml.safe_load((ROOT / ".github/workflows/static-release.yml").read_text())
    compile_job = workflow["jobs"]["compile-sign"]
    publish = next(step for step in compile_job["steps"] if step.get("id") == "publish")
    script = publish["run"]

    assert compile_job["permissions"] == {"contents": "read", "packages": "write"}
    assert publish["env"]["COSIGN_PRIVATE_KEY"] == "${{ secrets.COSIGN_PRIVATE_KEY }}"
    assert publish["env"]["COSIGN_PASSWORD"] == "${{ secrets.COSIGN_PASSWORD }}"
    assert "cosign sign --yes --key env://COSIGN_PRIVATE_KEY --tlog-upload=false" in script
    assert f"cosign verify --key {PUBLIC_KEY}" in script
    assert "--insecure-ignore-tlog" in script
    assert "certificate-identity" not in script
    assert "certificate-oidc-issuer" not in script


def test_every_release_reconciliation_uses_the_same_pinned_public_key():
    for name in ("static-release.yml", "agent-runtime-reconcile.yml"):
        text = (ROOT / ".github/workflows" / name).read_text()
        assert "cosign sign --yes \"$immutable\"" not in text
        assert "certificate-identity" not in text
        assert "certificate-oidc-issuer" not in text
        assert f"cosign verify --key {PUBLIC_KEY}" in text


def test_runtime_executor_uses_the_pinned_public_key():
    text = (ROOT / "operations/releases/ssa_executor.py").read_text()
    assert '"--key", str(STATIC_RELEASE_COSIGN_KEY)' in text
    assert '"--insecure-ignore-tlog"' in text
    assert '"--certificate-identity"' not in text
