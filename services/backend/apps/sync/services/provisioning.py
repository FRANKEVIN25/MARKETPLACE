"""
services/provisioning.py
========================
Aprovisionamiento de nuevos providers (Company + User en Odoo).

Incluye:
  - create_provider_with_odoo_setup(): crea Provider en Django, Company y User
    en Odoo, y los vincula atómicamente.
  - verify_provider_odoo_connection(): health-check de las credenciales Odoo
    almacenadas en un Provider existente.
"""
import logging

from django.db import transaction
from django.contrib.auth import get_user_model

from apps.marketplace.models import Provider
from apps.sync.connector import OdooConnector, get_odoo_connector_for_provider

logger = logging.getLogger(__name__)
User = get_user_model()


def create_provider_with_odoo_setup(
    user_id: int,
    provider_data: dict,
    odoo_password: str,
) -> dict:
    """
    Crea un Provider completo con su Company y Usuario en Odoo.

    Flujo (dentro de una transacción atómica de Django):
      1. Verificar que el usuario Django existe.
      2. Crear (o recuperar) el Provider en Django sin datos de Odoo aún.
      3. Crear la Company en Odoo (idempotente).
      4. Derivar un username único para Odoo.
      5. Crear el User en Odoo vinculado a la Company.
      6. Guardar odoo_company_id, odoo_user_id y odoo_username en el Provider.

    Si cualquier paso 3-6 falla, la transacción se revierte y el Provider se
    marca como inactivo (si ya existía en DB).

    Args:
        user_id:       ID del usuario Django que será owner del provider.
        provider_data: Dict con claves:
                         - name  (str, requerido)
                         - email (str)
                         - phone (str, opcional)
                         - ruc   (str, opcional)
                         - tier  (str, opcional; default 'starter')
        odoo_password: Password que el vendor eligió para su acceso a Odoo.

    Returns:
        dict con 'success' (bool) y datos del Provider/Odoo, o 'error' (str).
    """
    try:
        with transaction.atomic():
            # 1. Verificar usuario Django
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.error("Usuario %s no existe", user_id)
                return {'success': False, 'error': 'Usuario no encontrado'}

            # 2. Crear o recuperar Provider
            provider_name  = provider_data.get('name')
            provider_email = provider_data.get('email')

            if not provider_name:
                return {'success': False, 'error': 'Nombre del proveedor es requerido'}

            existing = Provider.objects.filter(name=provider_name).first()
            if existing:
                provider = existing
                # Guard: si ya tiene credenciales completas (otra task paralela terminó primero),
                # no hacer nada — el aprovisionamiento ya está completo.
                if provider.has_odoo_credentials():
                    logger.info(
                        "Provider '%s' ya tiene credenciales Odoo — task idempotente, nada que hacer.",
                        provider.name,
                    )
                    return {
                        'success': True,
                        'provider_id': provider.id,
                        'provider_name': provider.name,
                        'odoo_company_id': provider.odoo_company_id,
                        'odoo_user_id': provider.odoo_user_id,
                        'odoo_username': provider.odoo_username,
                        'message': 'Provider ya aprovisionado (task duplicada ignorada).',
                    }
                logger.info(
                    "Provider existente encontrado: %s (ID: %s)",
                    provider.name, provider.id,
                )
            else:
                provider = Provider(
                    name=provider_name,
                    email=provider_email,
                    phone=provider_data.get('phone', ''),
                    ruc=provider_data.get('ruc', ''),
                    tier=provider_data.get('tier', 'starter'),
                    owner=user,
                    is_active=True,
                    is_approved=False,
                )
                provider.save()
                logger.info("Provider creado en Django: %s (ID: %s)", provider.name, provider.id)

            # 3. Crear Company en Odoo (admin connector)
            odoo = OdooConnector()
            company_id = odoo.create_company(
                name=provider_name,
                email=provider_email,
                currency_code='PEN',
                vat=provider_data.get('ruc') or None,
                phone=provider_data.get('phone') or None,
            )
            if not company_id:
                raise RuntimeError("No se pudo crear Company en Odoo")
            logger.info("Company creada en Odoo: %s (ID: %s)", provider_name, company_id)

            # 4. Username único para Odoo
            odoo_username = provider.generate_odoo_username()

            # 5. Crear User en Odoo vinculado a la Company
            odoo_user_id = odoo.create_user_for_company(
                name=provider_name,
                login=odoo_username,
                password=odoo_password,
                company_id=company_id,
                groups=None,  # Grupos por defecto: Inventario + Ventas
            )
            if not odoo_user_id:
                raise RuntimeError("No se pudo crear Usuario en Odoo")
            logger.info("Usuario creado en Odoo: %s (ID: %s)", odoo_username, odoo_user_id)

            # 6. Vincular Provider con Odoo
            # Limpiar cualquier provider huérfano que tenga el mismo odoo_company_id
            # (puede ocurrir con datos de seed sin odoo_user_id real)
            Provider.objects.filter(
                odoo_company_id=company_id,
                odoo_user_id__isnull=True,
            ).exclude(pk=provider.pk).update(odoo_company_id=None)

            provider.odoo_company_id = company_id
            provider.odoo_user_id    = odoo_user_id
            provider.odoo_username   = odoo_username
            provider.set_odoo_password(odoo_password)  # almacena encriptado
            provider.clear_odoo_password_temp()        # ya no necesitamos la temporal
            provider.save(update_fields=[
                'odoo_company_id', 'odoo_user_id', 'odoo_username',
                'odoo_password_hash', 'odoo_password_temp',
            ])
            logger.info("Provider %s vinculado con Odoo correctamente", provider.name)

            return {
                'success': True,
                'provider_id': provider.id,
                'provider_name': provider.name,
                'odoo_company_id': company_id,
                'odoo_user_id': odoo_user_id,
                'odoo_username': odoo_username,
                'message': (
                    f'Proveedor {provider.name} creado exitosamente. '
                    'Pendiente de aprobación.'
                ),
            }

    except Exception as e:
        logger.exception("Error en create_provider_with_odoo_setup: %s", e)
        # No marcamos el provider como inactivo: el admin puede reintentar
        # la acción "Aprobar y configurar en Odoo" una vez resuelto el problema.
        return {
            'success': False,
            'error': str(e),
            'message': 'Error al configurar Odoo. Por favor revise los logs y reintente desde el admin.',
        }


