from django.db import models
from django.db.models import Q, F
from django.contrib.auth.models import User

"""
App: services
Valor real: no se trata de listar talleres, sino de reducir el riesgo del cliente
final mediante verificación, historial real y un ecosistema cerrado donde los
talleres actúan como consumidores masivos de autopartes (B2B) y, opcionalmente,
como proveedores de servicios y/o repuestos.

Dos ejes independientes definen la posición de cada taller:

  service_level   → nivel de operación interna (ERP)
    BASIC           sin Odoo (solo frontend)
    MANAGED         Odoo ERP + Repair
    ADVANCED        Odoo ERP + Repair + analítica futura

  commerce_level  → relación con autopartes
    NONE            no compra ni vende (caso extremo)
    BUYER           compra al precio de retail en el marketplace
    B2B_BUYER       compra a precio mayorista vía Odoo
    SELLER          compra B2B + vende en el marketplace

Combinaciones habituales:
    BASIC    + BUYER      → taller pequeño
  MANAGED  + B2B_BUYER  → taller profesional con ERP
  ADVANCED + SELLER     → taller que también comercializa repuestos
"""


class Workshop(models.Model):
    """
    Modelo central de talleres mecánicos.

    La posición del taller en el ecosistema se define por dos ejes ortogonales:

      service_level   → qué tan sofisticada es su operación interna (ERP).
      commerce_level  → cómo interactúa con el inventario de autopartes.

    Separar ambas dimensiones permite combinaciones reales del mercado peruano:
        - Taller pequeño sin ERP que compra en el marketplace (BASIC + BUYER).
      - Taller profesional con ERP solo para gestión interna (MANAGED + B2B_BUYER).
      - Taller empresarial que también vende repuestos (ADVANCED + SELLER).

    El campo `provider` solo se llena cuando commerce_level == 'SELLER'.
    """

    # ── Eje 1: nivel de operación (ERP) ───────────────────────────────────────
    SERVICE_LEVEL_CHOICES = [
        ('BASIC',    'Básico — Sin ERP'),
        ('MANAGED',  'Gestionado — Odoo ERP + Repair'),
        ('ADVANCED', 'Avanzado — Odoo ERP + Repair + ecomp + analitica'),
    ]

    # ── Eje 2: relación con autopartes ────────────────────────────────────────
    COMMERCE_LEVEL_CHOICES = [
        ('NONE',      'Sin relación con repuestos'),
        ('BUYER',     'Comprador retail — precio de marketplace'),
        ('B2B_BUYER', 'Comprador mayorista — precio B2B vía Odoo'),
        ('SELLER',    'Vendedor — vende repuestos en el marketplace'),
    ]

    # ── Propietario ────────────────────────────────────────────────────────────
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='workshops',
    )

    # ── Perfil comprador del taller ──────────────────────────────────────────
    # Reutiliza el historial, descuentos, direcciones y flujo de compras del
    # marketplace. Debe apuntar siempre a Customer(customer_type='company').
    customer_profile = models.OneToOneField(
        'customer.Customer',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='workshop',
        help_text=(
            "Perfil Customer empresa asociado al taller. "
            "Conserva historial y beneficios del marketplace."
        ),
    )

    # ── Puente al ecosistema de proveedores ────────────────────────────────────
    # Solo se llena cuando commerce_level = 'SELLER'.
    # Permite que el mismo negocio venda autopartes en el marketplace.
    provider = models.OneToOneField(
        'marketplace.Provider',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_workshop',
        help_text=(
            "Solo se llena cuando service_level es MANAGED o ADVANCED"
            "Permite adquirir una suscripcion en ODOO con las configuraciones listas para dar de alta."
        ),
    )

    # ── Sincronización Odoo ────────────────────────────────────────────────────
    # Un Partner en Odoo puede tener customer=True y supplier=True simultáneamente.
    odoo_partner_id = models.IntegerField(
        null=True,
        blank=True,
        unique=True,
        help_text="ID del Partner en Odoo (se crea al registrar el taller)",
    )
    odoo_repair_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID del módulo Repair en Odoo (solo para service_level MANAGED / ADVANCED)",
    )

    # ── Identificación ─────────────────────────────────────────────────────────
    name = models.CharField(max_length=255)
    ruc = models.CharField(
        max_length=11,
        unique=True,
        blank=True,
        null=True,
        help_text="RUC del taller (Perú, 11 dígitos)",
    )

    service_level = models.CharField(
        max_length=10,
        choices=SERVICE_LEVEL_CHOICES,
        default='BASIC',
        verbose_name="Nivel de servicio (ERP)",
        help_text="Define qué tan sofisticada es la operación interna del taller.",
    )
    commerce_level = models.CharField(
        max_length=10,
        choices=COMMERCE_LEVEL_CHOICES,
        default='BUYER',
        verbose_name="Nivel comercial (autopartes)",
        help_text="Define la relación del taller con el inventario de autopartes.",
    )

    # ── Capacidad operativa ────────────────────────────────────────────────────
    # Campos necesarios para la futura app de citas y matching por disponibilidad.
    bays = models.PositiveIntegerField(
        default=1,
        help_text="Número de bahías de trabajo disponibles",
    )
    employees = models.PositiveIntegerField(
        default=1,
        help_text="Número de técnicos/mecánicos",
    )
    max_fleet_size = models.PositiveIntegerField(
        default=0,
        help_text="Capacidad máxima de flota atendida (0 = no aplica)",
    )

    # ── Perfil del taller ──────────────────────────────────────────────────────
    description = models.TextField(blank=True, max_length=150, help_text="descripcion corta")
    large_description = models.TextField(blank=True, max_length=300, help_text="descripcion extensa")
    years_experience = models.PositiveIntegerField(default=0)
    certifications = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Lista de certificaciones (ej: ['ASE', 'ISO 9001']). "
            "Nivel 1: RUC + foto local; Nivel 2: certificaciones + inspección; "
            "Nivel 3: integración SUNAT + GPS."
        ),
    )

    STATUS_CHOICES = [
        ('open', 'Abierto'),
        ('busy', 'Saturado'),
        ('closed', 'Cerrado'),
    ]

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='open'
    )

    # ── Contacto ───────────────────────────────────────────────────────────────
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    # ── Estado y verificación ──────────────────────────────────────────────────
    is_verified = models.BooleanField(
        default=False,
        help_text="Verificado por el equipo de EcomParts",
    )
    is_active = models.BooleanField(default=True)

    # ── Score de visibilidad ───────────────────────────────────────────────────
    # Valor materializado (0.00–100.00) calculado por la tarea Celery
    # `recalculate_workshop_scores`. Permite ordenar el listado público sin
    # joins en tiempo real. Recalculado cada 12 horas (configurable via CELERY_BEAT).
    #
    # Fórmula (ver apps/services/tasks.py):
    #   40 % historial de compra (CustomerStats.total_spent del customer_profile)
    #   25 % rating promedio de reviews (WorkshopReview)
    #   15 % demanda de servicios (WorkshopServiceHistory.total_demand)
    #   10 % expertise vehicular  (WorkshopVehicleExpertise count + nivel)
    #   10 % confianza            (is_verified + years_experience)
    score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        db_index=True,
        verbose_name="Score de visibilidad",
        help_text="Puntuación 0–100 calculada periódicamente. Mayor score → aparece primero.",
    )

    # ── Auditoría ──────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Taller'
        verbose_name_plural = 'Talleres'
        ordering = ['-created_at']
        constraints = [
            # Un taller SELLER debe tener provider asignado.
            # Cualquier otro commerce_level no debe tenerlo.
            models.CheckConstraint(
                check=(
                    Q(commerce_level='SELLER', provider__isnull=False) |
                    ~Q(commerce_level='SELLER')
                ),
                name='provider_required_if_seller',
            ),
        ]

    def __str__(self):
        return f"{self.name}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.customer_profile_id:
            if self.customer_profile.user_id != self.owner_id:
                raise ValidationError({
                    'customer_profile': (
                        'El customer_profile debe pertenecer al mismo usuario owner del taller.'
                    )
                })
            if self.customer_profile.customer_type != 'company':
                raise ValidationError({
                    'customer_profile': 'El customer_profile del taller debe ser de tipo company.'
                })
            if self.customer_profile.document_type != 'RUC':
                raise ValidationError({
                    'customer_profile': 'El customer_profile del taller debe usar documento RUC.'
                })

    # ── Propiedades de negocio ─────────────────────────────────────────────────

    @property
    def can_sell_parts(self) -> bool:
        """True si el taller puede vender autopartes en el marketplace."""
        return self.commerce_level == 'SELLER'

    @property
    def can_buy_b2b(self) -> bool:
        """True si el taller compra autopartes a precio mayorista vía Odoo."""
        return self.commerce_level in ('B2B_BUYER', 'SELLER')

    @property
    def has_erp_integration(self) -> bool:
        """True si el taller tiene suscripción Odoo activa (MANAGED o ADVANCED)."""
        return self.service_level in ('MANAGED', 'ADVANCED')

    @property
    def is_basic_only(self) -> bool:
        """True si opera sin ERP (sin Odoo)."""
        return self.service_level == 'BASIC'

    @property
    def is_service_only(self) -> bool:
        """True si tiene ERP pero no vende repuestos en el marketplace."""
        return self.service_level in ('MANAGED', 'ADVANCED') and self.commerce_level != 'SELLER'


