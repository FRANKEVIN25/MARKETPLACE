"""Comprueba Odoo por JSON-RPC en Compose o Kubernetes. Usa la biblioteca estandar.

--seed prepara un conjunto minimo e idempotente de tres companias de laboratorio.
No representa el dataset de rendimiento que debe preparar Jesus.
"""

import argparse
from datetime import datetime, timezone
import http.cookiejar
import json
import re
from pathlib import Path
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    "base", "web", "sale_management", "stock", "ecomp", "orders_odoo",
    "multi_company_products", "odoo_django_webhook",
]


class RpcError(RuntimeError):
    def __init__(self, error):
        self.details = error.get("data", {})
        super().__init__(self.details.get("message") or error.get("message", "Error JSON-RPC"))


class Odoo:
    def __init__(self, url, database, login, password):
        self.url = url.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )
        auth = self.call("/web/session/authenticate", {
            "db": database, "login": login, "password": password,
        })
        if not auth or not auth.get("uid"):
            raise RuntimeError(f"Login fallido: {login}")
        self.uid = auth["uid"]

    def call(self, endpoint, params):
        payload = json.dumps({"jsonrpc": "2.0", "method": "call", "id": 1, "params": params}).encode()
        request = urllib.request.Request(
            self.url + endpoint, data=payload, headers={"Content-Type": "application/json"}
        )
        with self.opener.open(request, timeout=90) as response:
            body = json.load(response)
        if "error" in body:
            raise RpcError(body["error"])
        return body.get("result")

    def execute(self, model, method, args=None, **kwargs):
        return self.call("/web/dataset/call_kw", {
            "model": model, "method": method, "args": args or [], "kwargs": kwargs,
        })


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def config(env_file=".env.lab"):
    values = {}
    for line in (ROOT / env_file).read_text(encoding="utf-8-sig").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    require(values.get("LAB_MODE") == "1", "Se requiere un archivo de laboratorio con LAB_MODE=1")
    return values


def find_one(rpc, model, domain, context=None):
    kwargs = {"limit": 1}
    if context:
        kwargs["context"] = context
    ids = rpc.execute(model, "search", [domain], **kwargs)
    return ids[0] if ids else None


