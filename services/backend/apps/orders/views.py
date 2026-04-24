"""
Views para Orders - API REST y Lógica de Negocio
"""
import hmac
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)

from .models import Order, SubOrder, OrderItem, PaymentProof
from .serializers import (
    OrderSerializer,
    SubOrderSerializer,
    OrderItemSerializer,
    PaymentProofSerializer,
    CreateOrderSerializer,
    UploadPaymentProofSerializer,
    ConfirmPaymentSerializer,
    CheckoutPreviewSerializer,
)
from .pricing.customer_discount import calcular_descuento_suborder
from apps.customer.models import Customer
from apps.products.models import Product


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de órdenes
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar órdenes según el usuario"""
        user = self.request.user

        base_qs = Order.objects.select_related(
            'customer__user', 'shipping_address',
        ).prefetch_related(
            'sub_orders__provider',
            'sub_orders__items__product',
            'sub_orders__items__provider',
            'sub_orders__payments',
        )

        # Si es customer, solo sus órdenes
        if hasattr(user, 'customer_profile'):
            return base_qs.filter(customer=user.customer_profile)

        # Si es admin, todas las órdenes
        if user.is_staff:
            return base_qs

        return Order.objects.none()
    
    @action(detail=False, methods=['post'], url_path='checkout-preview')
    def checkout_preview(self, request):
        """
        Previsualización del checkout con descuentos aplicados.
        No crea ninguna orden. Útil para el frontend antes de confirmar.

        Request:
            { "customer_id": 1, "items": [{"product_id": 5, "quantity": 2}, ...] }

        Response:
            {
              "providers": [
                {
                  "provider_id": 1, "provider_name": "...",
                  "igv_applicable": true,
                  "subtotal": "250.00",
                  "discount_percent": "5.00",
                  "discount": "13.00",
                  "igv_amount": "42.66",
                  "total": "279.66",
                  "items": [...]
                }
              ],
              "summary": { "subtotal": ..., "discount": ..., "igv": ..., "total": ... }
            }
        """
        serializer = CheckoutPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer = Customer.objects.get(id=data['customer_id'])

        # Cargar todos los productos en una sola query para evitar N+1
        product_ids = [item_data['product_id'] for item_data in data['items']]
        products_map = {
            p.id: p
            for p in Product.objects.select_related('provider').filter(id__in=product_ids)
        }

        # Agrupar items por proveedor
        items_by_provider = {}
        for item_data in data['items']:
            product = products_map[item_data['product_id']]
            provider = product.provider
            if provider.id not in items_by_provider:
                items_by_provider[provider.id] = {'provider': provider, 'items': []}
            items_by_provider[provider.id]['items'].append({
                'product': product,
                'quantity': item_data['quantity'],
            })

        providers_preview = []
        summary_subtotal = Decimal('0.00')
        summary_discount = Decimal('0.00')
        summary_igv = Decimal('0.00')
        summary_total = Decimal('0.00')

        for provider_data in items_by_provider.values():
            provider = provider_data['provider']
            igv_rate = Decimal('18.00') if provider.igv_applicable else Decimal('0.00')

            sub_subtotal = Decimal('0.00')
            sub_igv = Decimal('0.00')
            items_detail = []

            for item_info in provider_data['items']:
                product = item_info['product']
                qty = item_info['quantity']
                base = product.price * qty
                igv_amount = (base * igv_rate / 100).quantize(Decimal('0.01')) if provider.igv_applicable else Decimal('0.00')

                sub_subtotal += base
                sub_igv += igv_amount
                items_detail.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_sku': product.reference,
                    'quantity': qty,
                    'unit_price': str(product.price),
                    'igv_amount': str(igv_amount),
                    'line_total': str(base + igv_amount),
                })

            discount_pct, discount_monto = calcular_descuento_suborder(customer, provider, sub_subtotal)
            provider_total = sub_subtotal - discount_monto + sub_igv

            providers_preview.append({
                'provider_id': provider.id,
                'provider_name': provider.name,
                'igv_applicable': provider.igv_applicable,
                'subtotal': str(sub_subtotal),
                'discount_percent': str(discount_pct),
                'discount': str(discount_monto),
                'igv_amount': str(sub_igv),
                'total': str(provider_total),
                'items': items_detail,
            })

            summary_subtotal += sub_subtotal
            summary_discount += discount_monto
            summary_igv += sub_igv
            summary_total += provider_total

        return Response({
            'providers': providers_preview,
            'summary': {
                'subtotal': str(summary_subtotal),
                'discount': str(summary_discount),
                'igv': str(summary_igv),
                'total': str(summary_total),
            },
        })

    @transaction.atomic
    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """
        Crear una nueva orden
        
        Flujo:
        1. Validar datos
        2. Crear Order principal
        3. Agrupar items por proveedor
        4. Crear SubOrders
        5. Crear OrderItems
        6. Calcular totales
        """
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # 1. Obtener customer
        customer = Customer.objects.get(id=data['customer_id'])
        
        # 2. Crear Order principal
        order = Order.objects.create(
            customer=customer,
            delivery_method=data['delivery_method'],
            shipping_address_id=data.get('shipping_address_id'),
            customer_notes=data.get('customer_notes', ''),
            status='pendiente_pago',
            payment_deadline=timezone.now() + timedelta(hours=3),  # TTL 3h para expiración
        )
        
        # 3. Agrupar items por proveedor
        # Cargar todos los productos en una sola query para evitar N+1
        product_ids = [item_data['product_id'] for item_data in data['items']]
        products_map = {
            p.id: p
            for p in Product.objects.select_related('provider').filter(id__in=product_ids)
        }

        items_by_provider = {}
        for item_data in data['items']:
            product = products_map[item_data['product_id']]
            provider = product.provider

            if provider.id not in items_by_provider:
                items_by_provider[provider.id] = {
                    'provider': provider,
                    'items': []
                }

            items_by_provider[provider.id]['items'].append({
                'product': product,
                'quantity': item_data['quantity']
            })
        
        # 4 y 5. Crear SubOrders y OrderItems
        order_subtotal = Decimal('0.00')
        order_discount = Decimal('0.00')
        order_tax = Decimal('0.00')
        
        for provider_data in items_by_provider.values():
            provider = provider_data['provider']
            
            # Crear SubOrder
            sub_order = SubOrder.objects.create(
                order=order,
                provider=provider,
                igv_rate=Decimal('18.00') if provider.igv_applicable else Decimal('0.00'),
                status='pendiente_pago'
            )
            
            sub_order_subtotal = Decimal('0.00')
            sub_order_igv = Decimal('0.00')
            
            # Crear OrderItems
            for item_info in provider_data['items']:
                product = item_info['product']
                quantity = item_info['quantity']
                
                # Precio unitario
                unit_price = product.price
                
                # Calcular IGV por item
                igv_rate = sub_order.igv_rate
                base_price = unit_price * quantity
                
                if provider.igv_applicable:
                    # IGV = base * 0.18
                    igv_amount = (base_price * igv_rate / 100).quantize(Decimal('0.01'))
                else:
                    igv_amount = Decimal('0.00')
                
                item_subtotal = base_price + igv_amount
                
                # Crear OrderItem
                OrderItem.objects.create(
                    sub_order=sub_order,
                    product=product,
                    provider=provider,
                    product_name=product.name,
                    product_sku=product.reference,
                    quantity=quantity,
                    unit_price=unit_price,
                    igv_rate=igv_rate,
                    igv_amount=igv_amount,
                    discount=Decimal('0.00'),
                    subtotal=item_subtotal
                )
                
                sub_order_subtotal += base_price
                sub_order_igv += igv_amount
            
            # Actualizar SubOrder totales
            # Calcular descuento cliente-proveedor sobre el subtotal (sin IGV)
            descuento_pct, descuento_monto = calcular_descuento_suborder(
                customer, provider, sub_order_subtotal
            )

            sub_order.subtotal = sub_order_subtotal
            sub_order.discount_percent = descuento_pct
            sub_order.discount = descuento_monto
            sub_order.igv_amount = sub_order_igv
            sub_order.total = sub_order_subtotal - descuento_monto + sub_order_igv
            sub_order.save()

            # ✅ NO se encola ninguna tarea Celery hacia Odoo aquí (create_order).
            # El draft a Odoo se encola en upload_payment_proof cuando el cliente sube
            # su comprobante (SubOrder.status → 'pago_en_revision').

            order_subtotal += sub_order_subtotal
            order_discount += descuento_monto
            order_tax += sub_order_igv
        
        # 6. Actualizar Order totales
        order.subtotal = order_subtotal
        order.discount = order_discount
        order.tax = order_tax
        order.total = order_subtotal - order_discount + order_tax
        order.save()
        
        # Retornar orden creada
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def upload_payment_proof(self, request):
        """
        Cliente sube comprobante de pago por una SubOrder.
        Crea un PaymentProof y transiciona la SubOrder a 'pago_en_revision'.
        Si había un rechazo previo (payment_rejected=True), limpia el flag.
        """
        serializer = UploadPaymentProofSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        sub_order = SubOrder.objects.get(id=data['sub_order_id'])

        # Guard: solo se permite subir comprobante desde estados válidos.
        # 'pendiente_pago'  → primera subida (timer activo).
        # 'pago_rechazado'  → el proveedor rechazó y el cliente corrige.
        ESTADOS_PERMITIDOS = ('pendiente_pago', 'pago_rechazado')
        if sub_order.status not in ESTADOS_PERMITIDOS:
            return Response(
                {'error': f'No se puede subir un comprobante en estado "{sub_order.status}".'
                          f' Estados permitidos: {ESTADOS_PERMITIDOS}.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        es_resubida = sub_order.status == 'pago_rechazado'

        # Crear PaymentProof (en Paso 3 esto será reemplazado por PaymentTransaction)
        payment_proof = PaymentProof.objects.create(
            sub_order=sub_order,
            payment_method=data['payment_method'],
            file=data['file'],
            operation_number=data.get('operation_number', ''),
            amount=data['amount'],
            uploaded_by=request.user
        )

        # Transición de estado + limpiar flag de rechazo
        sub_order.status = 'pago_en_revision'
        sub_order.payment_rejected = False
        sub_order.rejection_reason = ''
        sub_order.save(update_fields=['status', 'payment_rejected', 'rejection_reason', 'updated_at'])

        # Si es una resubida (pago_rechazado → pago_en_revision), la sale.order ya
        # existe en Odoo (odoo_sale_id presente). La tarea _enqueue_create_odoo es
        # idempotente y la omitirá, pero el signal post_save sincronizará
        # x_payment_status → 'pendiente_revision' automáticamente.
        if not es_resubida:
            sub_order_id_for_celery = sub_order.id
            transaction.on_commit(
                lambda sid=sub_order_id_for_celery: _enqueue_create_odoo(sid)
            )
        else:
            # Re-subida (pago_rechazado → pago_en_revision):
            # La sale.order ya existe en Odoo. Solo actualizamos x_payment_status
            # → 'pendiente_revision' para que el proveedor sepa que hay un nuevo comprobante.
            sub_order_id_for_celery = sub_order.id
            transaction.on_commit(
                lambda sid=sub_order_id_for_celery: _enqueue_update_payment_status(sid)
            )
            logger.info(
                "🔄 upload_payment_proof: resubida de comprobante para SubOrder %s "
                "(pago_rechazado → pago_en_revision). Actualizando x_payment_status en Odoo.",
                sub_order.sub_order_number,
            )

        return Response({
            'message': 'Comprobante subido correctamente' if not es_resubida else 'Comprobante corregido correctamente',
            'payment_proof': PaymentProofSerializer(payment_proof).data
        }, status=status.HTTP_201_CREATED)


def _enqueue_create_odoo(sub_order_id):
    """
    Encola la tarea Celery create_odoo_sale_order después del commit de la transacción.
    Se llama desde upload_payment_proof (primera subida, pago_en_revision).
    La tarea es idempotente: omite silenciosamente si odoo_sale_id ya existe.
    """
    try:
        from .tasks import create_odoo_sale_order
        create_odoo_sale_order.delay(sub_order_id)
        logger.info(f"📬 Tarea Celery encolada → create_odoo_sale_order para SubOrder {sub_order_id}")
    except Exception as e:
        logger.warning(f"⚠️  No se pudo encolar tarea Odoo para SubOrder {sub_order_id}: {e}")


def _enqueue_update_payment_status(sub_order_id):
    """
    Encola la tarea Celery update_suborder_payment_status después del commit.
    Se llama desde upload_payment_proof en resubidas (pago_rechazado → pago_en_revision)
    para actualizar x_payment_status → 'pendiente_revision' en la sale.order existente.
    """
    try:
        from .tasks import update_suborder_payment_status
        update_suborder_payment_status.delay(sub_order_id)
        logger.info(f"📬 Tarea Celery encolada → update_suborder_payment_status para SubOrder {sub_order_id}")
    except Exception as e:
        logger.warning(f"⚠️  No se pudo encolar tarea update_payment_status para SubOrder {sub_order_id}: {e}")


class SubOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para sub-órdenes (solo lectura para clientes)
    """
    serializer_class = SubOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar sub-órdenes según el usuario"""
        user = self.request.user

        base_qs = SubOrder.objects.select_related(
            'order', 'provider',
        ).prefetch_related(
            'items__product',
            'items__provider',
            'payments',
        )

        # Si es customer
        if hasattr(user, 'customer_profile'):
            return base_qs.filter(order__customer=user.customer_profile)

        # Si es vendor (provider owner)
        if hasattr(user, 'owned_providers'):
            provider_ids = user.owned_providers.values_list('id', flat=True)
            return base_qs.filter(provider_id__in=provider_ids)

        # Si es admin
        if user.is_staff:
            return SubOrder.objects.all()
        
        return SubOrder.objects.none()
    
    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """
        Vendor confirma o rechaza el pago
        """
        sub_order = self.get_object()
        
        # Validar que el usuario es el owner del provider
        if not request.user.is_staff:
            if not hasattr(request.user, 'owned_providers'):
                return Response(
                    {'error': 'No tienes permisos para confirmar pagos'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if sub_order.provider not in request.user.owned_providers.all():
                return Response(
                    {'error': 'No eres el propietario de este proveedor'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        serializer = ConfirmPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Obtener el comprobante más reciente en estado 'uploaded' para actualizarlo.
        latest_proof = (
            sub_order.payments.filter(status='uploaded').order_by('-uploaded_at').first()
        )

        if data['action'] == 'confirm':
            # Aprobar el comprobante
            if latest_proof:
                latest_proof.status = 'approved'
                latest_proof.verified_by = request.user
                latest_proof.verified_at = timezone.now()
                latest_proof.save(update_fields=['status', 'verified_by', 'verified_at'])

            # En v4 el proveedor confirma desde Odoo → SubOrder pasa directamente a 'confirmado'.
            # La sale.order ya existe en Odoo (draft) desde que el cliente subió el comprobante.
            # No se encola Celery de nuevo: la tarea es idempotente y el draft ya existe.
            sub_order.status = 'confirmado'
            sub_order.confirmed_at = timezone.now()
            sub_order.payment_rejected = False

            message = 'Pago aprobado y pedido confirmado'
        else:
            # Rechazar el comprobante + volver a pendiente_pago
            # El cliente verá el aviso y podrá subir un nuevo comprobante.
            rejection_reason = data.get('rejection_reason', '')
            if latest_proof:
                latest_proof.status = 'rejected'
                latest_proof.rejection_reason = rejection_reason
                latest_proof.verified_by = request.user
                latest_proof.verified_at = timezone.now()
                latest_proof.save(update_fields=[
                    'status', 'rejection_reason', 'verified_by', 'verified_at'
                ])

            sub_order.status = 'pago_rechazado'
            sub_order.payment_rejected = True
            message = 'Pago rechazado'

        sub_order.save()

        return Response({
            'message': message,
            'sub_order': SubOrderSerializer(sub_order).data
        })

    @action(detail=True, methods=['post'], url_path='mark-received')
    def mark_received(self, request, pk=None):
        """Cliente confirma que ya recibió la suborden."""
        sub_order = self.get_object()

        is_customer_owner = (
            hasattr(request.user, 'customer_profile')
            and sub_order.order.customer_id == request.user.customer_profile.id
        )

        if not (request.user.is_staff or is_customer_owner):
            return Response(
                {'error': 'No tienes permisos para marcar esta suborden como recibida'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if sub_order.status == 'cancelado':
            return Response(
                {'error': 'No se puede marcar como recibida una suborden cancelada'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sub_order.status not in ['enviado', 'entregado']:
            return Response(
                {'error': 'Solo se puede confirmar recepción para subórdenes enviadas'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sub_order.status != 'entregado':
            sub_order.status = 'entregado'

        if not sub_order.delivered_at:
            sub_order.delivered_at = timezone.now()

        sub_order.save(update_fields=['status', 'delivered_at', 'updated_at'])

        try:
            from .signals import update_odoo_delivery_status
            update_odoo_delivery_status(sub_order)
        except Exception as e:
            logger.warning(
                "⚠️ No se pudo sincronizar estado recibido con Odoo para %s: %s",
                sub_order.sub_order_number,
                e,
            )

        return Response({
            'message': 'Suborden marcada como recibida',
            'sub_order': SubOrderSerializer(sub_order).data,
        })


class VendorOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet especial para vendedores - Ver sus SubOrders
    """
    serializer_class = SubOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Solo SubOrders del proveedor del usuario"""
        user = self.request.user
        
        if hasattr(user, 'owned_providers'):
            provider_ids = user.owned_providers.values_list('id', flat=True)
            return SubOrder.objects.filter(
                provider_id__in=provider_ids
            ).select_related('order', 'provider').prefetch_related('items', 'payments')
        
        return SubOrder.objects.none()
    
    @action(detail=False, methods=['get'])
    def pending_confirmation(self, request):
        """Sub-órdenes con comprobante subido pendiente de revisión del proveedor"""
        queryset = self.get_queryset().filter(status='pago_en_revision')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estadísticas de órdenes del vendor (1 query agregada)"""
        qs = self.get_queryset()

        counts = qs.aggregate(
            total_orders      =Count('id'),
            pendiente_pago    =Count('id', filter=Q(status='pendiente_pago')),
            pago_en_revision  =Count('id', filter=Q(status='pago_en_revision')),
            pago_rechazado    =Count('id', filter=Q(status='pago_rechazado')),
            confirmado        =Count('id', filter=Q(status='confirmado')),
            enviado           =Count('id', filter=Q(status='enviado')),
            entregado         =Count('id', filter=Q(status='entregado')),
            cancelado         =Count('id', filter=Q(status='cancelado')),
            con_rechazo_previo=Count('id', filter=Q(payment_rejected=True)),
            error_odoo        =Count('id', filter=Q(odoo_sync_error=True)),
        )

        return Response(counts)



