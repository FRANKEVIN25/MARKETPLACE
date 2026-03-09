"""
Views para Orders - API REST y Lógica de Negocio
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
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
)
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
        
        # Si es customer, solo sus órdenes
        if hasattr(user, 'customer_profile'):
            return Order.objects.filter(customer=user.customer_profile)
        
        # Si es admin, todas las órdenes
        if user.is_staff:
            return Order.objects.all()
        
        return Order.objects.none()
    
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
        items_by_provider = {}
        for item_data in data['items']:
            product = Product.objects.select_related('provider').get(id=item_data['product_id'])
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
                    order=order,
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
            sub_order.subtotal = sub_order_subtotal
            sub_order.igv_amount = sub_order_igv
            sub_order.total = sub_order_subtotal + sub_order_igv
            sub_order.save()

            # ✅ NO se encola ninguna tarea Celery hacia Odoo aquí (create_order).
            # El draft a Odoo se encola en upload_payment_proof cuando el cliente sube
            # su comprobante (SubOrder.status → 'pago_en_revision').

            order_subtotal += sub_order_subtotal
        
        # 6. Actualizar Order totales
        order.subtotal = order_subtotal
        order.tax = order_tax
        order.total = order_subtotal + order_tax
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
        sub_order.save(update_fields=['status', 'payment_rejected', 'updated_at'])

        # Encolar creación de draft en Odoo ahora que el cliente subió su comprobante.
        # on_commit garantiza que la SubOrder ya está guardada antes de que la tarea corra.
        # La tarea es idempotente: si ya tiene odoo_sale_id, la omite silenciosamente.
        sub_order_id_for_celery = sub_order.id
        transaction.on_commit(
            lambda sid=sub_order_id_for_celery: _enqueue_create_odoo(sid)
        )

        return Response({
            'message': 'Comprobante subido correctamente',
            'payment_proof': PaymentProofSerializer(payment_proof).data
        }, status=status.HTTP_201_CREATED)


def _enqueue_create_odoo(sub_order_id):
    """
    Encola la tarea Celery create_odoo_sale_order después del commit de la transacción.
    Se llama desde upload_payment_proof (pago_en_revision) y opcionalmente desde
    confirm_payment para sincronizar el estado de pago actualizado.
    La tarea es idempotente: omite silenciosamente si odoo_sale_id ya existe.
    """
    try:
        from .tasks import create_odoo_sale_order
        create_odoo_sale_order.delay(sub_order_id)
        logger.info(f"📬 Tarea Celery encolada → Odoo para SubOrder {sub_order_id}")
    except Exception as e:
        logger.warning(f"⚠️  No se pudo encolar tarea Odoo para SubOrder {sub_order_id}: {e}")


class SubOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para sub-órdenes (solo lectura para clientes)
    """
    serializer_class = SubOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar sub-órdenes según el usuario"""
        user = self.request.user
        
        # Si es customer
        if hasattr(user, 'customer_profile'):
            return SubOrder.objects.filter(order__customer=user.customer_profile)
        
        # Si es vendor (provider owner)
        if hasattr(user, 'owned_providers'):
            provider_ids = user.owned_providers.values_list('id', flat=True)
            return SubOrder.objects.filter(provider_id__in=provider_ids)
        
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

            sub_order.status = 'pagado'
            sub_order.confirmed_at = timezone.now()
            sub_order.payment_rejected = False

            # Nota: el draft en Odoo ya fue encolado en upload_payment_proof cuando el
            # cliente subió el comprobante (pago_en_revision). La tarea es idempotente,
            # pero podemos volver a encolarla aquí para sincronizar el estado de pago
            # actualizado (x_payment_status) una vez el proveedor confirma.
            sub_order_id = sub_order.id
            transaction.on_commit(
                lambda sid=sub_order_id: _enqueue_create_odoo(sid)
            )

            message = 'Pago confirmado correctamente'
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

            sub_order.status = 'pendiente_pago'
            sub_order.payment_rejected = True
            message = 'Pago rechazado'

        sub_order.save()

        return Response({
            'message': message,
            'sub_order': SubOrderSerializer(sub_order).data
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
        """Estadísticas de órdenes del vendor"""
        queryset = self.get_queryset()
        
        stats = {
            'total_orders':          queryset.count(),
            'pendiente_pago':        queryset.filter(status='pendiente_pago').count(),
            'pago_en_revision':      queryset.filter(status='pago_en_revision').count(),
            'pagado':                queryset.filter(status='pagado').count(),
            'confirmado':            queryset.filter(status='confirmado').count(),
            'enviado':               queryset.filter(status='enviado').count(),
            'entregado':             queryset.filter(status='entregado').count(),
            'cancelado':             queryset.filter(status='cancelado').count(),
            # Flags
            'con_rechazo_previo':    queryset.filter(payment_rejected=True).count(),
            'error_odoo':            queryset.filter(odoo_sync_error=True).count(),
        }
        
        return Response(stats)



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
            "invoice_status": "invoiced",
            "delivery_status": "full"
        }
        """
        from django.conf import settings
        import logging
        
        logger = logging.getLogger(__name__)
        
        # 1. Validar token de seguridad
        token = request.data.get('token')
        expected_token = getattr(settings, 'ODOO_WEBHOOK_TOKEN', 'change-me-in-production')
        
        if token != expected_token:
            logger.warning(f"❌ Webhook recibido con token inválido")
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
        
        # 4. Mapear estado de Odoo a Django
        estado_anterior = sub_order.status
        
        status_mapping = {
            'draft': 'pendiente_pago',
            'sent': 'pendiente_pago',
            'sale': 'pagado_confirmado',  # Orden confirmada en Odoo
            'done': 'entregado',
            'cancel': 'cancelado',
        }
        
        nuevo_estado = status_mapping.get(odoo_state, sub_order.status)
        
        # 5. Actualizar SubOrder
        sub_order.status = nuevo_estado
        sub_order.save()
        
        
        # Actualizar estado de la Order principal
        sub_order.order.update_status_from_suborders()
        logger.info(
            f"✅ SubOrder {sub_order.sub_order_number} actualizada: "
            f"{estado_anterior} → {nuevo_estado}"
        )
        
        # 6. Notificar al cliente (opcional - implementar después)
        # if nuevo_estado in ['pagado_confirmado', 'enviado', 'entregado']:
        #     from .tasks import send_order_status_email
        #     send_order_status_email.delay(sub_order.id)
        
        return Response({
            'success': True,
            'sub_order_number': sub_order.sub_order_number,
            'estado_anterior': estado_anterior,
            'nuevo_estado': nuevo_estado,
            'message': f'SubOrder actualizada correctamente'
        })
