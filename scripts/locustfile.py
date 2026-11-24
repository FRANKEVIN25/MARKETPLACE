"""Odoo multi-company workload. Set BENCH_MODE=read or write.

Use -H http://odoo:8069 from a Pod in namespace ecomparts. Host-side
port-forward is useful for a smoke test, but pins traffic to one Pod.
"""

import os
import random
import json
from pathlib import Path
import time
import uuid

from locust import HttpUser, between, events
import requests

from verify_odoo_lab import config
from benchmark_protocol import VERSION, company_plan


def settings():
    if os.environ.get("ODOO_ADMIN_PASS"):
        return dict(os.environ)
    return config(os.environ.get("ECOMPARTS_ENV_FILE", ".env.k8s"))


VALUES = settings()
MODE = os.environ.get("BENCH_MODE", "read")
if MODE not in ("read", "write"):
    raise ValueError("BENCH_MODE debe ser read o write")
RUN_ID = os.environ.get("BENCH_RUN_ID", "")
if MODE == "write" and (not RUN_ID or not RUN_ID.isalnum()):
    raise ValueError("BENCH_RUN_ID alfanumerico es obligatorio para escrituras")
TARGET_USERS = int(os.environ.get('BENCH_USERS', '20'))
WARMUP = int(os.environ.get('BENCH_WARMUP_SECONDS', '30'))
DURATION = int(os.environ.get('BENCH_MEASURE_SECONDS', '300'))
SEED = int(os.environ.get('BENCH_SEED', '2026'))
PLAN = company_plan(TARGET_USERS)
NEXT_USER = 0
READY = {}
ACTIVE = set()
WORKLOAD_AT = None
SETUP_FAILURES = 0
PROTOCOL = {'protocol_version': VERSION, 'valid': False, 'phase': 'startup', 'phases': []}
MEASURING = False
random.seed(SEED)


def phase(name):
    from datetime import datetime, timezone
    PROTOCOL['phase'] = name
    PROTOCOL['phases'].append({'phase': name, 'at_utc': datetime.now(timezone.utc).isoformat()})
    output = os.environ.get('BENCH_PHASE_FILE')
    if output:
        Path(output).write_text(json.dumps(PROTOCOL) + '\n', encoding='utf-8')


@events.test_start.add_listener
def start_protocol(environment, **kwargs):
    import gevent

    def control():
        global MEASURING, WORKLOAD_AT
        phase('session_preparation')
        deadline = time.monotonic() + max(180, TARGET_USERS / max(1, float(os.environ.get('BENCH_SPAWN_RATE', '5')))+120)
        while len(READY) != TARGET_USERS or environment.runner.user_count != TARGET_USERS:
            if SETUP_FAILURES or time.monotonic() > deadline:
                PROTOCOL['invalid_reason'] = 'User preparation failed or target concurrency was not reached'
                environment.process_exit_code = 2
                environment.runner.quit()
                return
            gevent.sleep(.2)
        PROTOCOL['prepared_users'] = len(READY)
        PROTOCOL['company_users'] = {letter: list(READY.values()).count(letter) for letter in 'ABC'}
        WORKLOAD_AT = time.monotonic()
        phase('workload_ramp')
        ramp_deadline = WORKLOAD_AT + TARGET_USERS/max(1, float(os.environ.get('BENCH_SPAWN_RATE', '5'))) + 30
        while len(ACTIVE) != TARGET_USERS:
            if SETUP_FAILURES or time.monotonic() > ramp_deadline:
                PROTOCOL['invalid_reason'] = 'Workload ramp failed to reach target concurrency'
                environment.process_exit_code = 2
                environment.runner.quit()
                return
            gevent.sleep(.1)
        phase('warmup')
        gevent.sleep(WARMUP)
        if SETUP_FAILURES or len(ACTIVE) != TARGET_USERS:
            PROTOCOL['invalid_reason'] = 'Concurrency changed during warmup'
            environment.process_exit_code = 2
            environment.runner.quit()
            return
        environment.stats.reset_all()
        PROTOCOL['started_monotonic'] = time.monotonic()
        PROTOCOL['warmup_seconds'] = WARMUP
        PROTOCOL['requested_measurement_seconds'] = DURATION
        PROTOCOL['minimum_users_during_measurement'] = TARGET_USERS
        MEASURING = True
        phase('measurement')
        deadline = PROTOCOL['started_monotonic'] + DURATION
        while time.monotonic() < deadline:
            count = min(len(ACTIVE), environment.runner.user_count)
            PROTOCOL['minimum_users_during_measurement'] = min(PROTOCOL['minimum_users_during_measurement'], count)
            gevent.sleep(min(.25, max(0, deadline-time.monotonic())))
        MEASURING = False
        PROTOCOL['measurement_seconds'] = round(time.monotonic()-PROTOCOL['started_monotonic'], 3)
        PROTOCOL['valid'] = (not SETUP_FAILURES and PROTOCOL['minimum_users_during_measurement'] == TARGET_USERS)
        phase('finished')
        environment.runner.quit()

    gevent.spawn(control)


