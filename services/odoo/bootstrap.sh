#!/bin/sh
set -eu

: "${ODOO_DB:?Falta ODOO_DB}"
: "${ODOO_ADMIN_LOGIN:?Falta ODOO_ADMIN_LOGIN}"
: "${ODOO_ADMIN_PASS:?Falta ODOO_ADMIN_PASS}"
: "${ODOO_SERVICE_LOGIN:?Falta ODOO_SERVICE_LOGIN}"
: "${ODOO_SERVICE_PASS:?Falta ODOO_SERVICE_PASS}"

modules="${ODOO_INIT_MODULES:-base,web,sale_management,stock,ecomp,orders_odoo,multi_company_products,odoo_django_webhook}"

echo "[ODOO INIT] Inicializando $ODOO_DB y comprobando addons: $modules"
odoo-bin -c /etc/odoo/odoo.conf -d "$ODOO_DB" \
    --init "$modules" --without-demo=all --stop-after-init \
    --workers=0 --max-cron-threads=0 --no-http

echo "[ODOO INIT] Configurando las cuentas de administración e integración"
odoo-bin shell -c /etc/odoo/odoo.conf -d "$ODOO_DB" \
    --workers=0 --max-cron-threads=0 --no-http \
    < /opt/odoo/scripts/create_service_user.py

echo "[ODOO INIT] Base, addons y cuentas preparados"
