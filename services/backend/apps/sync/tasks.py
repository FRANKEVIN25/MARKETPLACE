"""
Tareas de sincronización entre Odoo y Django Marketplace
ACTUALIZADO: Incluye registro automático de vendors con setup completo de Odoo
"""
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.marketplace.models import Provider
from apps.products.models import Product
from apps.sync.odoo_connector import OdooConnector, get_odoo_connector_for_provider
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


# ====== NUEVA TAREA: REGISTRO AUTOMÁTICO DE VENDOR ======

@shared_task
def create_provider_with_odoo_setup(user_id, provider_data, odoo_password):
    """
    Crea un Provider completo con su Company y Usuario en Odoo
    Esta es la tarea principal para el registro automatizado de vendors
    
    Args:
        user_id (int): ID del usuario Django que será owner
        provider_data (dict): Datos del provider
            - name (str): Nombre del negocio
            - email (str): Email del negocio
            - phone (str): Teléfono (opcional)
            - ruc (str): RUC (opcional)
            - tier (str): Tier inicial (default: 'starter')
        odoo_password (str): Password que eligió el vendor para Odoo
        
    Returns:
        dict: Resultado del proceso con IDs creados o error
    """
    try:
        with transaction.atomic():
            # 1. Verificar que el usuario existe
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.error(f"Usuario {user_id} no existe")
                return {'success': False, 'error': 'Usuario no encontrado'}
            
            # 2. Crear Provider en Django (sin datos de Odoo aún)
            provider_name = provider_data.get('name')
            provider_email = provider_data.get('email')
            
            if not provider_name:
                return {'success': False, 'error': 'Nombre del proveedor es requerido'}
            
            # Buscar Provider existente o crear uno nuevo
            existing = Provider.objects.filter(name=provider_name).first()
            if existing:
                provider = existing
                logger.info(f"✅ Provider existente encontrado: {provider.name} (ID: {provider.id})")
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
                logger.info(f"✅ Provider creado en Django: {provider.name} (ID: {provider.id})")
            
            # 3. Crear Company en Odoo
            odoo = OdooConnector()  # Usa credenciales de admin
            
            company_id = odoo.create_company(
                name=provider_name,
                email=provider_email,
                currency_id=164  # PEN (Soles peruanos)
            )
            
            if not company_id:
                raise Exception("No se pudo crear Company en Odoo")
            
            logger.info(f"✅ Company creada en Odoo: {provider_name} (ID: {company_id})")
            
            # 4. Generar username único para Odoo
            odoo_username = provider.generate_odoo_username()
            
            # 5. Crear Usuario en Odoo
            odoo_user_id = odoo.create_user_for_company(
                name=provider_name,
                login=odoo_username,
                password=odoo_password,  # Password elegido por el vendor
                company_id=company_id,
                groups=None  # Usa grupos por defecto (Inventario + Ventas)
            )
            
            if not odoo_user_id:
                raise Exception("No se pudo crear Usuario en Odoo")
            
            logger.info(f"✅ Usuario creado en Odoo: {odoo_username} (ID: {odoo_user_id})")
            
            # 6. Actualizar Provider con datos de Odoo
            provider.odoo_company_id = company_id
            provider.odoo_user_id = odoo_user_id
            provider.odoo_username = odoo_username
            provider.set_odoo_password(odoo_password)  # Guarda encriptado
            provider.save()
            
            logger.info(f"✅ Provider vinculado con Odoo correctamente")
            
            # 7. Retornar resultado exitoso
            return {
                'success': True,
                'provider_id': provider.id,
                'provider_name': provider.name,
                'odoo_company_id': company_id,
                'odoo_user_id': odoo_user_id,
                'odoo_username': odoo_username,
                'message': f'Proveedor {provider.name} creado exitosamente. Pendiente de aprobación.'
            }
            
    except Exception as e:
        logger.exception(f"❌ Error en create_provider_with_odoo_setup: {e}")
        
        # Si ya se creó el provider, marcarlo como inactivo
        try:
            if 'provider' in locals():
                provider.is_active = False
                provider.save()
                logger.warning(f"Provider {provider.id} marcado como inactivo debido a error")
        except:
            pass
        
        return {
            'success': False,
            'error': str(e),
            'message': 'Error al crear el proveedor. Por favor contacte al administrador.'
        }


# ====== TAREAS DE SINCRONIZACIÓN (EXISTENTES - ACTUALIZADAS) ======