def fixture(rpc, values, seed):
    records = []
    groups = []
    for xmlid in ("base.group_user", "sales_team.group_sale_manager", "stock.group_stock_manager"):
        module, name = xmlid.split(".", 1)
        group = rpc.execute("ir.model.data", "search_read", [
            [["module", "=", module], ["name", "=", name]]
        ], fields=["res_id"], limit=1)
        require(bool(group), f"Grupo requerido ausente: {xmlid}")
        groups.append(group[0]["res_id"])

    for letter in "ABC":
        name = f"LAB - Compania {letter}"
        company_id = find_one(rpc, "res.company", [["name", "=", name]])
        if not company_id:
            require(seed, "Faltan datos de laboratorio. Ejecuta Check -Seed la primera vez.")
            company_id = rpc.execute("res.company", "create", [{"name": name}])
        records.append({"company_id": company_id, "letter": letter})

    company_ids = [record["company_id"] for record in records]
    if seed:
        integration_id = find_one(rpc, "res.users", [["login", "=", values["ODOO_SERVICE_LOGIN"]]])
        rpc.execute("res.users", "write", [[rpc.uid, integration_id], {
            "company_ids": [[4, company_id] for company_id in company_ids]
        }])

    for record in records:
        company_id, letter = record["company_id"], record["letter"]
        context = {"allowed_company_ids": [company_id], "company_id": company_id}
        login = f"lab-{letter.lower()}@ecomparts.local"
        password = values["ODOO_ADMIN_PASS"] + "-" + letter
        user_id = find_one(rpc, "res.users", [["login", "=", login]])
        if seed:
            user_values = {
                "name": f"Usuario laboratorio {letter}", "login": login, "password": password,
                "company_id": company_id, "company_ids": [[6, 0, [company_id]]],
                "groups_id": [[6, 0, groups]],
            }
            if user_id:
                rpc.execute("res.users", "write", [[user_id], user_values])
            else:
                user_id = rpc.execute("res.users", "create", [user_values], context=context)
        require(bool(user_id), f"Falta usuario de laboratorio {letter}")

        product_name = f"LAB - Producto {letter}"
        product_id = find_one(rpc, "product.product", [
            ["name", "=", product_name], ["company_id", "=", company_id]
        ], context)
        if not product_id:
            require(seed, f"Falta producto de laboratorio {letter}")
            product_id = rpc.execute("product.product", "create", [{
                "name": product_name, "company_id": company_id, "list_price": 100,
                "type": "consu", "is_storable": True,
            }], context=context)

        warehouse_id = find_one(rpc, "stock.warehouse", [["company_id", "=", company_id]], context)
        if not warehouse_id:
            require(seed, f"Falta almacen de laboratorio {letter}")
            warehouse_id = rpc.execute("stock.warehouse", "create", [{
                "name": f"LAB Almacen {letter}", "code": f"L{letter}", "company_id": company_id,
            }], context=context)
        warehouse = rpc.execute("stock.warehouse", "read", [[warehouse_id]], fields=["lot_stock_id"], context=context)[0]
        location_id = warehouse["lot_stock_id"][0]
        quant_id = find_one(rpc, "stock.quant", [
            ["product_id", "=", product_id], ["location_id", "=", location_id]
        ], context)
        if not quant_id:
            require(seed, f"Falta stock de laboratorio {letter}")
            quant_id = rpc.execute("stock.quant", "create", [{
                "product_id": product_id, "location_id": location_id, "inventory_quantity": 10,
            }], context={**context, "inventory_mode": True})
            rpc.execute("stock.quant", "action_apply_inventory", [[quant_id]], context=context)

        order_ref = f"LAB-B1-{letter}"
        order_id = find_one(rpc, "sale.order", [["client_order_ref", "=", order_ref]], context)
        if not order_id:
            require(seed, f"Falta pedido de laboratorio {letter}")
            partner_id = rpc.execute("res.partner", "create", [{
                "name": f"LAB Cliente {letter}", "company_id": company_id,
            }], context=context)
            order_id = rpc.execute("sale.order", "create", [{
                "partner_id": partner_id, "company_id": company_id, "user_id": user_id,
                "warehouse_id": warehouse_id, "client_order_ref": order_ref,
                "order_line": [[0, 0, {"product_id": product_id, "product_uom_qty": 1, "price_unit": 100}]],
            }], context=context)
        record.update(login=login, password=password, user_id=user_id, product_id=product_id, order_id=order_id)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", action="store_true")
    parser.add_argument("--project", default="ecomparts-lab")
    parser.add_argument("--env-file", default=".env.lab")
    parser.add_argument("--base-url")
    args = parser.parse_args()
    require(re.fullmatch(r"ecomparts-(?:lab|k8s)(?:-[a-z0-9-]+)?", args.project), "Nombre de laboratorio no valido")
    values = config(args.env_file)
    url = args.base_url or f"http://127.0.0.1:{values.get('ODOO_PORT', '8070')}"
    database = values["ODOO_DB"]
    admin = Odoo(url, database, values["ODOO_ADMIN_LOGIN"], values["ODOO_ADMIN_PASS"])
    service = Odoo(url, database, values["ODOO_SERVICE_LOGIN"], values["ODOO_SERVICE_PASS"])
    states = service.execute("ir.module.module", "search_read", [
        [["name", "in", MODULES]]
    ], fields=["name", "state"])
    installed = {row["name"] for row in states if row["state"] == "installed"}
    require(set(MODULES) <= installed, f"Addons pendientes: {sorted(set(MODULES) - installed)}")
    records = fixture(admin, values, args.seed)
    results = []
    for record in records:
        rpc = Odoo(url, database, record["login"], record["password"])
        user = rpc.execute("res.users", "read", [[rpc.uid]], fields=["company_ids"])[0]
        require(user["company_ids"] == [record["company_id"]], "El usuario tiene acceso a otras companias")
        require(not rpc.execute("res.users", "has_group", [[rpc.uid], "base.group_system"]), "El usuario de prueba es administrador del sistema")
        context = {"allowed_company_ids": [record["company_id"]]}
        for model, key in (("product.product", "product_id"), ("sale.order", "order_id")):
            visible = rpc.execute(model, "search", [
                [["id", "in", [item[key] for item in records]]]
            ], context=context)
            require(visible == [record[key]], f"Aislamiento incorrecto en {model}, compania {record['letter']}")
        stock = rpc.execute("stock.quant", "search_read", [
            [["product_id", "in", [item["product_id"] for item in records]], ["quantity", ">", 0]]
        ], fields=["product_id", "quantity", "company_id"], context=context)
        require(bool(stock), f"Stock no disponible para {record['letter']}")
        require(all(row["company_id"][0] == record["company_id"] for row in stock), "Stock de otra compania visible")
        foreign = next(item for item in records if item["company_id"] != record["company_id"])
        try:
            rpc.execute("product.product", "read", [[foreign["product_id"]]], fields=["name"], context=context)
        except RpcError as error:
            require("AccessError" in error.details.get("name", ""), "La lectura fallo por un error distinto de permisos")
        else:
            raise RuntimeError("La lectura directa de un producto ajeno fue permitida")
        try:
            rpc.execute("product.product", "search", [[]], context={"allowed_company_ids": [foreign["company_id"]]})
        except RpcError as error:
            require("AccessError" in error.details.get("name", ""), "El cambio de compania fallo por un error distinto de permisos")
        else:
            raise RuntimeError("El usuario pudo seleccionar una compania no autorizada")
        results.append({"company": record["letter"], "login": "ok", "catalog": "ok", "stock": "ok", "order": "ok", "isolation": "ok"})

    report = {
        "project": args.project, "database": database,
        "base_url": url,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "modules": sorted(installed), "companies": results, "status": "passed",
    }
    output_dir = ROOT / ".lab"
    output_dir.mkdir(exist_ok=True)
    (output_dir / f"{args.project}-checks.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"VALIDACION FALLIDA: {error}", file=sys.stderr)
        sys.exit(1)