# ============================================================================
# WEBHOOK ENDPOINT - Recibir actualizaciones desde Odoo
# ============================================================================

class OdooWebhookView(viewsets.ViewSet):
    """
    Endpoint para recibir webhooks desde Odoo
    URL: /api/orders/odoo-webhook/
    """
    permission_classes = []  # Sin autenticación estándar, usa token custom
    authentication_classes = []  # Sin autenticación
    
    @action(detail=False, methods=['post'], url_path='sale-order-update')
    def sale_order_update(self, request):
        """
        Webhook cuando cambia el estado de una Sale Order en Odoo
        
        Payload esperado:
        {
            "token": "SECRET_TOKEN",
            "sale_order_id": 123,
            "state": "sale",
            "invoice_status": "invoiced"
        }
        """
        from django.conf import settings
        import logging
        
        logger = logging.getLogger(__name__)
        
        # 1. Validar token de seguridad (compare_digest evita timing attacks)
        token = request.data.get('token') or ''
        expected_token = getattr(settings, 'ODOO_WEBHOOK_TOKEN', 'change-me-in-production')

        if not hmac.compare_digest(token, expected_token):
            logger.warning("❌ Webhook recibido con token inválido")
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 2. Extraer datos del webhook
        sale_order_id = request.data.get('sale_order_id')
        odoo_state = request.data.get('state')
        invoice_status = request.data.get('invoice_status')
        
        logger.info(f"📥 Webhook recibido: Sale Order {sale_order_id}, Estado: {odoo_state}")
        
        if not sale_order_id or not odoo_state:
            return Response(
                {'error': 'Missing required fields'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3. Buscar SubOrder correspondiente
        try:
            sub_order = SubOrder.objects.get(odoo_sale_id=sale_order_id)
        except SubOrder.DoesNotExist:
            logger.warning(f"⚠️  No se encontró SubOrder con odoo_sale_id={sale_order_id}")
            return Response(
                {'error': 'SubOrder not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 4. Mapear estado de Odoo a Django (v4)
        # Odoo notifica: 'sale' → SubOrder en 'confirmado'
        # Odoo notifica: 'cancel' → SubOrder en 'cancelado'
        # El despacho se sincroniza por separado desde stock.picking.
        estado_anterior = sub_order.status

        status_mapping = {
            'draft': 'pago_en_revision',   # cotización en draft = pago en revisión
            'sale':  'confirmado',          # cotización confirmada = pago aprobado
            'cancel': 'cancelado',
        }
        
        nuevo_estado = status_mapping.get(odoo_state, sub_order.status)

        # 5. Guardar si hay cambio real (idempotencia).
        if nuevo_estado == estado_anterior:
            logger.info(
                "ℹ️ sale_order_update: SubOrder %s ya está en %s, sin cambios.",
                sub_order.sub_order_number, estado_anterior,
            )
            return Response({
                'success': True,
                'sub_order_number': sub_order.sub_order_number,
                'estado_anterior': estado_anterior,
                'nuevo_estado': nuevo_estado,
                'message': 'Sin cambios (estado ya actualizado)',
            })

        # 6. Actualizar PaymentProof cuando el estado del pago cambia.
        # Cubre el caso en que review_payment falló o no llegó todavía.
        # Es idempotente: solo toca proofs en 'uploaded'.
        if nuevo_estado == 'confirmado':
            latest_proof = (
                sub_order.payments.filter(status='uploaded').order_by('-uploaded_at').first()
            )
            if latest_proof:
                latest_proof.status = 'approved'
                latest_proof.verified_at = timezone.now()
                latest_proof.save(update_fields=['status', 'verified_at'])
                logger.info(
                    "✅ sale_order_update: PaymentProof #%s → approved (SubOrder %s)",
                    latest_proof.pk, sub_order.sub_order_number,
                )
            else:
                # Normal cuando review_payment ya lo aprobó antes; solo es problema si
                # tampoco existe ningún proof approved.
                has_approved = sub_order.payments.filter(status='approved').exists()
                if not has_approved:
                    logger.warning(
                        "⚠️ sale_order_update: SubOrder %s confirmada sin PaymentProof "
                        "'uploaded' ni 'approved'. Revisar manualmente.",
                        sub_order.sub_order_number,
                    )
                else:
                    logger.info(
                        "ℹ️ sale_order_update: PaymentProof ya estaba approved (SubOrder %s). OK.",
                        sub_order.sub_order_number,
                    )

            sub_order.status = nuevo_estado
            sub_order.confirmed_at = sub_order.confirmed_at or timezone.now()
            sub_order.payment_rejected = False
            sub_order.save()

        else:
            sub_order.status = nuevo_estado
            sub_order.save()

        # El signal recalculate_order_status actualiza Order.status automáticamente.
        logger.info(
            "✅ sale_order_update: SubOrder %s actualizada: %s → %s",
            sub_order.sub_order_number, estado_anterior, nuevo_estado,
        )

        return Response({
            'success': True,
            'sub_order_number': sub_order.sub_order_number,
            'estado_anterior': estado_anterior,
            'nuevo_estado': nuevo_estado,
            'message': 'SubOrder actualizada correctamente',
        })

    @action(detail=False, methods=['post'], url_path='delivery-update')
    def delivery_update(self, request):
        """
        Webhook cuando se valida un stock.picking de salida en Odoo.

        Payload esperado:
        {
            "token": "SECRET_TOKEN",
            "sale_order_id": 123,
            "picking_id": 456,
            "picking_name": "AGU/OUT/00009",
            "state": "done",
            "picking_type_code": "outgoing"
        }
        """
        from django.conf import settings

        token = request.data.get('token') or ''
        expected_token = getattr(settings, 'ODOO_WEBHOOK_TOKEN', 'change-me-in-production')

        if not hmac.compare_digest(token, expected_token):
            logger.warning("❌ delivery_update: token inválido desde Odoo")
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

        sale_order_id = request.data.get('sale_order_id')
        picking_id = request.data.get('picking_id')
        picking_name = request.data.get('picking_name') or ''
        odoo_state = request.data.get('state')
        picking_type_code = request.data.get('picking_type_code')

        logger.info(
            "📦 delivery_update recibido: sale_order_id=%s, picking_id=%s, "
            "picking_name=%s, state=%s, picking_type_code=%s",
            sale_order_id,
            picking_id,
            picking_name,
            odoo_state,
            picking_type_code,
        )

        if not sale_order_id or not odoo_state:
            return Response(
                {'error': 'Missing required fields'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if picking_type_code and picking_type_code != 'outgoing':
            logger.info(
                "ℹ️ delivery_update ignorado: picking %s no es de salida (%s)",
                picking_name or picking_id,
                picking_type_code,
            )
            return Response({
                'success': True,
                'ignored': True,
                'reason': 'Picking is not outgoing',
            })

        if odoo_state != 'done':
            logger.info(
                "ℹ️ delivery_update ignorado: picking %s aún no está done (%s)",
                picking_name or picking_id,
                odoo_state,
            )
            return Response({
                'success': True,
                'ignored': True,
                'reason': 'Picking state is not done',
            })

        try:
            sub_order = SubOrder.objects.get(odoo_sale_id=sale_order_id)
        except SubOrder.DoesNotExist:
            logger.warning(
                "⚠️ delivery_update: No se encontró SubOrder con odoo_sale_id=%s",
                sale_order_id,
            )
            return Response({'error': 'SubOrder not found'}, status=status.HTTP_404_NOT_FOUND)

        estado_anterior = sub_order.status

        if sub_order.status == 'cancelado':
            logger.info(
                "ℹ️ delivery_update ignorado: SubOrder %s está cancelada",
                sub_order.sub_order_number,
            )
            return Response({
                'success': True,
                'ignored': True,
                'sub_order_number': sub_order.sub_order_number,
                'estado_actual': sub_order.status,
                'reason': 'SubOrder is cancelled',
            })

        update_fields = []

        if sub_order.status != 'entregado' and sub_order.status != 'enviado':
            sub_order.status = 'enviado'
            update_fields.append('status')

        if not sub_order.shipped_at:
            sub_order.shipped_at = timezone.now()
            update_fields.append('shipped_at')

        if update_fields:
            sub_order.save(update_fields=update_fields)

        try:
            from .signals import update_odoo_delivery_status
            update_odoo_delivery_status(sub_order)
        except Exception as e:
            logger.warning(
                "⚠️ delivery_update: no se pudo sincronizar estado logístico con Odoo para %s: %s",
                sub_order.sub_order_number,
                e,
            )

        logger.info(
            "✅ delivery_update: SubOrder %s actualizada %s → %s",
            sub_order.sub_order_number,
            estado_anterior,
            sub_order.status,
        )

        return Response({
            'success': True,
            'sub_order_number': sub_order.sub_order_number,
            'estado_anterior': estado_anterior,
            'nuevo_estado': sub_order.status,
            'shipped_at': sub_order.shipped_at.isoformat() if sub_order.shipped_at else None,
        })

    @action(detail=False, methods=['post'], url_path='mark-received')
    def mark_received(self, request):
        """
        Webhook interno para que Odoo/backoffice marque una SubOrder como recibida.

        Payload esperado:
        {
            "token": "SECRET_TOKEN",
            "suborder_number": "ORD-2026-00001-A"
        }
        """
        from django.conf import settings

        token = request.data.get('token') or ''
        expected_token = getattr(settings, 'ODOO_WEBHOOK_TOKEN', 'change-me-in-production')

        if not hmac.compare_digest(token, expected_token):
            logger.warning("❌ mark_received: token inválido desde Odoo")
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

        suborder_number = request.data.get('suborder_number')
        if not suborder_number:
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            sub_order = SubOrder.objects.get(sub_order_number=suborder_number)
        except SubOrder.DoesNotExist:
            logger.warning("⚠️ mark_received: No se encontró SubOrder %s", suborder_number)
            return Response({'error': 'SubOrder not found'}, status=status.HTTP_404_NOT_FOUND)

        if sub_order.status == 'cancelado':
            return Response(
                {'error': 'SubOrder is cancelled'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sub_order.status not in ['enviado', 'entregado']:
            return Response(
                {'error': 'SubOrder is not ready to be marked as received'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        estado_anterior = sub_order.status

        update_fields = []
        if sub_order.status != 'entregado':
            sub_order.status = 'entregado'
            update_fields.append('status')

        if not sub_order.delivered_at:
            sub_order.delivered_at = timezone.now()
            update_fields.append('delivered_at')

        if update_fields:
            sub_order.save(update_fields=update_fields)

        logger.info(
            "✅ mark_received: SubOrder %s actualizada %s → %s",
            sub_order.sub_order_number,
            estado_anterior,
            sub_order.status,
        )

        return Response({
            'success': True,
            'sub_order_number': sub_order.sub_order_number,
            'estado_anterior': estado_anterior,
            'nuevo_estado': sub_order.status,
            'delivered_at': sub_order.delivered_at.isoformat() if sub_order.delivered_at else None,
        })

    @action(detail=False, methods=['post'], url_path='review-payment')
    def review_payment(self, request):
        """
        Odoo llama este endpoint cuando el proveedor aprueba o rechaza el pago.

        Casos de uso:
          - Botón "Rechazar pago" en Odoo  → action='reject'
          - action_confirm override en Odoo → action='approve'

        Payload esperado:
        {
            "token": "SECRET_TOKEN",
            "suborder_number": "ORD-2026-00001-A",
            "action": "approve" | "reject",
            "rejection_reason": "Monto incorrecto"   ← solo para reject
        }

        Respuesta:
        {
            "success": true,
            "sub_order_number": "ORD-2026-00001-A",
            "new_status": "confirmado" | "pendiente_pago"
        }
        """
        from django.conf import settings

        # 1. Validar token
        token = request.data.get('token') or ''
        expected_token = getattr(settings, 'ODOO_WEBHOOK_TOKEN', 'change-me-in-production')
        if not hmac.compare_digest(token, expected_token):
            logger.warning("❌ review_payment: token inválido desde Odoo")
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)

        # 2. Validar campos requeridos
        suborder_number = request.data.get('suborder_number')
        action_type = request.data.get('action')
        rejection_reason = request.data.get('rejection_reason', '')

        if not suborder_number or action_type not in ('approve', 'reject'):
            return Response(
                {'error': 'suborder_number y action (approve|reject) son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Buscar SubOrder
        try:
            sub_order = SubOrder.objects.get(sub_order_number=suborder_number)
        except SubOrder.DoesNotExist:
            return Response(
                {'error': f'SubOrder {suborder_number} no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4. Obtener el último PaymentProof en estado 'uploaded'
        latest_proof = (
            sub_order.payments.filter(status='uploaded').order_by('-uploaded_at').first()
        )

        if action_type == 'approve':
            # Proveedor confirmó la cotización en Odoo → pago aprobado
            if latest_proof:
                latest_proof.status = 'approved'
                latest_proof.verified_at = timezone.now()
                latest_proof.save(update_fields=['status', 'verified_at'])
                logger.info(
                    "✅ review_payment [approve]: PaymentProof #%s → approved (SubOrder %s)",
                    latest_proof.pk, suborder_number,
                )
            else:
                has_approved = sub_order.payments.filter(status='approved').exists()
                if not has_approved:
                    logger.warning(
                        "⚠️ review_payment [approve]: SubOrder %s sin PaymentProof "
                        "'uploaded' ni 'approved'. Puede que sale_order_update ya lo procesó "
                        "o el comprobante no existe. Revisar manualmente.",
                        suborder_number,
                    )
                else:
                    logger.info(
                        "ℹ️ review_payment [approve]: PaymentProof ya estaba approved "
                        "(SubOrder %s). OK — sale_order_update puede haberlo adelantado.",
                        suborder_number,
                    )

            # Idempotente: solo actualiza si aún no está confirmado.
            if sub_order.status != 'confirmado':
                sub_order.status = 'confirmado'
                sub_order.confirmed_at = sub_order.confirmed_at or timezone.now()
                sub_order.payment_rejected = False
                sub_order.save()
            else:
                logger.info(
                    "ℹ️ review_payment [approve]: SubOrder %s ya estaba confirmada. Sin cambios.",
                    suborder_number,
                )

            logger.info(
                "✅ review_payment [approve]: SubOrder %s → confirmado", suborder_number,
            )
            return Response({
                'success': True,
                'sub_order_number': suborder_number,
                'new_status': 'confirmado',
            })

        else:  # reject
            # Proveedor rechazó el pago desde Odoo
            if latest_proof:
                latest_proof.status = 'rejected'
                latest_proof.rejection_reason = rejection_reason
                latest_proof.verified_at = timezone.now()
                latest_proof.save(
                    update_fields=['status', 'rejection_reason', 'verified_at']
                )
                logger.info(
                    "🚫 review_payment [reject]: PaymentProof #%s → rejected (SubOrder %s)",
                    latest_proof.pk, suborder_number,
                )
            else:
                logger.warning(
                    "⚠️ review_payment [reject]: SubOrder %s sin PaymentProof 'uploaded'. "
                    "No hay comprobante que rechazar formalmente.",
                    suborder_number,
                )

            sub_order.status = 'pago_rechazado'
            sub_order.payment_rejected = True
            sub_order.rejection_reason = rejection_reason
            sub_order.save()

            logger.info(
                "🚫 review_payment [reject]: SubOrder %s → pago_rechazado (motivo: %s)",
                suborder_number, rejection_reason[:80],
            )
            return Response({
                'success': True,
                'sub_order_number': suborder_number,
                'new_status': 'pago_rechazado',
                'rejection_reason': rejection_reason,
            })