# ── Categorías de servicio ─────────────────────────────────────────────────────
# Catálogo plano: Motor y Rendimiento | Frenos y Seguridad | Suspensión y Dirección | Diagnóstico …
# Transmisión y Embrague | Sistema de Enfriamiento | Electricidad e Iluminación|
# Aire Acondicionado | Sistema de Escape | Neumáticos y Aros | Mantenimiento | Planchado y pintura
class ServiceCategory(models.Model):
    """
    Categorías de servicio de un solo nivel.

    El dominio de talleres para el MVP no necesita jerarquía padre → hijo.
    Mantener un catálogo plano simplifica el admin, los filtros, la API y el
    seed inicial sin perder valor de negocio.
    """

    name = models.CharField(max_length=100)

    # Aquí viven los problemas que el cliente siente.
    description = models.TextField(blank=True, help_text="Ej: Chirridos, pedal largo o vibración al frenar.")
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Identificador del ícono para la UI (ej: 'fa-wrench')",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Orden de aparición en el frontend (menor = primero)",
    )

    class Meta:
        verbose_name = 'Categoría de Servicio'
        verbose_name_plural = 'Categorías de Servicio'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


# ── Servicios ──────────────────────────────────────────────────────────────────
# Ejemplos: Motor → Afinamiento | Frenos → Cambio de pastillas | Diagnóstico → Escaneo

