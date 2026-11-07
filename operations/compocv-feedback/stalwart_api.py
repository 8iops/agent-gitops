"""Shared bounded Stalwart JMAP helpers for CompoCV credential provisioning."""
import ipaddress
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


HOST = "stalwart.mail-system.svc.cluster.local:8080"
CAPABILITIES = ["urn:ietf:params:jmap:core", "urn:stalwart:jmap"]
PHASE = "initialization"
ERROR_TYPES = {
    "invalidArguments", "invalidProperties", "forbidden", "notFound",
    "serverFail", "serverUnavailable", "stateMismatch", "alreadyExists",
    "invalidResultReference", "unknownMethod", "accountNotFound",
    "accountNotSupportedByMethod", "requestTooLarge", "invalidPatch",
    "willDestroy", "singleton", "overQuota", "rateLimit", "tooLarge",
}
PROPERTY_NAMES = {
    "clientId", "secret", "description", "redirectUris", "memberTenantId",
    "contacts", "grantTypes", "postLogoutRedirectUris", "logo", "expiresAt",
}


class RegistrationError(ValueError):
    def __init__(self, code, detail=None):
        self.code = code
        self.detail = detail or {}
        super().__init__(code)


def safe_api_error(error):
    if not isinstance(error, dict):
        return {"type": "unrecognized"}
    return {
        "type": error.get("type") if error.get("type") in ERROR_TYPES else "unrecognized",
        "invalidProperties": sorted(
            item for item in error.get("properties", [])
            if isinstance(item, str) and item in PROPERTY_NAMES
        ),
    }


def failure_report(error):
    report = {
        "outcome": "failed",
        "phase": PHASE,
        "reason": "credential-bearing diagnostics withheld",
    }
    if isinstance(error, RegistrationError):
        report.update({"code": error.code, **error.detail})
    elif isinstance(error, HTTPError):
        report["httpStatus"] = error.code
    return report


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def internal_api_url(session, base):
    url = urlsplit(session["apiUrl"])
    if url.path.rstrip("/") != "/jmap" or url.query or url.fragment:
        raise ValueError("unexpected JMAP endpoint")
    return base + url.path
