import os
from odoo import api, SUPERUSER_ID

# =========================
# CONFIGURACIÓN (desde env del contenedor)
# =========================

ADMIN_LOGIN = os.environ.get("ODOO_ADMIN_LOGIN", "admin2@ecomparts.local")
ADMIN_PASS = os.environ.get("ODOO_ADMIN_PASS", "Admin!2025")

SERVICE_LOGIN = os.environ.get(
    "ODOO_SERVICE_LOGIN",
    os.environ.get("ODOO_USERNAME", "service@ecomparts.local"),
)
SERVICE_PASS = os.environ.get(
    "ODOO_SERVICE_PASS",
    "Service!2025",
)

ADMIN_GROUPS = [
    "base.group_user",
    "base.group_system",
    "sales_team.group_sale_manager",
    "stock.group_stock_manager",
]

SERVICE_GROUPS = [
    "base.group_user",
    "base.group_system",
    "sales_team.group_sale_manager",
    "stock.group_stock_manager",
]

shell_env = globals().get("env")
if shell_env is None:
    raise RuntimeError("Este script debe ejecutarse desde odoo shell para disponer de 'env'.")

env = api.Environment(shell_env.cr, SUPERUSER_ID, {})
Users = env["res.users"].sudo()


def ensure_user(login, password, name):
    user = Users.search([("login", "=", login)], limit=1)
    if not user:
        user = Users.create({
            "name": name,
            "login": login,
            "password": password,
            "email": login,
            "active": True,
        })
        print(f"✅ Usuario creado: {login} (ID: {user.id})")
    else:
        # Actualizar password si es diferente
        try:
            user.write({"password": password})
            print(f"ℹ️  Usuario existente, contraseña actualizada: {login}")
        except Exception:
            print(f"ℹ️  Usuario existente (no se pudo actualizar contraseña): {login}")
        print(f"ℹ️ Usuario ya existe: {login} (ID: {user.id})")
    return user


def assign_groups(user, xmlids):
    for xmlid in xmlids:
        if not xmlid:
            continue
        group = env.ref(xmlid, raise_if_not_found=False)
        if group:
            if group.id not in user.groups_id.ids:
                user.write({"groups_id": [(4, group.id)]})
                print(f"   ➕ Grupo asignado: {xmlid}")
            else:
                print(f"   ℹ️ Grupo ya asignado: {xmlid}")
        else:
            print(f"   ⚠️ Grupo no encontrado: {xmlid}")


# 1) Administrador total
admin_user = ensure_user(ADMIN_LOGIN, ADMIN_PASS, "ECOMPARTS Administrator")
assign_groups(admin_user, ADMIN_GROUPS)

# 2) Usuario de servicio
service_user = ensure_user(SERVICE_LOGIN, SERVICE_PASS, "ECOMPARTS Service User")
assign_groups(service_user, SERVICE_GROUPS)

env.cr.commit()
print("\n🚀 Script finalizado correctamente.")
