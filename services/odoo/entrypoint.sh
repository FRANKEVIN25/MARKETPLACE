#!/bin/sh
set -e

# Generar /etc/odoo/odoo.conf desde la plantilla con variables de entorno
if [ -f /etc/odoo/odoo.conf.tpl ]; then
  echo "[ODOO] Generando /etc/odoo/odoo.conf desde /etc/odoo/odoo.conf.tpl"
  envsubst < /etc/odoo/odoo.conf.tpl > /etc/odoo/odoo.conf
  chmod 644 /etc/odoo/odoo.conf
else
  echo "[ODOO] ERROR: /etc/odoo/odoo.conf.tpl no encontrado" >&2
  exit 1
fi

echo "[ODOO] Iniciando Odoo 18..."
exec odoo-bin "$@"
