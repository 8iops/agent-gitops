import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "operations/releases"))
import probe_re8ch_mcp as probe


class Response:
    def __init__(self, status, body=b""):
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, _limit):
        return self.body


def test_public_probe_requires_metadata_and_anonymous_rejection():
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, request.data, timeout))
        if request.full_url == probe.METADATA:
            return Response(200, json.dumps({"resource": probe.RESOURCE}).encode())
        raise probe.urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", {}, io.BytesIO(b""))

    assert probe.probe(opener) == (
        True, "RFC9728 metadata and protected MCP response are healthy")
    assert [item[0] for item in calls] == [probe.METADATA, probe.RESOURCE]


def test_public_probe_fails_closed_on_wrong_resource():
    def opener(_request, timeout):
        assert timeout == 10
        return Response(200, b'{"resource":"https://example.invalid/mcp"}')

    assert probe.probe(opener) == (
        False, "protected-resource metadata names a different resource")