def verify_provider_odoo_connection(provider_id: int) -> dict:
    """
    Verifica que las credenciales Odoo del provider funcionen correctamente.

    Comprueba que tanto la Company como el User existen en Odoo.

    Returns:
        dict con 'success' (bool) y datos de Company/User, o 'error' (str).
    """
    try:
        provider = Provider.objects.get(id=provider_id)
    except Provider.DoesNotExist:
        return {'success': False, 'error': 'Provider no encontrado'}

    if not provider.has_odoo_credentials():
        return {'success': False, 'error': 'Provider no tiene credenciales de Odoo'}

    try:
        odoo = get_odoo_connector_for_provider(provider)

        company = odoo.get_company(provider.odoo_company_id)
        if not company:
            return {
                'success': False,
                'error': f'Company {provider.odoo_company_id} no existe en Odoo',
            }

        user = odoo.get_user(provider.odoo_user_id)
        if not user:
            return {
                'success': False,
                'error': f'Usuario {provider.odoo_user_id} no existe en Odoo',
            }

        return {
            'success': True,
            'provider': provider.name,
            'company': company['name'],
            'user': user['login'],
            'message': 'Conexión verificada correctamente',
        }

    except Exception as e:
        logger.exception("Error verificando conexión de provider %s: %s", provider_id, e)
        return {'success': False, 'error': str(e)}
