from pathlib import Path
from urllib.parse import urlparse

import yaml


ROOT = Path(__file__).resolve().parents[1]
ISSUER = "https://db-rw.re8ch.com/auth/v1"
CLIENT_ID = "5e150902-f015-5c2d-b962-049f71900311"
CALLBACK = "https://cube.service.re8ch.com/oauth2/callback"
SSO_IMAGE_REVISION = "8b5f09bd01bd35e077a9d9601340e617cc101a2f"


def test_cube_uses_only_supabase_gotrue_oauth():
    docs = list(yaml.safe_load_all(
        (ROOT / "releases/agent-runtime-domain-cube-trial/resources.yaml").read_text()
    ))
    deployment = next(
        item for item in docs
        if item["kind"] == "Deployment"
        and item["metadata"]["name"] == "oauth2-proxy-cube"
    )
    route = next(item for item in docs if item["kind"] == "HTTPRoute")
    pod = deployment["spec"]["template"]["spec"]
    container = pod["containers"][0]
    args = dict(
        argument[2:].split("=", 1)
        for argument in container["args"]
        if argument.startswith("--") and "=" in argument
    )

    assert args["oidc-issuer-url"] == ISSUER
    assert args["client-id"] == CLIENT_ID
    assert "client-secret" not in args
    assert args["code-challenge-method"] == "S256"
    assert args["oidc-extra-audience"] == "authenticated"
    assert args["scope"] == "openid profile email offline_access"
    assert args["redirect-url"] == CALLBACK
    assert urlparse(CALLBACK).hostname in route["spec"]["hostnames"]
    assert pod["automountServiceAccountToken"] is False
    assert deployment["metadata"]["namespace"] == "cube-trial"

    skip_routes = [
        argument.split("=", 1)[1]
        for argument in container["args"]
        if argument.startswith("--skip-auth-route=")
    ]
    assert skip_routes == [
        "GET=^/$",
        "GET=^/login(?:[/?].*)?$",
        "GET=^/assets/.*$",
    ]
    assert all("/opsapi" not in route for route in skip_routes)

    cube_ops = next(
        item for item in docs
        if item["kind"] == "Deployment"
        and item["metadata"]["name"] == "cube-recovery-ops"
    )
    cube_webui = next(
        item for item in docs
        if item["kind"] == "Deployment"
        and item["metadata"]["name"] == "cube-recovery-webui"
    )
    ops_image = cube_ops["spec"]["template"]["spec"]["containers"][0]["image"]
    webui_image = cube_webui["spec"]["template"]["spec"]["containers"][0]["image"]
    assert f":{SSO_IMAGE_REVISION}@sha256:" in ops_image
    assert f":{SSO_IMAGE_REVISION}@sha256:" in webui_image


def test_retired_cube_oauth_plans_are_absent():
    assert not (ROOT / "operations/identity/cube-stalwart-migration.yaml").exists()
    rendered = (
        ROOT / "releases/agent-runtime-domain-cube-trial/resources.yaml"
    ).read_text()
    assert "--oidc-issuer-url=https://auth.re8ch.com" not in rendered
    assert "--oidc-issuer-url=https://id.re8ch.com" not in rendered
    assert "--scope=openid profile email groups" not in rendered
