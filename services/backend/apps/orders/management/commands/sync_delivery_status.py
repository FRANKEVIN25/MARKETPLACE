"""
DEPRECADO — este archivo es un shim de compatibilidad.
La implementación real vive en apps/sync/management/commands/sync_delivery_status.py.

Este módulo re-exporta la clase Command desde allí para que Django la encuentre
bajo el mismo nombre (apps.orders está antes que apps.sync en INSTALLED_APPS).
"""
from apps.sync.management.commands.sync_delivery_status import Command  # noqa: F401
