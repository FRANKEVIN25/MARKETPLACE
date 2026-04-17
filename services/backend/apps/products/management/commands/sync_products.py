"""
DEPRECADO — este archivo es un shim de compatibilidad.
La implementación real vive en apps/sync/management/commands/sync_products.py.

Este módulo re-exporta la clase Command desde allí para que Django la encuentre
bajo el mismo nombre (apps.products está antes que apps.sync en INSTALLED_APPS).
Cuando se reordene INSTALLED_APPS o se elimine este archivo, el comando seguirá
funcionando desde apps/sync/management/commands/sync_products.py.
"""
from apps.sync.management.commands.sync_products import Command  # noqa: F401

