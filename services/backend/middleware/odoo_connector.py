"""
Conector Odoo para middleware — redirige al conector principal JSON-RPC
Migrado de XML-RPC → JSON-RPC el 9 Mar 2026

NOTA: Este archivo existe por compatibilidad con imports del middleware.
      Toda la lógica real está en apps/sync/odoo_connector.py
"""
from apps.sync.odoo_connector import OdooConnector, get_odoo_connector_for_provider

# Re-exportar para compatibilidad con imports existentes
__all__ = ['OdooConnector', 'get_odoo_connector_for_provider', 'odoo_connector']

# Instancia singleton para uso general
odoo_connector = OdooConnector()