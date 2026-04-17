"""
apps/sync/connector
===================
Cliente Odoo JSON-RPC dividido por dominio de responsabilidad.

Módulos:
  base            — transporte HTTP, autenticación, execute_kw, ping
  companies       — res.company (crear, leer)
  users           — res.users (crear, leer, actualizar companies)
  products        — product.product/template, product.category, stock.warehouse, stock.quant
  vehicles        — push de jerarquía vehicular Django → Odoo y scope multi-company
  compatibility   — autopart.compatibility y vehiculo.variante (lectura)

Uso externo:
    from apps.sync.connector import OdooConnector, get_odoo_connector_for_provider

Todos los imports existentes con apps.sync.odoo_connector siguen funcionando
gracias al shim de compatibilidad en ese módulo.
"""
import logging

from django.conf import settings

from .base import OdooBaseConnector
from .companies import OdooCompaniesMixin
from .compatibility import OdooCompatibilityMixin
from .products import OdooProductsMixin
from .users import OdooUsersMixin
from .vehicles import OdooVehiclesMixin

logger = logging.getLogger(__name__)


class OdooConnector(
    OdooCompaniesMixin,
    OdooUsersMixin,
    OdooProductsMixin,
    OdooVehiclesMixin,
    OdooCompatibilityMixin,
    OdooBaseConnector,
):
    """
    Cliente completo para Odoo via JSON-RPC.

    Compuesto por mixins especializados por dominio. El orden de herencia
    asegura que OdooBaseConnector (que contiene __init__, execute_kw, etc.)
    se resuelve al final de la MRO, permitiendo que cada mixin llame a
    self.execute_kw() sin necesidad de imports circulares.
    """


def get_odoo_connector_for_provider(provider) -> OdooConnector:
    """
    Factory: retorna un OdooConnector configurado para un Provider específico.

    Siempre usa credenciales de admin del settings (las credenciales propias
    del provider aún no tienen desencriptación implementada).

    Args:
        provider: Instancia del modelo Provider

    Returns:
        OdooConnector autenticado para operar en el contexto del provider
    """
    from apps.marketplace.models import Provider as ProviderModel

    if not isinstance(provider, ProviderModel):
        raise TypeError("provider debe ser una instancia de Provider")

    connection_info = provider.get_odoo_connection_info()

    if provider.has_odoo_credentials():
        logger.warning(
            f"Provider {provider.name} tiene credenciales propias pero "
            "aún no implementamos desencriptación. Usando admin."
        )

    return OdooConnector(
        url=connection_info['url'],
        db_name=connection_info['db'],
        username=settings.ODOO_CONFIG.get('USERNAME', 'admin'),
        password=settings.ODOO_CONFIG.get('PASSWORD', 'admin'),
    )


# Instancia singleton para uso general (credenciales por defecto del settings)
odoo_connector = OdooConnector()

__all__ = [
    'OdooConnector',
    'get_odoo_connector_for_provider',
    'odoo_connector',
]
