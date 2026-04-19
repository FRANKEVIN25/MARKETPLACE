"""
apps/sync/odoo_connector.py — shim de compatibilidad
=====================================================
Toda la lógica del conector vive en apps/sync/connector/.
Este módulo re-exporta OdooConnector y get_odoo_connector_for_provider
para que todos los imports existentes sigan funcionando sin cambios.

  from apps.sync.odoo_connector import OdooConnector                  ← OK
  from apps.sync.odoo_connector import get_odoo_connector_for_provider ← OK
  from apps.sync.connector import OdooConnector                       ← nuevo (preferido)
"""
from apps.sync.connector import (  # noqa: F401
    OdooConnector,
    get_odoo_connector_for_provider,
    odoo_connector,
)

__all__ = ['OdooConnector', 'get_odoo_connector_for_provider', 'odoo_connector']