class Service(models.Model):
    """
    Catálogo maestro de servicios disponibles en la plataforma.

    Los campos `service_type` y `complexity` permiten:
      - Ordenar y filtrar resultados en el frontend.
      - Calcular rangos de precio estimados.
      - Mejorar el matching IA taller↔vehículo.

    FUTURO (bundling con marketplace):
      - linked_product: FK a products.Product para vincular el repuesto
        que se consume en este servicio (ej: pastillas de freno en "Cambio de pastillas").
      - odoo_product_id: ID del producto/servicio en Odoo para facturación automática.

    Cuando se active el bundling, el flujo será:
      WorkshopService → Service → linked_product → marketplace.Product
    """

    SERVICE_TYPE_CHOICES = [
        ('maintenance', 'Mantenimiento'),
        ('repair', 'Reparación'),
        ('diagnostic', 'Diagnóstico'),
    ]

    COMPLEXITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
    ]

    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='services',
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    service_type = models.CharField(
        max_length=20,
        choices=SERVICE_TYPE_CHOICES,
        default='repair',
        verbose_name="Tipo de servicio",
        help_text="Clasificación general: mantenimiento, reparación o diagnóstico.",
    )
    complexity = models.CharField(
        max_length=10,
        choices=COMPLEXITY_CHOICES,
        default='medium',
        verbose_name="Nivel de complejidad",
        help_text="Baja = rutinario (<1h), Media = intermedio, Alta = especializado o motor.",
    )

    # ── FUTURO: bundling con marketplace ──────────────────────────────────────
    # linked_product = models.ForeignKey(
    #     'products.Product',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='linked_services',
    #     help_text="Repuesto del marketplace que se usa en este servicio",
    # )
    # ── FUTURO: sincronización Odoo ───────────────────────────────────────────
    # odoo_product_id = models.IntegerField(
    #     null=True, blank=True,
    #     help_text="ID del producto/servicio en Odoo para facturación",
    # )

    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.category.name} → {self.name}"


