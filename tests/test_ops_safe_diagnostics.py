import contextlib
import importlib.util
import io
import json
import pathlib
import unittest
import yaml
from urllib.error import URLError

PATH = pathlib.Path(__file__).parents[1] / "operations/ops/safe_diagnostics.py"
SPEC = importlib.util.spec_from_file_location("safe_diagnostics", PATH)
DIAG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DIAG)

class SafeDiagnosticsTests(unittest.TestCase):
    def capture(self, error, request):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            request_id = DIAG.report_failure(error, request)
        self.assertRegex(request_id, r"^[0-9a-f]{24}$")
        return json.loads(stream.getvalue())

    def test_delivered_helper_matches_reviewed_source_in_both_cohorts(self):
        root = PATH.parents[2]
        for relative in ["clusters/re8ch/resources.yaml", "releases/agent-runtime-domain-toolhive-system/resources.yaml"]:
            docs = yaml.safe_load_all((root / relative).read_text())
            cm = next(d for d in docs if d and d.get("metadata", {}).get("name") == "ops-mcp-server-code")
            self.assertEqual(cm["data"]["safe_diagnostics.py"], PATH.read_text())
            self.assertTrue(cm["data"]["app.py"].startswith("ENC[AES256_GCM,"))

    def test_timeout_class_and_reviewed_tool_without_sensitive_content(self):
        row = self.capture(URLError("token=DO-NOT-LOG"), {"id": "sensitive-user-id", "method": "tools/call", "params": {"name": "postgres_admin_sql", "arguments": {"sql": "PRIVATE SQL", "password": "PRIVATE"}}})
        self.assertEqual(row["exceptionClass"], "URLError")
        self.assertEqual(row["toolName"], "postgres_admin_sql")
        self.assertEqual(set(row), {"event", "requestId", "exceptionClass", "toolName"})
        self.assertNotIn("PRIVATE", json.dumps(row))
        self.assertNotIn("sensitive", json.dumps(row))
        self.assertNotIn("DO-NOT-LOG", json.dumps(row))

    def test_malformed_request_and_unreviewed_names_cannot_enter_logs(self):
        for request in [None, [], {"method": "tools/call", "params": []}, {"method": "tools/call", "params": {"name": []}}, {"method": "tools/call", "params": {"name": "secret-token"}}]:
            row = self.capture(type("SensitiveClassName", (Exception,), {})("secret"), request)
            self.assertEqual(row["toolName"], "unknown")
            self.assertEqual(row["exceptionClass"], "OtherError")

if __name__ == "__main__":
    unittest.main()
