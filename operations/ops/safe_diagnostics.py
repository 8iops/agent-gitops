"""Bounded error metadata; never serialize request or exception contents."""
import json
import secrets

TOOL_NAMES = frozenset({"postgres_admin_sql", "get_observability_platform_status", "kubectl_exec"})
ERROR_CLASSES = frozenset({"TimeoutError", "ConnectionError", "ConnectionResetError", "ConnectionRefusedError", "BrokenPipeError", "OSError", "URLError", "HTTPError", "SSLError", "SSLCertVerificationError", "ValueError", "TypeError", "KeyError", "RuntimeError", "PgProtocolError"})

def report_failure(exc, request=None):
    request_id = secrets.token_hex(12)
    tool = "unknown"
    if isinstance(request, dict) and request.get("method") == "tools/call":
        params = request.get("params")
        if isinstance(params, dict) and isinstance(params.get("name"), str) and params["name"] in TOOL_NAMES:
            tool = params["name"]
    name = type(exc).__name__
    row = {"event": "ops_mcp_request_failed", "requestId": request_id,
           "exceptionClass": name if name in ERROR_CLASSES else "OtherError", "toolName": tool}
    print(json.dumps(row, sort_keys=True), flush=True)
    return request_id
