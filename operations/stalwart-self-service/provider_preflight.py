"""Offline compatibility gate over reviewed provider discovery evidence.

Reads sanitized schema/metadata files; never fetches credentials, writes provider
state or enables the application. A successful result permits native dry-run,
not production activation or a claim that token isolation has been verified.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

SERVICES = {"mail", "calendars", "files"}
SCOPE_PREFIX = "urn:ietf:params:oauth:scope:"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
CLIENT_GRANTS = {"deviceCode"}
CLIENT_ID = "re8ch-self-service"


def validate(schema, metadata, origin):
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise ValueError("provider origin must be an HTTPS origin without credentials")
    fields = schema.get("fields", {}).get("x:OAuthClient", {}).get("properties", {})
    if fields.get("firstParty", {}).get("type", {}).get("type") != "boolean":
        raise ValueError("provider schema lacks explicit non-first-party OAuth clients")
    scope_type = fields.get("scopes", {}).get("type", {})
    if scope_type.get("type") != "set" or scope_type.get("class", {}).get("enumName") != "OAuthScope":
        raise ValueError("provider schema lacks service-scoped OAuth clients")
    grant_type = fields.get("grantTypes", {}).get("type", {})
    if grant_type.get("type") != "set" or grant_type.get("class", {}).get("enumName") != "OAuthGrantType":
        raise ValueError("provider schema lacks explicit client grant selection")
    grants = {entry.get("name") for entry in schema.get("enums", {}).get("OAuthGrantType", [])}
    if not CLIENT_GRANTS <= grants:
        raise ValueError("provider schema lacks required device grant")
    enum = {entry.get("name") for entry in schema.get("enums", {}).get("OAuthScope", [])}
    if not SERVICES <= enum:
        raise ValueError("provider schema lacks the required collaboration scopes")
    if not {SCOPE_PREFIX + service for service in SERVICES} <= set(metadata.get("scopes_supported", [])):
        raise ValueError("provider metadata does not advertise the required scopes")
    if DEVICE_GRANT not in metadata.get("grant_types_supported", []):
        raise ValueError("provider metadata does not advertise device authorization")
    if metadata.get("issuer", "").rstrip("/") != origin.rstrip("/"):
        raise ValueError("provider issuer differs from the reviewed origin")
    for field in ("device_authorization_endpoint", "token_endpoint"):
        endpoint = urlsplit(metadata.get(field, ""))
        if (endpoint.scheme, endpoint.netloc) != (parsed.scheme, parsed.netloc) or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            raise ValueError("provider OAuth endpoint is outside the reviewed origin")
    return {
        "compatibility": "candidate",
        "clientId": CLIENT_ID,
        "nativeDryRunRequired": True,
        "tokenIsolationProbeRequired": True,
        "activationAllowed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--origin", default="https://id.re8ch.com")
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.schema.read_text()), json.loads(args.metadata.read_text()), args.origin)
    except (ValueError, TypeError, AttributeError, KeyError, OSError):
        # Schema/metadata input is untrusted and may contain server details. Do
        # not copy it or arbitrary parse-error excerpts into release logs.
        raise SystemExit("provider compatibility gate failed; keep collaboration disabled")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
