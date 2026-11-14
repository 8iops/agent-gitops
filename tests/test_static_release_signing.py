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


def test_accepted_reconciliation_supports_pinned_key_and_legacy_keyless_signatures():
    text = (ROOT / ".github/workflows" / "agent-runtime-reconcile.yml").read_text()
    assert f"cosign verify --key {PUBLIC_KEY}" in text
    assert "--certificate-identity '${{ matrix.signer }}'" in text
    assert "--certificate-oidc-issuer https://token.actions.githubusercontent.com" in text


def test_runtime_executor_uses_the_pinned_public_key():
    text = (ROOT / "operations/releases/ssa_executor.py").read_text()
    assert '"--key", str(STATIC_RELEASE_COSIGN_KEY)' in text
    assert '"--insecure-ignore-tlog"' in text
    assert '"--certificate-identity", bundle["signer"]' in text
    assert '"--certificate-oidc-issuer", bundle["issuer"]' in text
