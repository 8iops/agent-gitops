from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CLIENT_ID = "5e150902-f015-5c2d-b962-049f71900311"


def oauth2_proxy(path: Path) -> dict:
    documents = list(yaml.safe_load_all(path.read_text()))
    deployment = next(
        item
        for item in documents
        if item
        and item.get("kind") == "Deployment"
        and item.get("metadata", {}).get("name") == "oauth2-proxy-cube"
    )
    container = next(
        item
        for item in deployment["spec"]["template"]["spec"]["containers"]
        if item["name"] == "oauth2-proxy"
    )
    return container


def test_cube_oauth_client_is_public_pkce_in_flat_and_release_manifests():
    paths = (
        ROOT / "clusters/re8ch/resources.yaml",
        ROOT / "releases/agent-runtime-domain-cube-trial/resources.yaml",
    )
    for path in paths:
        container = oauth2_proxy(path)
        args = container["args"]
        assert f"--client-id={CLIENT_ID}" in args
        assert "--client-secret=" in args
        assert "--code-challenge-method=S256" in args
        assert "--oidc-issuer-url=https://db-rw.re8ch.com/auth/v1" in args
        assert "envFrom" not in container
        assert container["env"] == [
            {
                "name": "OAUTH2_PROXY_COOKIE_SECRET",
                "valueFrom": {"secretKeyRef": {
                    "key": "OAUTH2_PROXY_COOKIE_SECRET",
                    "name": "oauth2-proxy-cube",
                }},
            },
        ]
