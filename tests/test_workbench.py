import json
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError

from digit_harness.server import Handler
from digit_harness.sandbox import prepare_sandbox
from digit_harness.workflow import knowledge, run


def request(folder, method, path, payload=b"", origin="http://127.0.0.1:8090"):
    """Exercise the HTTP handler with memory streams so CI needs no sockets."""
    raw = (
        f"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:8090\r\n"
        f"Origin: {origin}\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(payload)}\r\n\r\n"
    ).encode() + payload
    output = io.BytesIO()
    handler = Handler.__new__(Handler)
    handler.data = Path(folder)
    handler.rfile = io.BytesIO(raw)
    handler.wfile = output
    handler.server = SimpleNamespace(server_port=8090)
    handler.client_address = ("127.0.0.1", 0)
    handler.handle_one_request()
    headers, body = output.getvalue().split(b"\r\n\r\n", 1)
    return int(headers.split(b" ", 2)[1]), body


class WorkbenchTest(unittest.TestCase):
    def test_configuration_preserves_baseline(self):
        baseline = knowledge()["catalog"]
        result = run("Add missed pickups", "complaint-subtype", "MISSED_PICKUP", "Missed pickup")
        self.assertEqual(result["decision"]["path"], "configure")
        self.assertIn("MISSED_PICKUP", result["diff"])
        self.assertEqual(result["preview_catalog"][:-1], baseline)
        self.assertEqual(len(result["tests"]), 3)
        self.assertTrue(all(test["pass"] for test in result["tests"]))
        self.assertEqual(knowledge()["catalog"], baseline)

    def test_duplicate_and_invalid_input(self):
        for code in ("STREET_SWEEPING", "bad code"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                run("Add category", "complaint-subtype", code, "Label")

    def test_defer_unimplemented_paths(self):
        for kind in ("extension", "new-module"):
            with self.subTest(kind=kind):
                result = run("Add an inspection workflow", kind, "", "")
                self.assertEqual(result["decision"]["path"], "needs-review")
                self.assertNotIn("configuration", result)

    @patch("digit_harness.workflow.summarize")
    def test_model_advice_cannot_change_the_decision(self, summarize):
        summarize.return_value = {"status": "completed", "advice": "Build a new module"}
        result = run("Add missed pickups", "complaint-subtype", "MISSED_PICKUP", "Missed pickup", True)
        self.assertEqual(result["decision"]["path"], "configure")
        summarize.assert_called_once()

    def test_http_run_is_persisted_and_retrievable(self):
        with tempfile.TemporaryDirectory() as folder:
            status, page = request(folder, "GET", "/")
            self.assertEqual(status, 200)
            self.assertIn(b"DIGIT Development Studio", page)
            payload = json.dumps({
                "requirement": "Add missed pickups",
                "kind": "complaint-subtype",
                "code": "MISSED_PICKUP",
                "label": "Missed pickup",
            }).encode()
            status, body = request(folder, "POST", "/api/runs", payload)
            self.assertEqual(status, 201)
            document = json.loads(body)
            status, saved = request(folder, "GET", "/api/runs/" + document["run_id"])
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(saved), document)
            status, _ = request(folder, "GET", "/", origin="https://example.org")
            self.assertEqual(status, 403)

    @patch.dict("os.environ", {}, clear=True)
    def test_sandbox_unconfigured(self):
        self.assertEqual(prepare_sandbox()["status"], "unconfigured")

    @patch.dict("os.environ", {
        "HARNESS_DIGIT_TENANT": "pg.citya",
        "HARNESS_DIGIT_PGR_URL": "http://pgr-services:8080",
        "HARNESS_DIGIT_MDMS_URL": "http://mdms-backend:8094",
    })
    @patch("digit_harness.sandbox.read_document")
    def test_sandbox_reads_live_contract_and_reports_unreachable_service(self, read):
        hierarchy = {"MdmsRes": {"RAINMAKER-PGR": {
            "ComplaintHierarchyDefinition": [{"hierarchyType": "complaints"}],
            "ComplaintHierarchy": [{"hierarchyType": "complaints", "code": "Waste"}],
        }}}
        read.side_effect = [{"status": "UP"}, hierarchy, URLError("unreachable"), hierarchy]
        self.assertEqual(prepare_sandbox()["status"], "readable")
        self.assertEqual(read.call_args.args[2]["MdmsCriteria"]["tenantId"], "pg.citya")
        self.assertEqual(prepare_sandbox()["status"], "blocked")
