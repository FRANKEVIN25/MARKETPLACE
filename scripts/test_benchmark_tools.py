"""Small checks for error accounting and CSV aggregation."""

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))


def import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    status_code = 200

    def __init__(self, body):
        self.body = body
        self.failure_message = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def json(self):
        return self.body

    def failure(self, message):
        self.failure_message = message


class RpcAccountingTests(unittest.TestCase):
    def setUp(self):
        stub = types.ModuleType("locust")
        stub.HttpUser = type("HttpUser", (), {})
        stub.between = lambda *_: None
        hook = types.SimpleNamespace(add_listener=lambda function: function)
        stub.events = types.SimpleNamespace(spawning_complete=hook, quitting=hook)
        env = {"ODOO_ADMIN_PASS": "test", "ODOO_DB": "test"}
        self.patches = [patch.dict(sys.modules, {"locust": stub}),
                        patch.dict(os.environ, env)]
        for item in self.patches:
            item.start()
        self.module = import_file("bench_locust_test", SCRIPTS / "locustfile.py")

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()

    def test_json_rpc_error_with_http_200_is_failure(self):
        response = FakeResponse({"error": {"message": "Access denied",
                                           "data": {"name": "odoo.exceptions.AccessError"}}})
        user = self.module.BenchmarkUser()
        user.client = types.SimpleNamespace(post=lambda *_args, **_kwargs: response)
        self.assertIsNone(user._rpc("/web/dataset/call_kw", {}, "catalogue"))
        self.assertIn("AccessError", response.failure_message)

    def test_empty_required_result_is_failure(self):
        response = FakeResponse({"result": []})
        user = self.module.BenchmarkUser()
        user.client = types.SimpleNamespace(post=lambda *_args, **_kwargs: response)
        self.assertIsNone(user._rpc("/web/dataset/call_kw", {}, "stock", nonempty=True))
        self.assertIn("vacio", response.failure_message)


class SummaryTests(unittest.TestCase):
    def test_successful_operations_exclude_failures(self):
        module = import_file("bench_summary_test", SCRIPTS / "summarize_benchmark.py")
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "metadata.json").write_text(json.dumps({
                "run_id": "abc", "commit": "123", "mode": "read", "pods_expected": 2,
                "hpa": False, "users": 20, "repeat": 1,
            }), encoding="utf-8")
            (folder / "timing.json").write_text('{"measurement_seconds": 5}', encoding="utf-8")
            (folder / "final.json").write_text(json.dumps([
                {"name": "catalogue", "num_requests": 60, "num_failures": 6,
                 "total_response_time": 6000, "response_times": {"100": 54, "200": 6}},
                {"name": "stock", "num_requests": 40, "num_failures": 4,
                 "total_response_time": 4000, "response_times": {"100": 36, "200": 4}},
            ]), encoding="utf-8")
            row = module.load_run(folder)
            self.assertEqual(row["successful_rps"], 18)
            self.assertEqual(row["error_pct"], 10)
            self.assertEqual(row["p95_ms"], 200)


if __name__ == "__main__":
    unittest.main()
