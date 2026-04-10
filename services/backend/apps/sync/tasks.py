"""
Tareas de sincronización entre Odoo y Django Marketplace
ACTUALIZADO: Incluye registro automático de vendors con setup completo de Odoo
"""
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.marketplace.models import Provider
from apps.products.models import Product, Category
from apps.sync.odoo_connector import OdooConnector, get_odoo_connector_for_provider
from apps.vehicles.models import VariantVehiculo
from apps.products.models import CompatibilidadProducto
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
    Sincroniza productos, categorías, almacenes y stock de un provider desde Odoo.

    Orden de ejecución:
      1. Categorías  — se crean/actualizan vinculando por odoo_category_id
      2. Almacenes   — se crean/actualizan vinculando por odoo_warehouse_id
      3. Productos   — se crean/actualizan con su categoría correcta
      4. Stock       — se actualiza por almacén usando stock.quant

    Args:
        provider_id: ID del Provider a sincronizar

    Returns:
        dict con estadísticas de la sincronización
    """
    try:
        provider = Provider.objects.get(id=provider_id, is_active=True, is_approved=True)
        logger.info(f"Iniciando sincronización completa para {provider.name}")

        odoo = get_odoo_connector_for_provider(provider)
        now = timezone.now()

        stats = {
            'provider': provider.name,
            'categories': {'created': 0, 'updated': 0},
            'products': {'total_odoo': 0, 'created': 0, 'updated': 0, 'errors': 0},
            'stock': {'updated': 0, 'errors': 0},
        }

        # ── 1. CATEGORÍAS ────────────────────────────────────────────────────
        # Se vinculan por odoo_category_id, no por nombre ni por PK de Django.
        # Esto garantiza que aunque los auto-increment difieran entre DBs, la
        # relación siempre es correcta.
        #
        # Paso 1a: crear/actualizar todas las categorías (sin parent todavía,
        #          para evitar referencias a nodos aún no creados).
        # Paso 1b: segunda pasada para asignar parent a partir de parent_id de
        #          Odoo — construye la jerarquía de 3 niveles correctamente.
        odoo_categories_raw = odoo.get_categories()
        # Filtrar la categoría raíz 'All' de Odoo — no existe en Django y no
        # se asigna a ningún producto; incluirla solo genera ruido.
        odoo_categories = [
            oc for oc in odoo_categories_raw
            if not (oc['name'] == 'All' and not oc.get('parent_id'))
        ]
        odoo_categ_map = {}  # {odoo_category_id: Category instance}
        # Estrategia de 3 vías para bridgear seed_categories → primera sync:
        #   1. Buscar por odoo_category_id     (syncs subsiguientes)
        #   2. Fallback: buscar por nombre     (primera sync tras seed_categories)
        #   3. Crear si realmente no existe
        for oc in odoo_categories:
            created = False
            try:
                cat = Category.objects.get(odoo_category_id=oc['id'])
                changed = False
                if cat.name != oc['name']:
                    cat.name = oc['name']
                    changed = True
                if not cat.is_active:
                    cat.is_active = True
                    changed = True
                if changed:
                    cat.save(update_fields=['name', 'is_active'])
            except Category.DoesNotExist:
                # Bridge: categoría creada por seed_categories (odoo_category_id=NULL)
                try:
                    cat = Category.objects.get(
                        name=oc['name'], odoo_category_id__isnull=True
                    )
                    cat.odoo_category_id = oc['id']
                    if not cat.is_active:
                        cat.is_active = True
                    cat.save(update_fields=['odoo_category_id', 'is_active'])
                except Category.DoesNotExist:
                    cat = Category(odoo_category_id=oc['id'], name=oc['name'], is_active=True)
                    cat.save()
                    created = True
                except Category.MultipleObjectsReturned:
                    cat = Category.objects.filter(
                        name=oc['name'], odoo_category_id__isnull=True
                    ).first()
                    cat.odoo_category_id = oc['id']
                    cat.save(update_fields=['odoo_category_id', 'is_active'])
            odoo_categ_map[oc['id']] = cat
            if created:
                stats['categories']['created'] += 1
            else:
                stats['categories']['updated'] += 1

        # Paso 1b — asignar parents
        for oc in odoo_categories:
            parent_raw = oc.get('parent_id')  # False o [id, 'nombre']
            if not parent_raw:
                continue
            parent_odoo_id = parent_raw[0]
            parent_cat = odoo_categ_map.get(parent_odoo_id)
            child_cat  = odoo_categ_map.get(oc['id'])
            if parent_cat and child_cat and child_cat.parent_id != parent_cat.pk:
                child_cat.parent = parent_cat
                child_cat.save(update_fields=['parent'])

        logger.info(
            f"{provider.name} — categorías: "
            f"+{stats['categories']['created']} / ~{stats['categories']['updated']}"
        )

        # ── 2. PRODUCTOS ────────────────────────────────────────────────────
        odoo_products = odoo.get_products(company_id=provider.odoo_company_id)
        stats['products']['total_odoo'] = len(odoo_products)

        for odoo_product in odoo_products:
            try:
                # Subir imagen a Cloudinary si existe en Odoo
                image_url = None
                image_cloudinary_id = None
                image_b64 = odoo_product.get('image_1920')
                if image_b64 and image_b64 is not False:
                    try:
                        import cloudinary.uploader, base64
                        image_data = base64.b64decode(image_b64)
                        product_ref = odoo_product.get('default_code') or str(odoo_product['id'])
                        upload_result = cloudinary.uploader.upload(
                            image_data,
                            public_id=f"ecomparts/products/{product_ref}",
                            overwrite=True,
                            resource_type="image",
                            transformation=[{
                                "width": 800, "height": 800,
                                "crop": "limit", "quality": "auto",
                                "fetch_format": "auto"
                            }]
                        )
                        image_url = upload_result.get('secure_url')
                        image_cloudinary_id = upload_result.get('public_id')
                        logger.info(f"✅ Imagen subida a Cloudinary: {image_url}")
                    except Exception as img_err:
                        logger.warning(f"⚠️ No se pudo subir imagen a Cloudinary: {img_err}")

                # Resolución de referencia con protección contra duplicados de Odoo
                raw_reference = odoo_product.get('default_code') or None
                if raw_reference:
                    conflict = Product.objects.filter(
                        provider=provider,
                        reference=raw_reference
                    ).exclude(odoo_product_id=odoo_product['id']).exists()
                    if conflict:
                        logger.warning(
                            f"Referencia duplicada en Odoo '{raw_reference}' "
                            f"(provider={provider.id}, odoo_id={odoo_product['id']}). "
                            f"Usando fallback ODOO-{odoo_product['id']}."
                        )
                        raw_reference = f"ODOO-{odoo_product['id']}"

                # Stock total directo desde qty_available de Odoo
                qty_available = int(odoo_product.get('qty_available') or 0)

                # Buscar o crear producto en marketplace
                # Resolver categoría vía odoo_category_id
                categ_raw = odoo_product.get('categ_id')  # (id, nombre) o False
                category = None
                if categ_raw and isinstance(categ_raw, (list, tuple)) and categ_raw[0]:
                    category = odoo_categ_map.get(categ_raw[0])

                # Resolver product_tmpl_id
                tmpl_raw = odoo_product.get('product_tmpl_id')
                tmpl_id = tmpl_raw[0] if isinstance(tmpl_raw, (list, tuple)) else tmpl_raw

                product, created = Product.objects.update_or_create(
                    provider=provider,
                    odoo_product_id=odoo_product['id'],
                    defaults={
                        'name': odoo_product['name'],
                        'reference': raw_reference,
                        'description': odoo_product.get('description_sale') or '',
                        'price': odoo_product.get('list_price', 0),
                        'image_url': image_url,
                        'image_cloudinary_id': image_cloudinary_id,
                        'product_type': odoo_product.get('type', 'product'),
                        'category': category,
                        'is_active': odoo_product.get('active', True),
                        'odoo_template_id': tmpl_id,
                        'odoo_state': 'synced',
                        'last_sync_at': now,
                        'total_stock_cached': qty_available,
                    }
                )

                if created:
                    stats['products']['created'] += 1
                else:
                    stats['products']['updated'] += 1

            except Exception as e:
                logger.error(f"Error sincronizando producto {odoo_product.get('id')}: {e}")
                stats['products']['errors'] += 1

        logger.info(
            f"{provider.name} — productos: "
            f"+{stats['products']['created']} / ~{stats['products']['updated']} "
            f"/ err {stats['products']['errors']}"
        )

        # ── 3. STOCK TOTAL ────────────────────────────────────────────────────
        # total_stock_cached ya se actualizó en el paso de productos
        # desde qty_available de Odoo. No hay tablas de stock separadas.
        stats['stock']['updated'] = stats['products']['created'] + stats['products']['updated']
        logger.info(
            f"{provider.name} — stock: {stats['stock']['updated']} productos con stock actualizado"
        )

        # ── 4. COMPATIBILIDADES PRODUCTO ↔ VEHÍCULO ──────────────────────────
        # Se ejecuta al final para garantizar que los productos ya tienen
        # odoo_template_id poblado (paso anterior).
        compat_stats = sync_provider_compatibility(provider_id)
        stats['compatibility'] = {
            'created': compat_stats.get('compat_created', 0),
            'updated': compat_stats.get('compat_updated', 0),
            'skipped': (
                compat_stats.get('skipped_no_product', 0) +
                compat_stats.get('skipped_no_variant', 0)
            ),
            'errors': compat_stats.get('errors', 0),
        }

        # Actualizar contador de productos activos del provider
        provider.total_products = Product.objects.filter(
            provider=provider, is_active=True
        ).count()
        provider.save(update_fields=['total_products'])

        logger.info(f"Sincronización completa para {provider.name}: {stats}")
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
def sync_all_stock():
    """
    Dispara sync_provider_stock para todos los providers activos.
    Se ejecuta cada 15 minutos vía Celery Beat — solo actualiza stock.quant,
    no toca categorías ni datos de producto.
    """
    providers = Provider.objects.filter(
        is_active=True,
        is_approved=True,
        odoo_company_id__isnull=False
    )
    logger.info(f"Iniciando sync de stock para {providers.count()} providers")
    results = []
    for provider in providers:
        result = sync_provider_stock.delay(provider.id)
        results.append({'provider_id': provider.id, 'task_id': result.id})
    return {'total_providers': providers.count(), 'tasks_launched': results}


@shared_task
def sync_provider_compatibility(provider_id):
    """
    Sincroniza las compatibilidades de producto↔vehículo desde Odoo.

    Flujo:
      1. Obtiene todos los productos del provider que tienen odoo_template_id
      2. Consulta autopart.compatibility en Odoo para esos templates (en lote)
      3. Para cada registro de compatibilidad:
           - Resuelve el Product Django por odoo_template_id
           - Resuelve el VariantVehiculo Django por:
               a) vehiculo.variante.django_external_id  (si está seteado, es el PK de Django)
               b) VariantVehiculo.odoo_variante_id       (si fue sinced previamente)
               c) Coincidencia por clave natural (modelo+motor+transmision+traccion+años)
      4. Crea o actualiza CompatibilidadProducto con las notas de montaje

    Args:
        provider_id: ID del Provider

    Returns:
        dict con estadísticas
    """
    try:
        provider = Provider.objects.get(id=provider_id, is_active=True)
        odoo = get_odoo_connector_for_provider(provider)

        stats = {
            'provider': provider.name,
            'compat_created': 0,
            'compat_updated': 0,
            'skipped_no_product': 0,
            'skipped_no_variant': 0,
            'errors': 0,
        }

        # ── 1. Templates del provider ──────────────────────────────────────
        provider_products = list(
            Product.objects
            .filter(provider=provider, odoo_template_id__isnull=False)
            .values('id', 'odoo_template_id')
        )
        tmpl_to_product_id = {p['odoo_template_id']: p['id'] for p in provider_products}
        tmpl_ids = list(tmpl_to_product_id.keys())

        if not tmpl_ids:
            logger.info(f"{provider.name}: sin productos con odoo_template_id, omitiendo compatibilidades")
            return stats

        # ── 2. Compatibilidades desde Odoo (una sola query) ────────────────
        compat_records = odoo.get_compatibilities(tmpl_ids)
        logger.info(f"{provider.name}: {len(compat_records)} compatibilidad(es) encontradas en Odoo")

        # ── 3. Prefetch variantes de Odoo (una sola query) ─────────────────
        odoo_variant_ids = [
            r['variant_id'][0] for r in compat_records
            if r.get('variant_id')
        ]
        odoo_variant_map = odoo.get_vehicle_variants(list(set(odoo_variant_ids)))

        # ── 4. Procesar cada compatibilidad ────────────────────────────────
        for record in compat_records:
            try:
                # Resolver Product
                tmpl_id = record['product_tmpl_id'][0] if record.get('product_tmpl_id') else None
                product_id = tmpl_to_product_id.get(tmpl_id)
                if not product_id:
                    stats['skipped_no_product'] += 1
                    continue

                # Resolver VariantVehiculo
                odoo_variant_id = record['variant_id'][0] if record.get('variant_id') else None
                variant = _resolve_django_variant(odoo_variant_id, odoo_variant_map)
                if not variant:
                    stats['skipped_no_variant'] += 1
                    logger.warning(
                        f"No se encontró VariantVehiculo para odoo_variante_id={odoo_variant_id} "
                        f"(product_tmpl_id={tmpl_id})"
                    )
                    continue

                # Persistir odoo_variante_id para futuras syncs
                if variant.odoo_variante_id != odoo_variant_id:
                    VariantVehiculo.objects.filter(pk=variant.pk).update(
                        odoo_variante_id=odoo_variant_id
                    )

                # Crear / actualizar CompatibilidadProducto
                notes = record.get('fitment_notes') or ''
                _, created = CompatibilidadProducto.objects.update_or_create(
                    producto_id=product_id,
                    variante=variant,
                    defaults={'notas_instalacion': notes[:255]}
                )
                if created:
                    stats['compat_created'] += 1
                else:
                    stats['compat_updated'] += 1

            except Exception as e:
                stats['errors'] += 1
                logger.error(
                    f"Error procesando compatibilidad odoo_id={record.get('id')}: {e}",
                    exc_info=True,
                )

        logger.info(f"{provider.name} compatibilidades: {stats}")
        return stats

    except Provider.DoesNotExist:
        return {'error': 'Provider no encontrado'}
    except Exception as e:
        logger.error(f"Error en sync_provider_compatibility provider={provider_id}: {e}")
        return {'error': str(e)}


def _resolve_django_variant(odoo_variant_id, odoo_variant_map):
    """
    Resuelve un VariantVehiculo de Django a partir del ID de Odoo.

    Estrategia en orden de prioridad:
      1. VariantVehiculo.odoo_variante_id == odoo_variant_id  (más rápido)
      2. vehiculo.variante.django_external_id → PK directo en Django
      3. Natural key: modelo+motor+transmision+traccion+años via los IDs de Odoo
         que ya están guardados en Odoo como relaciones a los catalogs
         (fallback, solo si las entidades tienen sus propios django_external_id)

    Args:
        odoo_variant_id (int): ID de vehiculo.variante en Odoo
        odoo_variant_map (dict): Resultado de get_vehicle_variants()

    Returns:
        VariantVehiculo | None
    """
    if not odoo_variant_id:
        return None

    # Estrategia 1: ya tenemos el odoo_variante_id en Django
    try:
        v = VariantVehiculo.objects.get(odoo_variante_id=odoo_variant_id)
        return v
    except VariantVehiculo.DoesNotExist:
        pass

    # Estrategia 2: usar django_external_id guardado en Odoo
    odoo_record = odoo_variant_map.get(odoo_variant_id)
    if odoo_record:
        django_ext_id = odoo_record.get('django_external_id')
        if django_ext_id:
            try:
                django_pk = int(django_ext_id)
                return VariantVehiculo.objects.get(pk=django_pk)
            except (ValueError, TypeError, VariantVehiculo.DoesNotExist):
                pass

    # Estrategia 3: matching por clave natural (anio_desde + anio_hasta + slugs)
    # Solo llega aquí si ni odoo_variante_id ni django_external_id están seteados.
    # En ese caso no podemos resolver sin riesgo de falsos positivos.
    logger.debug(
        f"No se pudo resolver VariantVehiculo para odoo_variante_id={odoo_variant_id}. "
        "Ejecutar push de vehículos desde Django a Odoo para poblar django_external_id."
    )
    return None


@shared_task
def sync_provider_stock(provider_id):
    """
    Actualiza total_stock_cached de todos los productos del provider
    consultando qty_available directamente desde Odoo.
    Más rápido que la sync completa: no toca categorías ni datos de producto.

    Args:
        provider_id: ID del Provider
    """
    try:
        provider = Provider.objects.get(id=provider_id, is_active=True)
        odoo = get_odoo_connector_for_provider(provider)

        stats = {'updated': 0, 'errors': 0}

        odoo_products = odoo.get_products(company_id=provider.odoo_company_id)

        for op in odoo_products:
            qty = int(op.get('qty_available') or 0)
            try:
                rows = Product.objects.filter(
                    provider=provider,
                    odoo_product_id=op['id']
                ).update(total_stock_cached=qty)
                stats['updated'] += rows
            except Exception as e:
                logger.error(
                    f"Error actualizando stock odoo_product_id={op['id']}: {e}"
                )
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