@shared_task
def sync_provider_products(provider_id):
    """
    Sincroniza productos de un provider desde su Odoo al marketplace
    
    Args:
        provider_id: ID del Provider a sincronizar
    
    Returns:
        dict con estadísticas de la sincronización
    """
    try:
        provider = Provider.objects.get(id=provider_id, is_active=True, is_approved=True)
        logger.info(f"Iniciando sincronización de productos para {provider.name}")
        
        # Obtener conector de Odoo
        odoo = get_odoo_connector_for_provider(provider)
        
        # Obtener productos de Odoo
        odoo_products = odoo.get_products(company_id=provider.odoo_company_id)
        
        stats = {
            'provider': provider.name,
            'total_odoo': len(odoo_products),
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        import cloudinary.uploader, base64

        def upload_image(b64_data, public_id):
            """Sube imagen base64 a Cloudinary, retorna (url, cloudinary_id)"""
            if not b64_data or b64_data is False:
                return None, None
            try:
                image_data = base64.b64decode(b64_data)
                result = cloudinary.uploader.upload(
                    image_data,
                    public_id=public_id,
                    overwrite=True,
                    resource_type="image",
                    transformation=[{
                        "width": 800, "height": 800,
                        "crop": "limit", "quality": "auto",
                        "fetch_format": "auto"
                    }]
                )
                return result.get('secure_url'), result.get('public_id')
            except Exception as img_err:
                logger.warning(f"⚠️ No se pudo subir imagen a Cloudinary ({public_id}): {img_err}")
                return None, None

        # Batch-fetch imágenes de galería para todos los templates de este provider
        tmpl_ids = set()
        for p in odoo_products:
            tmpl = p.get('product_tmpl_id')
            if tmpl:
                tid = tmpl[0] if isinstance(tmpl, list) else tmpl
                tmpl_ids.add(tid)
        gallery_by_tmpl = odoo.get_gallery_images(tmpl_ids)
        logger.info(f"Galería cargada: {sum(len(v) for v in gallery_by_tmpl.values())} imágenes para {len(gallery_by_tmpl)} templates")

        for odoo_product in odoo_products:
            try:
                product_ref = odoo_product.get('default_code') or str(odoo_product['id'])

                # Imagen principal desde image_1920
                image_url, image_cloudinary_id = upload_image(
                    odoo_product.get('image_1920'),
                    f"ecomparts/products/{product_ref}"
                )

                # Imágenes 2 y 3 desde la galería ecomparts_image_ids
                tmpl = odoo_product.get('product_tmpl_id')
                tmpl_id = tmpl[0] if isinstance(tmpl, list) else tmpl
                gallery_imgs = gallery_by_tmpl.get(tmpl_id, [])

                image_url_2, image_cloudinary_id_2 = upload_image(
                    gallery_imgs[0].get('image') if len(gallery_imgs) > 0 else None,
                    f"ecomparts/products/{product_ref}_gallery_1"
                )
                image_url_3, image_cloudinary_id_3 = upload_image(
                    gallery_imgs[1].get('image') if len(gallery_imgs) > 1 else None,
                    f"ecomparts/products/{product_ref}_gallery_2"
                )

                if image_url:
                    logger.info(f"✅ Imagen principal subida para {product_ref} | galería: {len(gallery_imgs)} imgs")

                # Buscar o crear producto en marketplace
                product, created = Product.objects.update_or_create(
                    provider=provider,
                    odoo_product_id=odoo_product['id'],
                    defaults={
                        'name': odoo_product['name'],
                        'reference': odoo_product.get('default_code') or str(odoo_product.get('id', '')),
                        'description': odoo_product.get('description_sale') or '',
                        'price': odoo_product.get('list_price', 0),
                        'image_url': image_url,
                        'image_cloudinary_id': image_cloudinary_id,
                        'image_url_2': image_url_2,
                        'image_cloudinary_id_2': image_cloudinary_id_2,
                        'image_url_3': image_url_3,
                        'image_cloudinary_id_3': image_cloudinary_id_3,
                        'is_active': odoo_product.get('active', True),
                        'last_sync_at': timezone.now()
                    }
                )

                if created:
                    stats['created'] += 1
                else:
                    stats['updated'] += 1

            except Exception as e:
                logger.error(f"Error al sincronizar producto {odoo_product['id']}: {e}")
                stats['errors'] += 1
        
        # Actualizar contador de productos del provider
        provider.total_products = Product.objects.filter(
            provider=provider,
            is_active=True
        ).count()
        provider.save(update_fields=['total_products'])
        
        logger.info(f"Sincronización completada para {provider.name}: {stats}")
        return stats
        
    except Provider.DoesNotExist:
        logger.error(f"Provider {provider_id} no existe o no está activo")
        return {'error': 'Provider no encontrado'}
    except Exception as e:
        logger.error(f"Error en sincronización de provider {provider_id}: {e}")
        return {'error': str(e)}


@shared_task
def sync_all_active_providers():
    """
    Sincroniza todos los providers activos y aprobados
    Esta tarea se ejecuta periódicamente (ej: cada hora)
    """
    providers = Provider.objects.filter(is_active=True, is_approved=True)
    
    logger.info(f"Iniciando sincronización de {providers.count()} providers")
    
    results = []
    for provider in providers:
        result = sync_provider_products.delay(provider.id)
        results.append({
            'provider_id': provider.id,
            'provider_name': provider.name,
            'task_id': result.id
        })
    
    return {
        'total_providers': providers.count(),
        'tasks_launched': results
    }


@shared_task
def sync_provider_stock(provider_id):
    """
    Sincroniza solo el stock de productos (más rápido que sincronizar todo)
    
    Args:
        provider_id: ID del Provider
    """
    try:
        provider = Provider.objects.get(id=provider_id, is_active=True)
        odoo = get_odoo_connector_for_provider(provider)
        
        # Obtener todos los productos del provider en marketplace
        marketplace_products = Product.objects.filter(provider=provider, is_active=True)
        
        stats = {'updated': 0, 'errors': 0}
        
        for product in marketplace_products:
            try:
                # Obtener stock actualizado de Odoo
                stock_info = odoo.get_product_stock(product.odoo_product_id)
                
                if stock_info:
                    product.stock = int(stock_info.get('qty_available', 0))
                    product.last_sync_at = timezone.now()
                    product.save(update_fields=['stock', 'last_sync_at'])
                    stats['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error al actualizar stock de producto {product.id}: {e}")
                stats['errors'] += 1
        
        logger.info(f"Stock actualizado para {provider.name}: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error en sync_provider_stock: {e}")
        return {'error': str(e)}


@shared_task
def check_providers_for_upgrade():
    """
    Verifica si algún provider necesita upgrade de tier
    Tarea que corre diariamente
    """
    providers = Provider.objects.filter(is_active=True, is_approved=True)
    
    upgrade_suggestions = []
    
    for provider in providers:
        suggested_tier = provider.check_upgrade_needed()
        
        if suggested_tier:
            upgrade_suggestions.append({
                'provider_id': provider.id,
                'provider_name': provider.name,
                'current_tier': provider.tier,
                'suggested_tier': suggested_tier,
                'usage': provider.get_usage_percentage()
            })
            
            logger.info(
                f"Provider {provider.name} necesita upgrade: "
                f"{provider.tier} → {suggested_tier}"
            )
            
            # TODO: Enviar notificación al provider
            # send_upgrade_notification.delay(provider.id, suggested_tier)
    
    return {
        'total_checked': providers.count(),
        'upgrades_needed': len(upgrade_suggestions),
        'suggestions': upgrade_suggestions
    }


@shared_task
def create_order_in_odoo(marketplace_order_id):
    """
    Crea una orden de venta en el Odoo del provider correspondiente
    
    Args:
        marketplace_order_id: ID de la orden en el marketplace
    """
    # TODO: Implementar cuando tengamos el modelo Order
    pass


# ====== TAREAS DE MANTENIMIENTO ======

@shared_task
def verify_provider_odoo_connection(provider_id):
    """
    Verifica que la conexión a Odoo del provider funcione correctamente
    
    Args:
        provider_id: ID del Provider
        
    Returns:
        dict: Resultado de la verificación
    """
    try:
        provider = Provider.objects.get(id=provider_id)
        
        if not provider.has_odoo_credentials():
            return {
                'success': False,
                'error': 'Provider no tiene credenciales de Odoo'
            }
        
        # Intentar conectar con Odoo
        odoo = get_odoo_connector_for_provider(provider)
        
        # Verificar que la company existe
        company = odoo.get_company(provider.odoo_company_id)
        if not company:
            return {
                'success': False,
                'error': f'Company {provider.odoo_company_id} no existe en Odoo'
            }
        
        # Verificar que el usuario existe
        user = odoo.get_user(provider.odoo_user_id)
        if not user:
            return {
                'success': False,
                'error': f'Usuario {provider.odoo_user_id} no existe en Odoo'
            }
        
        return {
            'success': True,
            'provider': provider.name,
            'company': company['name'],
            'user': user['login'],
            'message': 'Conexión verificada correctamente'
        }
        
    except Provider.DoesNotExist:
        return {'success': False, 'error': 'Provider no encontrado'}
    except Exception as e:
        logger.exception(f"Error verificando conexión de provider {provider_id}: {e}")
        return {'success': False, 'error': str(e)}