# ── Servicios por taller ───────────────────────────────────────────────────────

class WorkshopService(models.Model):
    """
    Tabla intermedia Workshop ↔ Service con datos operativos del taller.
    Es lo que se muestra en el perfil del taller y habilita la app de citas.

    Campos clave:
      - min_price / max_price: rango de precio numérico (el texto lo genera el frontend).
      - estimated_time_min: duración en minutos (más preciso para agenda).
      - has_warranty / warranty_days: evidencia de confianza estructurada.
      - available: si el servicio está disponible actualmente.
      - is_specialized: servicio diferenciador del taller.
    """

    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        related_name='workshop_services',
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    is_specialized = models.BooleanField(
        default=True,
        help_text="Servicio diferenciador / fuerte del taller",
    )

    # ── Precio estructurado ─────────────────
    min_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio mínimo referencial del servicio",
    )
    max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio máximo referencial del servicio",
    )
    currency = models.CharField(
        max_length=10,
        default='PEN',
        help_text="Moneda (ISO 4217). Default: PEN (soles peruanos).",
    )

    # ── Duración en minutos (más preciso para agenda tipo Google Calendar) ────
    estimated_time_min = models.PositiveIntegerField(
        default=60,
        help_text="Tiempo estimado en minutos (ej: 90 = 1h 30min)",
    )

    available = models.BooleanField(
        default=True,
        help_text="Si el servicio está disponible actualmente en este taller",
    )

    # ── Garantía — más persuasiva que cualquier rating ────────────────────────
    has_warranty = models.BooleanField(
        default=False,
        help_text="Si el taller ofrece garantía para este servicio",
    )
    warranty_days = models.PositiveIntegerField(
        default=0,
        help_text="Días de garantía ofrecidos (0 si no aplica)",
    )

    class Meta:
        verbose_name = 'Servicio de Taller'
        verbose_name_plural = 'Servicios de Taller'
        unique_together = ('workshop', 'service')
        constraints = [
            # max_price >= min_price cuando ambos están definidos.
            # Si alguno es null el constraint no aplica (precio aún sin definir).
            models.CheckConstraint(
                check=(
                    Q(min_price__isnull=True) |
                    Q(max_price__isnull=True) |
                    Q(max_price__gte=F('min_price'))
                ),
                name='valid_workshop_service_price_range',
            ),
        ]

    def __str__(self):
        return f"{self.workshop.name} → {self.service.name}"


# ── Historial de servicios ─────────────────────────────────────────────────────

class WorkshopServiceHistory(models.Model):
    """
    Historial agregado de trabajos realizados por taller y tipo de servicio.

    Propósito actual: métricas de reputación visibles en el perfil del taller.
    Propósito futuro: insumo para el motor de recomendaciones (matching IA).

    desde las reseñas y órdenes cerradas (vía signals o tarea Celery).
    El matching inteligente (taller + vehículo + ubicación) es una
    implementación FUTURA (Fase 2).
    """

    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        related_name='service_history',
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # total_jobs = models.PositiveIntegerField(default=0)
    # total de solicitudes de servicio, es una forma mas facil de contabilizar la demanda de los servicios de un taller.
    total_demand = models.PositiveIntegerField(default=0)
    total_ratings = models.PositiveIntegerField(default=0)
    
    # cambiar a un sistema de puntuacion tipo choices, elegir entre: 1,2,3,4,5.
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Calificación promedio del cliente (0.00 - 5.00)",
    )
    last_jobs_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha del última solicitud",
    )

    class Meta:
        verbose_name = 'Historial de Servicio'
        verbose_name_plural = 'Historial de Servicios'
        unique_together = ('workshop', 'service')


# ── Horario semanal del taller ─────────────────────────────────────────────────
# Cimiento para la futura app de citas (slots de disponibilidad real).
# DAY_OF_WEEK sigue la convención de Python/ISO: 0 = lunes, 6 = domingo.

