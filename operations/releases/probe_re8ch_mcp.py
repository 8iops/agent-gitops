#!/usr/bin/env python3
"""Bounded public probe for the canonical RE8CH MCP route.

The probe intentionally uses no credential. A healthy protected endpoint must
publish RFC9728 metadata and reject an anonymous MCP initialize request.
"""
import argparse
import json
import time
import urllib.error
import urllib.request


ORIGIN = "https://tools.service.re8ch.com"
RESOURCE = f"{ORIGIN}/tenant-native/mcp"
METADATA = f"{ORIGIN}/.well-known/oauth-protected-resource/tenant-native/mcp"


def request(url, *, data=None, opener=urllib.request.urlopen):
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        with opener(urllib.request.Request(url, data=data, headers=headers), timeout=10) as response:
            return response.status, response.read(65536)
    except urllib.error.HTTPError as error:
        return error.code, error.read(65536)


def probe(opener=urllib.request.urlopen):
    status, body = request(METADATA, opener=opener)
    if status != 200:
        return False, f"protected-resource metadata returned HTTP {status}"
    try:
        metadata = json.loads(body)
    except (TypeError, ValueError):
        return False, "protected-resource metadata is not JSON"
    if metadata.get("resource") != RESOURCE:
        return False, "protected-resource metadata names a different resource"
    payload = json.dumps({
        "jsonrpc": "2.0", "id": "public-readiness",
        "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "release-readiness", "version": "1"},
        },
    }).encode()
    status, _ = request(RESOURCE, data=payload, opener=opener)
    if status != 401:
        return False, f"anonymous MCP initialize returned HTTP {status}, expected 401"
    return True, "RFC9728 metadata and protected MCP response are healthy"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout
    while True:
        healthy, reason = probe()
        if healthy:
            print(reason)
            return 0
        if time.monotonic() >= deadline:
            print(reason)
            return 1
        time.sleep(min(5, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    raise SystemExit(main())
