from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
RELEASE = ROOT / "releases/agent-runtime-domain-llm-gateway/resources.yaml"


def test_litellm_uses_userhub_gotrue_confidential_client():
    deployment = next(
        item
        for item in yaml.safe_load_all(RELEASE.read_text())
        if item and item.get("kind") == "Deployment" and item["metadata"]["name"] == "litellm"
    )
    container = next(item for item in deployment["spec"]["template"]["spec"]["containers"] if item["name"] == "litellm")
    env = {item["name"]: item for item in container["env"]}

    assert env["GENERIC_CLIENT_ID"]["valueFrom"]["secretKeyRef"] == {
        "key": "client-id",
        "name": "litellm-gotrue-sso",
    }
    assert env["GENERIC_CLIENT_SECRET"]["valueFrom"]["secretKeyRef"] == {
        "key": "client-secret",
        "name": "litellm-gotrue-sso",
    }
    assert env["GENERIC_AUTHORIZATION_ENDPOINT"]["value"] == "https://db-rw.re8ch.com/auth/v1/oauth/authorize"
    assert env["GENERIC_TOKEN_ENDPOINT"]["value"] == "https://db-rw.re8ch.com/auth/v1/oauth/token"
    assert env["GENERIC_USERINFO_ENDPOINT"]["value"] == "https://db-rw.re8ch.com/auth/v1/user"
    assert env["GENERIC_CLIENT_USE_PKCE"]["value"] == "true"
    assert env["GENERIC_USER_ID_ATTRIBUTE"]["value"] == "sub"
    assert env["GENERIC_USER_EMAIL_ATTRIBUTE"]["value"] == "email"
    assert env["AUTO_REDIRECT_UI_LOGIN_TO_SSO"]["value"] == "true"
    assert "dex" not in RELEASE.read_text().lower()