class WorkshopSchedule(models.Model):
    """
    Horario operativo semanal del taller.

    Propósito actual: mostrar horario en el perfil del taller.
    Propósito futuro: generar slots de citas (Fase 2 — matching inteligente).

    Un taller puede tener múltiples registros por día (ej: mañana y tarde).
    La combinación (workshop, day_of_week, start_time) debe ser única.
    """

    DAY_CHOICES = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        related_name='schedules',
    )
    day_of_week = models.IntegerField(
        choices=DAY_CHOICES,
        help_text="0 = lunes, 6 = domingo (ISO / Python weekday)",
    )
    start_time = models.TimeField(help_text="Hora de apertura")
    end_time = models.TimeField(help_text="Hora de cierre")
    is_active = models.BooleanField(
        default=True,
        help_text="Permite deshabilitar días sin eliminarlos (ej: feriados permanentes)",
    )

    class Meta:
        verbose_name = 'Horario de Taller'
        verbose_name_plural = 'Horarios de Taller'
        unique_together = ('workshop', 'day_of_week', 'start_time')
        ordering = ['workshop', 'day_of_week', 'start_time']

    def __str__(self):
        return (
            f"{self.workshop.name} — "
            f"{self.get_day_of_week_display()} "
            f"{self.start_time:%H:%M}–{self.end_time:%H:%M}"
        )


# ── Expertise del taller por vehículo ─────────────────────────────────────────
# Responde la pregunta: "¿En qué vehículos es especialista este taller?"
#
# El modelo maneja dos niveles de granularidad:
#
#   Nivel 1 — Marca  : sabe de Toyota en general
#   Nivel 2 — Modelo : sabe de Toyota Corolla
#
# Solo uno de los dos FK debe estar poblado a la vez (constraint validado en
# clean()). Esto permite crecer sin migrar: un taller empieza declarando marca
# y luego refina por modelo a medida que agrega historial real.
#
# Relación con WorkshopServiceHistory:
#   El historial registra cuántos trabajos hizo el taller por tipo de servicio.
#   Este modelo agrega la dimensión vehicular: cuánto sabe del vehículo.
#   Ambos alimentan el motor de matching (Fase 2).

