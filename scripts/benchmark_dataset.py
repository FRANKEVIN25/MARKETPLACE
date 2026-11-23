"""Create and verify a repeatable, isolated Odoo benchmark fixture.

The existing LAB fixture must be seeded first. This script only writes records
whose names start with BENCH- and requires LAB_MODE=1.
"""

import argparse
import json

from verify_odoo_lab import Odoo, config, find_one, require


def prepare(rpc, company, count, seed):
    letter = company["letter"]
    company_id = company["company_id"]
    context = {"allowed_company_ids": [company_id], "company_id": company_id}
    warehouse_id = find_one(rpc, "stock.warehouse", [["company_id", "=", company_id]], context)
    require(warehouse_id, f"Falta almacen de la compania {letter}")
    warehouse = rpc.execute("stock.warehouse", "read", [[warehouse_id]], fields=["lot_stock_id"], context=context)[0]
    location_id = warehouse["lot_stock_id"][0]
    partner_name = f"BENCH-{letter}-CLIENTE"
    partner_id = find_one(rpc, "res.partner", [["name", "=", partner_name], ["company_id", "=", company_id]], context)
    if not partner_id and seed:
        partner_id = rpc.execute("res.partner", "create", [{"name": partner_name, "company_id": company_id}], context=context)
    require(partner_id, f"Falta cliente BENCH de {letter}")
    products = []
    for number in range(1, count + 1):
        name = f"BENCH-{letter}-{number:03d}"
        product_id = find_one(rpc, "product.product", [["name", "=", name], ["company_id", "=", company_id]], context)
        if not product_id and seed:
            product_id = rpc.execute("product.product", "create", [{
                "name": name, "company_id": company_id, "list_price": 50 + number,
                "type": "consu", "is_storable": True,
            }], context=context)
        require(product_id, f"Falta producto {name}")
        quant_id = find_one(rpc, "stock.quant", [
            ["product_id", "=", product_id], ["location_id", "=", location_id],
        ], context)
        if seed:
            if quant_id:
                rpc.execute("stock.quant", "write", [[quant_id], {"inventory_quantity": 1000}],
                            context={**context, "inventory_mode": True})
            else:
                quant_id = rpc.execute("stock.quant", "create", [{
                    "product_id": product_id, "location_id": location_id,
                    "inventory_quantity": 1000,
                }], context={**context, "inventory_mode": True})
            rpc.execute("stock.quant", "action_apply_inventory", [[quant_id]], context=context)
        require(quant_id, f"Falta stock de {name}")
        quant = rpc.execute("stock.quant", "read", [[quant_id]], fields=["quantity"], context=context)[0]
        require(quant["quantity"] >= 1, f"Stock no positivo de {name}")
        products.append(product_id)
    return {"company": letter, "company_id": company_id, "user": company["login"],
            "partner_id": partner_id, "warehouse_id": warehouse_id, "products": products}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seed", "verify", "reset-orders"])
    parser.add_argument("--env-file", default=".env.k8s")
    parser.add_argument("--base-url", default="http://127.0.0.1:18070")
    parser.add_argument("--products", type=int, default=12)
    parser.add_argument("--run-id", help="Required for reset-orders; only that run's BENCH orders are removed")
    args = parser.parse_args()
    require(1 <= args.products <= 100, "--products debe estar entre 1 y 100")
    values = config(args.env_file)
    rpc = Odoo(args.base_url, values["ODOO_DB"], values["ODOO_ADMIN_LOGIN"], values["ODOO_ADMIN_PASS"])
    if args.action == "reset-orders":
        require(args.run_id and args.run_id.isalnum(), "--run-id alfanumerico obligatorio")
        prefix = f"BENCH-{args.run_id}-"
        ids = rpc.execute("sale.order", "search", [[["client_order_ref", "=like", prefix + "%"]]])
        if ids:
            states = rpc.execute("sale.order", "read", [ids], fields=["state", "client_order_ref"])
            require(all(row["state"] in ("draft", "sent") and row["client_order_ref"].startswith(prefix)
                        for row in states), "Solo se pueden limpiar pedidos BENCH en borrador")
            rpc.execute("sale.order", "unlink", [ids])
        print(json.dumps({"run_id": args.run_id, "removed_orders": len(ids)}))
        return

    companies = []
    for letter in "ABC":
        company_id = find_one(rpc, "res.company", [["name", "=", f"LAB - Compania {letter}"]])
        require(company_id, "Ejecuta primero verify_odoo_lab.py --seed")
        login = f"lab-{letter.lower()}@ecomparts.local"
        require(find_one(rpc, "res.users", [["login", "=", login]]), f"Falta usuario {login}")
        companies.append({"letter": letter, "company_id": company_id, "login": login})
    result = [prepare(rpc, company, args.products, args.action == "seed") for company in companies]
    print(json.dumps({"status": "passed", "action": args.action, "products_per_company": args.products,
                      "companies": result}, indent=2))


if __name__ == "__main__":
    main()
