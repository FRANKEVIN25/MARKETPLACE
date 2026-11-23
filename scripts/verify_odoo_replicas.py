"""Verify a session, attachment and company isolation across two Odoo Pods.

Forward each Pod to a different local port before running this script.
The two URLs must point to different Pod names, not to service/odoo.
"""

import argparse
import base64
import hashlib
import json
import uuid

from verify_odoo_lab import Odoo, config, find_one, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pod-a", required=True)
    parser.add_argument("--pod-b", required=True)
    parser.add_argument("--url-a", default="http://127.0.0.1:18071")
    parser.add_argument("--url-b", default="http://127.0.0.1:18072")
    parser.add_argument("--env-file", default=".env.k8s")
    args = parser.parse_args()
    require(args.pod_a != args.pod_b and args.url_a != args.url_b, "Se requieren dos Pods distintos")
    values = config(args.env_file)
    database = values["ODOO_DB"]
    admin = Odoo(args.url_a, database, values["ODOO_ADMIN_LOGIN"], values["ODOO_ADMIN_PASS"])
    admin_uid = admin.uid
    session_a = admin.call("/web/session/get_session_info", {})
    require(session_a["uid"] == admin_uid, "Sesion de administrador invalida en Pod A")
    marker = "BENCH-REPLICA-" + uuid.uuid4().hex
    content = ("Adjunto compartido " + marker).encode()
    partner_id = admin.execute("res.partner", "create", [{"name": marker}])
    attachment_id = admin.execute("ir.attachment", "create", [{
        "name": marker + ".txt", "type": "binary",
        "datas": base64.b64encode(content).decode(),
        "res_model": "res.partner", "res_id": partner_id,
        "mimetype": "text/plain",
    }])
    admin.url = args.url_b.rstrip("/")
    session_b = admin.call("/web/session/get_session_info", {})
    require(session_b["uid"] == admin_uid, "La cookie no continuo en Pod B")
    attachment = admin.execute("ir.attachment", "read", [[attachment_id]],
                               fields=["datas", "store_fname"])[0]
    require(bool(attachment["store_fname"]), "El adjunto no se guardo en el filestore")
    require(hashlib.sha256(base64.b64decode(attachment["datas"])).digest() ==
            hashlib.sha256(content).digest(), "El adjunto cambio entre Pods")
    checks = []
    for letter in "ABC":
        login = f"lab-{letter.lower()}@ecomparts.local"
        user = Odoo(args.url_a, database, login, values["ODOO_ADMIN_PASS"] + "-" + letter)
        company_id = find_one(admin, "res.company", [["name", "=", f"LAB - Compania {letter}"]])
        require(company_id, f"Falta compania {letter}")
        for label, url in (("A", args.url_a), ("B", args.url_b)):
            user.url = url.rstrip("/")
            require(user.call("/web/session/get_session_info", {})["uid"] == user.uid,
                    f"La cookie de {letter} no es valida en Pod {label}")
            companies = user.execute("res.users", "read", [[user.uid]], fields=["company_ids"])[0]
            require(companies["company_ids"] == [company_id], f"Permisos incorrectos de {letter} en Pod {label}")
            context = {"allowed_company_ids": [company_id]}
            own = user.execute("product.product", "search", [[
                ["name", "=", f"LAB - Producto {letter}"],
            ]], context=context)
            require(len(own) == 1, f"Producto de {letter} no visible en Pod {label}")
            for foreign in (other for other in "ABC" if other != letter):
                hidden = user.execute("product.product", "search", [[
                    ["name", "=", f"LAB - Producto {foreign}"],
                ]], context=context)
                require(not hidden, f"Producto de {foreign} visible para {letter} en Pod {label}")
        checks.append(letter)
    print(json.dumps({
        "status": "passed", "pod_a": args.pod_a, "pod_b": args.pod_b,
        "session": "shared", "attachment": "shared", "company_checks": checks,
        "isolation_checked_on": [args.pod_a, args.pod_b],
        "marker": marker, "partner_id": partner_id, "attachment_id": attachment_id,
    }, indent=2))


if __name__ == "__main__":
    main()
