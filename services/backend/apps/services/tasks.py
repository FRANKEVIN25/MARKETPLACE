"""
Tareas Celery para el app services.

Tarea principal:
  recalculate_workshop_scores — recalcula Workshop.score para todos los talleres
  activos y lo persiste en un único UPDATE por taller.

Fórmula de score (0–100):
  40 % historial de compra   → CustomerStats.total_spent del customer_profile
  25 % rating promedio       → promedio de WorkshopReview.rating
  15 % demanda de servicios  → suma de WorkshopServiceHistory.total_demand
  10 % expertise vehicular   → count y nivel de WorkshopVehicleExpertise
  10 % confianza             → is_verified (binario) + years_experience (cap 20 años)

Cada componente se normaliza a un valor en [0, 1] antes de aplicar el peso,
usando caps configurables para evitar que un solo taller con datos extremos
distorsione todo el ranking.
"""
import logging
from decimal import Decimal

from celery import shared_task
from django.db.models import Avg, Sum

logger = logging.getLogger(__name__)

# ── Caps de normalización ──────────────────────────────────────────────────────
# Ajusta estos valores según el perfil real de talleres en producción.
# Un taller que supere el cap obtiene el 100 % en ese componente.
PURCHASE_CAP = Decimal('50000')   # S/ 50,000 de historial de compra total
DEMAND_CAP   = 500                # 500 solicitudes de servicio acumuladas
EXP_CAP      = 20                 # 20 años de experiencia → tope del componente

# Mapa de expertise_level → puntos (se suma y se normaliza sobre el máximo posible)
EXPERTISE_POINTS = {'basic': 1, 'pro': 2, 'expert': 3}
EXPERTISE_MAX_PER_ENTRY = 3       # máximo por entrada individual


def _clamp(value, cap) -> Decimal:
    """Normaliza value al rango [0, 1] usando cap como techo."""
    if cap <= 0:
        return Decimal('0')
    return min(Decimal(str(value)) / Decimal(str(cap)), Decimal('1'))


def _compute_score(workshop) -> Decimal:
    """
    Calcula el score de visibilidad para un taller.
    Devuelve un Decimal en [0.00, 100.00].
    """
    # ── Componente 1: historial de compra (40 %) ──────────────────────────────
    purchase_norm = Decimal('0')
    if workshop.customer_profile_id:
        try:
            total_spent = workshop.customer_profile.stats.total_spent
            purchase_norm = _clamp(total_spent, PURCHASE_CAP)
        except Exception:
            pass

    # ── Componente 2: rating promedio de reviews (25 %) ──────────────────────
    rating_norm = Decimal('0')
    avg = workshop.reviews.aggregate(avg=Avg('rating'))['avg']
    if avg:
        # Rating está en [1, 5]; mapeamos a [0, 1]
        rating_norm = _clamp(avg - 1, 4)   # (avg-1)/4

    # ── Componente 3: demanda de servicios (15 %) ─────────────────────────────
    demand_total = (
        workshop.service_history.aggregate(total=Sum('total_demand'))['total'] or 0
    )
    demand_norm = _clamp(demand_total, DEMAND_CAP)

    # ── Componente 4: expertise vehicular (10 %) ──────────────────────────────
    expertise_norm = Decimal('0')
    expertise_entries = list(workshop.vehicle_expertise.values_list('expertise_level', flat=True))
    if expertise_entries:
        points = sum(EXPERTISE_POINTS.get(lvl, 1) for lvl in expertise_entries)
        # cap: 10 entradas al nivel máximo
        expertise_norm = _clamp(points, 10 * EXPERTISE_MAX_PER_ENTRY)

    # ── Componente 5: confianza (10 %) ────────────────────────────────────────
    verified_part = Decimal('0.5') if workshop.is_verified else Decimal('0')
    exp_part = _clamp(workshop.years_experience, EXP_CAP) * Decimal('0.5')
    trust_norm = verified_part + exp_part   # [0, 1]

    # ── Score final ponderado ─────────────────────────────────────────────────
    score = (
        purchase_norm * Decimal('40') +
        rating_norm   * Decimal('25') +
        demand_norm   * Decimal('15') +
        expertise_norm * Decimal('10') +
        trust_norm    * Decimal('10')
    )
    return score.quantize(Decimal('0.01'))


@shared_task(bind=True, ignore_result=True)
def recalculate_workshop_scores(self):
    """
    Recalcula Workshop.score para todos los talleres activos.

    Estrategia:
      - Carga todos los talleres activos con sus relaciones necesarias en memoria.
      - Calcula el score de cada uno.
      - Hace bulk_update en lotes de 200 para minimizar round-trips a la DB.

    El periodo de ejecución se configura en celery.py (WORKSHOP_SCORE_RECALCULATE_SCHEDULE).
    Por defecto: cada 12 horas.
    """
    from .models import Workshop

    logger.info("⚙️  Iniciando recálculo de scores de talleres...")

    workshops = list(
        Workshop.objects.filter(is_active=True)
        .select_related('customer_profile__stats')
        .prefetch_related('reviews', 'service_history', 'vehicle_expertise')
    )

    updated = 0
    batch = []

    for workshop in workshops:
        new_score = _compute_score(workshop)
        if workshop.score != new_score:
            workshop.score = new_score
            batch.append(workshop)

        if len(batch) >= 200:
            Workshop.objects.bulk_update(batch, ['score'])
            updated += len(batch)
            batch = []

    if batch:
        Workshop.objects.bulk_update(batch, ['score'])
        updated += len(batch)

    logger.info("✅ Scores recalculados: %d talleres actualizados de %d.", updated, len(workshops))
