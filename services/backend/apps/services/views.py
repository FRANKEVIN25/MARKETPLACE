"""Views públicas para servicios de taller."""
from django.db.models import (
    Count,
    DecimalField,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce
from rest_framework import filters, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Service,
    ServiceCategory,
    Workshop,
    WorkshopLocation,
    WorkshopService,
    WorkshopServiceHistory,
    WorkshopVehicleExpertise,
)
from .serializers import (
    ServiceCategorySerializer,
    ServiceListingSerializer,
    ServicePublicDetailSerializer,
    WorkshopPublicDetailSerializer,
)


def _parse_bool_param(value):
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if normalized in {'true', '1', 'yes', 'si', 'sí'}:
        return True
    if normalized in {'false', '0', 'no'}:
        return False
    return None


def _vehicle_expertise_prefetch():
    return Prefetch(
        'workshop__vehicle_expertise',
        queryset=WorkshopVehicleExpertise.objects.select_related(
            'marca',
            'modelo__marca',
        ).order_by('-total_jobs', '-created_at'),
        to_attr='prefetched_vehicle_expertise',
    )


def _workshop_locations_prefetch():
    """Prefetch de ubicaciones del taller ordenadas: principal primero."""
    return Prefetch(
        'workshop__locations',
        queryset=WorkshopLocation.objects.order_by('-is_main', 'id'),
        to_attr='prefetched_locations',
    )


def _listing_queryset():
    history_qs = WorkshopServiceHistory.objects.filter(
        workshop_id=OuterRef('workshop_id'),
        service_id=OuterRef('service_id'),
    )

    return (
        WorkshopService.objects.filter(available=True, workshop__is_active=True)
        .select_related('service__category', 'workshop')
        .prefetch_related(
            _vehicle_expertise_prefetch(),
            _workshop_locations_prefetch(),
        )
        .annotate(
            history_total_demand=Coalesce(
                Subquery(history_qs.values('total_demand')[:1], output_field=IntegerField()),
                Value(0),
            ),
            history_avg_rating=Coalesce(
                Subquery(
                    history_qs.values('avg_rating')[:1],
                    output_field=DecimalField(max_digits=3, decimal_places=2),
                ),
                Value(0, output_field=DecimalField(max_digits=3, decimal_places=2)),
            ),
        )
    )


class PublicServiceCategoryListView(generics.ListAPIView):
    """Lista pública de categorías de servicio."""

    permission_classes = []
    authentication_classes = []
    serializer_class = ServiceCategorySerializer

    def get_queryset(self):
        return ServiceCategory.objects.annotate(
            services_count=Count('services', distinct=True),
            # Talleres que ofrecen al menos un servicio de esta categoría
            workshops_count=Count('services__workshopservice__workshop', distinct=True),
        ).order_by('order', 'name')


class PublicServiceListingListView(generics.ListAPIView):
    """Listado público de servicios publicados por talleres."""

    permission_classes = []
    authentication_classes = []
    serializer_class = ServiceListingSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = [
        'service__name',
        'workshop__name',
        'min_price',
        'max_price',
        'estimated_time_min',
        'history_total_demand',
        'history_avg_rating',
        'workshop__years_experience',
    ]
    ordering = ['-history_total_demand', '-history_avg_rating', 'service__name']

    def get_queryset(self):
        qs = _listing_queryset()
        params = self.request.query_params

        q = params.get('q') or params.get('search')
        category_id = params.get('category_id')
        category_name = params.get('category')
        service_type = params.get('service_type') or params.get('type')
        district = params.get('district')
        province = params.get('province')
        department = params.get('department')
        workshop_id = params.get('workshop_id')
        service_id = params.get('service_id')
        marca_id = params.get('marca_id')
        modelo_id = params.get('modelo_id')

        verified_only = _parse_bool_param(params.get('verified_only') or params.get('verified'))
        specialized_only = _parse_bool_param(params.get('specialized_only') or params.get('specialized'))
        erp_only = _parse_bool_param(params.get('erp_only') or params.get('erp_integrated'))

        if q:
            qs = qs.filter(
                Q(service__name__icontains=q)
                | Q(service__description__icontains=q)
                | Q(service__category__name__icontains=q)
                | Q(workshop__name__icontains=q)
                | Q(workshop__description__icontains=q)
                | Q(workshop__locations__district__icontains=q)
            )

        if category_id:
            qs = qs.filter(service__category_id=category_id)
        elif category_name:
            qs = qs.filter(service__category__name__iexact=category_name)

        if service_type:
            qs = qs.filter(service__service_type=service_type)

        if district:
            qs = qs.filter(workshop__locations__district__iexact=district)

        if province:
            qs = qs.filter(workshop__locations__province__iexact=province)

        if department:
            qs = qs.filter(workshop__locations__department__iexact=department)

        if workshop_id:
            qs = qs.filter(workshop_id=workshop_id)

        if service_id:
            qs = qs.filter(service_id=service_id)

        if verified_only is True:
            qs = qs.filter(workshop__is_verified=True)

        if specialized_only is True:
            qs = qs.filter(is_specialized=True)

        if erp_only is True:
            qs = qs.filter(workshop__service_level__in=['MANAGED', 'ADVANCED'])

        if marca_id:
            qs = qs.filter(
                Q(workshop__vehicle_expertise__marca_id=marca_id)
                | Q(workshop__vehicle_expertise__modelo__marca_id=marca_id)
            )

        if modelo_id:
            qs = qs.filter(workshop__vehicle_expertise__modelo_id=modelo_id)

        return qs.distinct()


