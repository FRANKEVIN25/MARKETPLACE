#!/bin/sh
set -e

ODOO_USER="${ODOO_USER:-odoo}"

# Asegurar permisos correctos sobre volúmenes montados antes de bajar privilegios.
if [ "$(id -u)" = "0" ]; then
  mkdir -p /var/lib/odoo /opt/odoo/.local/share/Odoo /mnt/extra-addons /etc/odoo
  chown -R "${ODOO_USER}:${ODOO_USER}" /var/lib/odoo /opt/odoo/.local/share/Odoo /mnt/extra-addons /etc/odoo /opt/odoo
  chmod -R u+rwX,g+rwX /var/lib/odoo /opt/odoo/.local/share/Odoo /mnt/extra-addons /etc/odoo /opt/odoo
fi

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
if [ "$(id -u)" = "0" ]; then
  exec gosu "${ODOO_USER}" odoo-bin "$@"
fi

exec odoo-bin "$@"
