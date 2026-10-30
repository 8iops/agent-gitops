import copy
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stalwart_provider_preflight", ROOT / "operations/stalwart-self-service/provider_preflight.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def evidence():
    schema = {
        "fields": {"x:OAuthClient": {"properties": {
            "grantTypes": {"type": {"type": "set", "class": {"type": "enum", "enumName": "OAuthGrantType"}}},
            "firstParty": {"type": {"type": "boolean"}},
            "scopes": {"type": {"type": "set", "class": {"type": "enum", "enumName": "OAuthScope"}}},
        }}},
        "enums": {"OAuthGrantType": [{"name": grant} for grant in sorted(gate.CLIENT_GRANTS)], "OAuthScope": [{"name": service} for service in sorted(gate.SERVICES)]},
    }
    metadata = {
        "issuer": "https://id.re8ch.com",
        "device_authorization_endpoint": "https://id.re8ch.com/auth/device",
        "token_endpoint": "https://id.re8ch.com/auth/token",
        "grant_types_supported": [gate.DEVICE_GRANT],
        "scopes_supported": [gate.SCOPE_PREFIX + service for service in gate.SERVICES],
    }
    return schema, metadata


def test_declared_v01618_without_scoped_oauth_client_is_rejected():
    # Official v0.16.18 schema has no firstParty/scopes properties. Do not
    # backport current online documentation into an incompatible deployment.
    schema, metadata = evidence()
    schema["fields"]["x:OAuthClient"]["properties"] = {"clientId": {"type": {"type": "string"}}}
    with pytest.raises(ValueError):
        gate.validate(schema, metadata, "https://id.re8ch.com")


@pytest.mark.parametrize("field,value", [
    ("device_authorization_endpoint", "https://evil.example/auth/device"),
    ("token_endpoint", "http://id.re8ch.com/auth/token"),
    ("token_endpoint", "https://user:password@id.re8ch.com/auth/token"),
    ("issuer", "https://another.example"),
    ("grant_types_supported", []),
    ("scopes_supported", ["openid"]),
])
def test_untrusted_or_incomplete_provider_evidence_is_rejected(field, value):
    schema, metadata = evidence()
    metadata[field] = value
    with pytest.raises(ValueError):
        gate.validate(schema, metadata, "https://id.re8ch.com")


def test_supported_schema_does_not_activate_or_replace_token_isolation_probe():
    schema, metadata = evidence()
    before = copy.deepcopy((schema, metadata))
    result = gate.validate(schema, metadata, "https://id.re8ch.com")
    assert result["activationAllowed"] is False
    assert result["tokenIsolationProbeRequired"] is True
    assert result["nativeDryRunRequired"] is True
    assert (schema, metadata) == before


def test_candidate_registration_is_unprivileged_and_not_in_runtime_root():
    candidate = json.loads((ROOT / "operations/stalwart-self-service/oauth-client.candidate.ndjson").read_text())
    value = candidate["value"][gate.CLIENT_ID]
    assert value["clientId"] == gate.CLIENT_ID
    assert value["firstParty"] is False
    assert value["scopes"] == {service: True for service in gate.SERVICES}
    assert value["grantTypes"] == {grant: True for grant in gate.CLIENT_GRANTS}
    assert value["redirectUris"] == {}
    assert "secret" not in value
    env = (ROOT / "operations/stalwart-self-service/tenant-runtime.env.example").read_text()
    assert "COLLABORATION_ENABLED=false" in env
    root = yaml.safe_load((ROOT / "clusters/re8ch/kustomization.yaml").read_text())
    assert all("stalwart-self-service" not in name for name in root["resources"])


@pytest.mark.parametrize("missing", ["grantTypes", "deviceCode"])
def test_missing_client_grant_support_is_rejected(missing):
    schema, metadata = evidence()
    if missing == "grantTypes":
        del schema["fields"]["x:OAuthClient"]["properties"][missing]
    else:
        schema["enums"]["OAuthGrantType"] = [entry for entry in schema["enums"]["OAuthGrantType"] if entry["name"] != missing]
    with pytest.raises(ValueError):
        gate.validate(schema, metadata, "https://id.re8ch.com")