@events.quitting.add_listener
def record_measurement_end(environment, **kwargs):
    output = os.environ.get("BENCH_TIMING_FILE")
    PROTOCOL['setup_failures'] = SETUP_FAILURES
    PROTOCOL['users'] = TARGET_USERS
    if not PROTOCOL.get('valid') or environment.stats.total.num_requests < 1:
        PROTOCOL['valid'] = False
        environment.process_exit_code = 2
    if output:
        record = {key: value for key, value in PROTOCOL.items() if key != 'started_monotonic'}
        Path(output).write_text(json.dumps(record) + '\n', encoding='utf-8')


class EcompartsUser(HttpUser):
    abstract = True
    wait_time = between(0.1, 0.5)

    def _setup_rpc(self, session, path, params):
        payload = {"jsonrpc": "2.0", "method": "call", "id": uuid.uuid4().hex, "params": params}
        response = session.post(self.host.rstrip("/") + path, json=payload, timeout=30)
        response.raise_for_status()
        body = response.json()
        if body.get("error") or "result" not in body:
            raise RuntimeError("Fallo la preparacion de sesion o datos BENCH en Odoo")
        return body["result"]

    def _setup_execute(self, session, model, method, args, **kwargs):
        return self._setup_rpc(session, "/web/dataset/call_kw", {
            "model": model, "method": method, "args": args, "kwargs": kwargs,
        })

    def _rpc(self, path, params, name, nonempty=False):
        payload = {"jsonrpc": "2.0", "method": "call", "id": uuid.uuid4().hex, "params": params}
        with self.client.post(path, json=payload, name=name, catch_response=True, timeout=30) as response:
            try:
                body = response.json()
            except ValueError:
                response.failure(f"Respuesta no JSON, HTTP {response.status_code}")
                return None
            if not isinstance(body, dict):
                response.failure('Respuesta JSON-RPC no es un objeto')
                return None
            if response.status_code >= 400:
                response.failure(f"HTTP {response.status_code}")
                return None
            if body.get("error"):
                details = body["error"].get("data") or {}
                response.failure("JSON-RPC: " + str(details.get("name") or body["error"].get("message", "error")))
                return None
            if "result" not in body or (nonempty and not body["result"]):
                response.failure("Resultado JSON-RPC ausente o vacio")
                return None
            return body.get("result")

    def _execute(self, model, method, args, name, nonempty=False, **kwargs):
        return self._rpc("/web/dataset/call_kw", {
            "model": model, "method": method, "args": args, "kwargs": kwargs,
        }, name, nonempty=nonempty)

    def on_start(self):
        global NEXT_USER, SETUP_FAILURES
        self.bench_index = NEXT_USER
        NEXT_USER += 1
        self.letter = PLAN[self.bench_index]
        for attempt in range(3):
            try:
                self._prepare()
                READY[self.bench_index] = self.letter
                import gevent
                while WORKLOAD_AT is None:
                    gevent.sleep(.05)
                offset = self.bench_index/max(1, float(os.environ.get('BENCH_SPAWN_RATE', '5')))
                gevent.sleep(max(0, WORKLOAD_AT+offset-time.monotonic()))
                ACTIVE.add(self.bench_index)
                return
            except Exception as error:
                setup = getattr(self, '_setup_connection', None)
                if setup:
                    setup.close()
                PROTOCOL.setdefault('setup_attempt_errors', []).append({
                    'user_index': self.bench_index, 'company': self.letter,
                    'attempt': attempt+1, 'error_type': type(error).__name__})
                if attempt < 2:
                    import gevent
                    gevent.sleep(2*(attempt+1))
        from locust.exception import StopUser
        SETUP_FAILURES += 1
        raise StopUser()

    def on_stop(self):
        READY.pop(getattr(self, 'bench_index', -1), None)
        ACTIVE.discard(getattr(self, 'bench_index', -1))

    def _prepare(self):
        login = f"lab-{self.letter.lower()}@ecomparts.local"
        password = VALUES["ODOO_ADMIN_PASS"] + "-" + self.letter
        setup = requests.Session()
        self._setup_connection = setup
        setup.trust_env = False
        session = self._setup_rpc(setup, "/web/session/authenticate", {
            "db": VALUES["ODOO_DB"], "login": login, "password": password,
        })
        if not session or not session.get("uid"):
            raise RuntimeError(f"Login fallido de la compania {self.letter}")
        self.uid = session["uid"]
        companies = self._setup_execute(setup, "res.users", "read", [[self.uid]],
                                        fields=["company_id", "company_ids"])
        if not companies or len(companies[0]["company_ids"]) != 1:
            raise RuntimeError(f"Usuario {self.letter} no esta aislado")
        self.company_id = companies[0]["company_id"][0]
        self.odoo_context = {"allowed_company_ids": [self.company_id], "company_id": self.company_id}
        products = self._setup_execute(setup, "product.product", "search_read", [[
            ["name", "=like", f"BENCH-{self.letter}-%"], ["company_id", "=", self.company_id],
        ]], fields=["id"], limit=100, context=self.odoo_context)
        if not products:
            raise RuntimeError("Ejecuta benchmark_dataset.py seed antes de Locust")
        self.product_ids = [row["id"] for row in products]
        if MODE == "write":
            partners = self._setup_execute(setup, "res.partner", "search_read", [[
                ["name", "=", f"BENCH-{self.letter}-CLIENTE"], ["company_id", "=", self.company_id],
            ]], fields=["id"], limit=1, context=self.odoo_context)
            warehouses = self._setup_execute(setup, "stock.warehouse", "search_read", [[
                ["company_id", "=", self.company_id],
            ]], fields=["id"], limit=1, context=self.odoo_context)
            if not partners or not warehouses:
                raise RuntimeError("Faltan cliente o almacen BENCH")
            self.partner_id = partners[0]["id"]
            self.warehouse_id = warehouses[0]["id"]
        self.client.cookies.update(setup.cookies)
        # A new TCP connection lets the Service route to newly ready Pods.
        # The session cookie stays unchanged and must work across replicas.
        self.client.headers.update({'Connection': 'close'})
        setup.close()

    def read_catalogue(self):
        self._execute("product.product", "search_read", [[
            ["id", "in", self.product_ids], ["company_id", "=", self.company_id],
        ]], "catalogue", nonempty=True, fields=["id", "name", "list_price"], limit=20, context=self.odoo_context)

    def read_stock(self):
        product_id = random.choice(self.product_ids)
        self._execute("stock.quant", "search_read", [[
            ["product_id", "=", product_id], ["quantity", ">", 0],
        ]], "stock", nonempty=True, fields=["product_id", "quantity", "company_id"], limit=10, context=self.odoo_context)

    def write_order(self):
        product_id = random.choice(self.product_ids)
        ref = f"BENCH-{RUN_ID}-{self.letter}-{uuid.uuid4().hex[:12]}"
        self._execute("sale.order", "create", [{
            "partner_id": self.partner_id, "company_id": self.company_id,
            "warehouse_id": self.warehouse_id, "user_id": self.uid,
            "client_order_ref": ref,
            "order_line": [[0, 0, {"product_id": product_id, "product_uom_qty": 1}]],
        }], "order/create", nonempty=True, context=self.odoo_context)


if MODE == "read":
    class BenchmarkUser(EcompartsUser):
        abstract = False
        tasks = {EcompartsUser.read_catalogue: 3, EcompartsUser.read_stock: 2}
else:
    class BenchmarkUser(EcompartsUser):
        abstract = False
        tasks = {EcompartsUser.write_order: 1}