class WorkshopVehicleExpertise(models.Model):
    """
    Declara el nivel de expertise de un taller para una marca o modelo
    específica de vehículo.

    Solo uno de los dos FK debe estar poblado:
      - marca sola   → "somos buenos con Toyota"
      - modelo solo  → "somos buenos con Toyota Corolla"

    El campo `expertise_level` permite:
      - Ordenar resultados de búsqueda (experto primero).
      - Calcular un score de confianza para el matching IA.
      - Mostrar badges en el perfil del taller.

    Casos de uso inmediatos:
      - Filtro en el marketplace: "talleres que trabajan mi vehículo".
      - Perfil del taller: "Este taller es experto en Toyota Corolla".
      - Matching futuro: taller + vehículo + servicio + ubicación.
    """

    EXPERTISE_CHOICES = [
        ('basic',  'Básico — Experiencia general con el vehículo'),
        ('pro',    'Profesional — Diagnóstico + reparaciones frecuentes'),
        ('expert', 'Experto — Especialista certificado o con historial extenso'),
    ]

    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        related_name='vehicle_expertise',
    )

    # ── Granularidad del expertise ─────────────────────────────────────────────
    # Solo uno debe estar poblado (validado en clean()).
    marca = models.ForeignKey(
        'vehicles.Marca',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='workshop_expertise',
        help_text="Nivel 1: expertise por marca (ej: Toyota)",
    )
    modelo = models.ForeignKey(
        'vehicles.ModeloVehiculo',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='workshop_expertise',
        help_text="Nivel 2: expertise por modelo (ej: Toyota Corolla)",
    )

    expertise_level = models.CharField(
        max_length=10,
        choices=EXPERTISE_CHOICES,
        default='basic',
        verbose_name="Nivel de expertise",
        help_text=(
            "Básico = experiencia general; "
            "Pro = diagnóstico + reparaciones frecuentes; "
            "Experto = especialista certificado o con historial extenso."
        ),
    )

    notes = models.TextField(
        blank=True,
        help_text=(
            "Notas internas sobre la experiencia con este vehículo. "
            "Ej: 'Motor 2ZR-FE: cambiamos 40 cadenas de distribución'."
        ),
    )

    # ── Métricas de actividad ──────────────────────────────────────────────────
    # Responden: "¿Cuántos trabajos ha hecho este taller en este vehículo?"
    # Se actualizan desde órdenes cerradas (vía signal o tarea Celery, Fase 2).
    # No se desagrega por tipo de servicio para evitar una tabla adicional;
    # WorkshopServiceHistory ya cubre el eje servicio, este cubre el eje vehículo.
    total_jobs = models.PositiveIntegerField(
        default=0,
        help_text="Total de trabajos realizados en esta marca/modelo/variante.",
    )
    last_job_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha del último trabajo registrado en este vehículo.",
    )

    # ── Auditoría ──────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Expertise Vehicular del Taller'
        verbose_name_plural = 'Expertise Vehicular de Talleres'
        ordering = ['workshop', '-expertise_level']
        indexes = [
            models.Index(fields=['workshop', 'expertise_level']),
            models.Index(fields=['marca']),
            models.Index(fields=['modelo']),
        ]
        constraints = [
            # Dos constraints condicionales en lugar de unique_together porque
            # PostgreSQL trata NULL != NULL — un unique_together estándar no
            # impide duplicados cuando uno de los FK es NULL.
            models.UniqueConstraint(
                fields=['workshop', 'marca'],
                condition=Q(modelo__isnull=True),
                name='unique_workshop_marca',
            ),
            models.UniqueConstraint(
                fields=['workshop', 'modelo'],
                condition=Q(modelo__isnull=False),
                name='unique_workshop_modelo',
            ),
        ]

    def clean(self):
        """Garantiza que solo uno de los dos FK de vehículo esté poblado."""
        from django.core.exceptions import ValidationError
        filled = sum([
            bool(self.marca_id),
            bool(self.modelo_id),
        ])
        if filled == 0:
            raise ValidationError(
                "Debes especificar al menos marca o modelo."
            )
        if filled > 1:
            raise ValidationError(
                "Solo puedes especificar uno de: marca o modelo. "
                "Usa el nivel más específico disponible."
            )

    def __str__(self):
        vehicle = (
            str(self.modelo) if self.modelo_id else
            str(self.marca)
        )
        return f"{self.workshop.name} → {vehicle} [{self.get_expertise_level_display()}]"

    # ── Propiedades de conveniencia ────────────────────────────────────────────

    @property
    def granularity(self) -> str:
        """Retorna 'modelo' o 'marca' según qué FK está poblado."""
        if self.modelo_id:
            return 'modelo'
        return 'marca'



class WorkshopLocation(models.Model):
    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        related_name='locations'
    )

    name = models.CharField(max_length=150, blank=True)  # "Sucursal Surco"

    address = models.CharField(max_length=255)
    district = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    department = models.CharField(max_length=100)

    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)

    is_main = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ubicación de Taller'
        verbose_name_plural = 'Ubicaciones de Taller'
        indexes = [
            # Cubre búsquedas por department solo, (department, province) y (department, province, district).
            models.Index(fields=['department', 'province', 'district']),
        ]
        constraints = [
            # Solo puede haber una sede principal por taller.
            models.UniqueConstraint(
                fields=['workshop'],
                condition=Q(is_main=True),
                name='unique_main_location_per_workshop',
            ),
        ]


class WorkshopReview(models.Model):
    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    user = models.ForeignKey('customer.Customer', on_delete=models.CASCADE)

    service = models.ForeignKey(  # opcional: permite filtrar reseñas por servicio
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    rating = models.PositiveSmallIntegerField(
            choices=[(i, i) for i in range(1, 6)],
            default=5
        )
    
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reseña de Taller'
        verbose_name_plural = 'Reseñas de Taller'
        constraints = [
            models.UniqueConstraint(
                fields=['workshop', 'user'],
                name='unique_review_per_user_per_workshop',
            ),
        ]