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
        stub.events = types.SimpleNamespace(test_start=hook, quitting=hook)
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

    def test_non_object_json_is_failure(self):
        response = FakeResponse([])
        user = self.module.BenchmarkUser()
        user.client = types.SimpleNamespace(post=lambda *_args, **_kwargs: response)
        self.assertIsNone(user._rpc('/web/dataset/call_kw', {}, 'catalogue'))
        self.assertIn('objeto', response.failure_message)


class ProtocolTests(unittest.TestCase):
    def test_company_allocation_matches_target_concurrency(self):
        from benchmark_protocol import company_plan
        from collections import Counter
        for users in (1, 20, 50, 100, 200):
            plan = company_plan(users)
            self.assertEqual(len(plan), users)
            counts = Counter(plan)
            for letter, weight in zip('ABC', (1, 2, 3)):
                self.assertLess(abs(counts[letter] - users*weight/6), 1)
            self.assertEqual(plan, company_plan(users))

    def test_configuration_drift_changes_comparison_family(self):
        from benchmark_protocol import fingerprint
        self.assertNotEqual(fingerprint({'cpu': '500m'}, {'warmup': 30}),
                            fingerprint({'cpu': '1000m'}, {'warmup': 30}))
        self.assertNotEqual(fingerprint({'cpu': '500m'}, {'warmup': 30}),
                            fingerprint({'cpu': '500m'}, {'warmup': 0}))
        self.assertEqual(fingerprint({'cpu': '500m', 'memory': '768Mi'}, {}),
                         fingerprint({'memory': '768Mi', 'cpu': '500m'}, {}))


class SummaryTests(unittest.TestCase):
    def test_protocol_two_rejects_changed_configuration(self):
        from benchmark_protocol import VERSION, company_plan, comparison_policy, fingerprint
        from collections import Counter
        module = import_file('bench_summary_strict', SCRIPTS / 'summarize_benchmark.py')
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            metadata = {'run_id':'strict','commit':'abc','mode':'read','pods_expected':2,
                'hpa':False,'users':20,'repeat':1,'protocol_version':VERSION,'purpose':'smoke',
                'spawn_rate':5,'warmup_seconds':5,'duration_seconds':30,'seed':2026,
                'company_weights':'1:2:3','read_mix':'3:2','locust_script_sha256':'a',
                'protocol_script_sha256':'b','runner_script_sha256':'c','experiment_id':'test',
                'request_connection':'close','configuration':{'cpu':'500m'}}
            metadata['comparison_signature'] = fingerprint(metadata['configuration'], comparison_policy(metadata))
            (folder/'metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
            (folder/'timing.json').write_text(json.dumps({'valid':True,'measurement_seconds':30,
                'prepared_users':20,'minimum_users_during_measurement':20,'setup_failures':0,
                'company_users':dict(Counter(company_plan(20)))}), encoding='utf-8')
            (folder/'final.json').write_text(json.dumps([
                {'name':name,'num_requests':20,'num_failures':0,'total_response_time':200,
                 'response_times':{'10':20}} for name in ('catalogue','stock')]), encoding='utf-8')
            self.assertFalse(module.load_run(folder)['comparison_eligible'])
            metadata['configuration']['cpu'] = '1000m'
            (folder/'metadata.json').write_text(json.dumps(metadata), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'firma'):
                module.load_run(folder)

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