class PublicServiceDetailView(generics.RetrieveAPIView):
    """Detalle público de un servicio con talleres que lo ofrecen."""

    permission_classes = []
    authentication_classes = []
    serializer_class = ServicePublicDetailSerializer

    def get_queryset(self):
        service_listings = _listing_queryset().order_by(
            '-history_total_demand',
            '-history_avg_rating',
            'min_price',
        )
        return Service.objects.select_related('category').prefetch_related(
            Prefetch('workshopservice_set', queryset=service_listings, to_attr='public_listings')
        )


class PublicWorkshopLocationOptionsView(APIView):
    """
    Retorna listas de opciones para los filtros de ubicación del wizard.

    GET /api/v1/services/locations/
      → { departments: [...], provinces: [...], districts: [...] }

    GET /api/v1/services/locations/?department=Lima
      → provinces y districts filtrados por Lima

    GET /api/v1/services/locations/?department=Lima&province=Lima
      → districts filtrados por Lima + Lima
    """

    permission_classes = []
    authentication_classes = []

    def get(self, request):
        dept_param = request.query_params.get('department', '').strip()
        province_param = request.query_params.get('province', '').strip()

        base_qs = WorkshopLocation.objects.filter(workshop__is_active=True)

        departments = sorted(
            base_qs.values_list('department', flat=True).distinct()
        )

        province_qs = base_qs.filter(department__iexact=dept_param) if dept_param else base_qs
        provinces = sorted(province_qs.values_list('province', flat=True).distinct())

        if dept_param and province_param:
            district_qs = base_qs.filter(
                department__iexact=dept_param,
                province__iexact=province_param,
            )
        elif dept_param:
            district_qs = base_qs.filter(department__iexact=dept_param)
        else:
            district_qs = base_qs
        districts = sorted(district_qs.values_list('district', flat=True).distinct())

        return Response({
            'departments': departments,
            'provinces': provinces,
            'districts': districts,
        })


class PublicWorkshopDetailView(generics.RetrieveAPIView):
    """Detalle público de un taller con catálogo visible."""

    permission_classes = []
    authentication_classes = []
    serializer_class = WorkshopPublicDetailSerializer

    def get_queryset(self):
        workshop_services = _listing_queryset().order_by(
            '-history_total_demand',
            '-history_avg_rating',
            'service__name',
        )

        return Workshop.objects.filter(is_active=True).prefetch_related(
            Prefetch(
                'vehicle_expertise',
                queryset=WorkshopVehicleExpertise.objects.select_related(
                    'marca',
                    'modelo__marca',
                ).order_by('-total_jobs', '-created_at'),
                to_attr='prefetched_vehicle_expertise',
            ),
            Prefetch(
                'locations',
                queryset=WorkshopLocation.objects.order_by('-is_main', 'id'),
                to_attr='prefetched_locations',
            ),
            Prefetch('workshop_services', queryset=workshop_services, to_attr='public_services'),
        )
