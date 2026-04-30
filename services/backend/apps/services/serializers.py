"""
Serializers públicos para servicios de taller.
"""
from decimal import Decimal

from rest_framework import serializers
from django.utils.text import slugify

from .models import (
    ServiceCategory,
    Service,
    Workshop,
    WorkshopLocation,
    WorkshopSchedule,
    WorkshopService,
    WorkshopVehicleExpertise,
)


def _vehicle_label(item) -> str | None:
    """Retorna el label legible de un WorkshopVehicleExpertise."""
    if item.modelo_id:
        return str(item.modelo)
    if item.marca_id:
        return item.marca.nombre
    return None


class ServiceCategorySerializer(serializers.ModelSerializer):
    services_count = serializers.IntegerField(read_only=True)
    workshops_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ServiceCategory
        fields = [
            'id',
            'name',
            'description',
            'icon',
            'order',
            'services_count',
            'workshops_count',
        ]
        read_only_fields = fields


class WorkshopLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopLocation
        fields = [
            'id',
            'name',
            'address',
            'district',
            'province',
            'department',
            'latitude',
            'longitude',
            'is_main',
        ]
        read_only_fields = fields


class WorkshopScheduleSerializer(serializers.ModelSerializer):
    day_label = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = WorkshopSchedule
        fields = [
            'id',
            'day_of_week',
            'day_label',
            'start_time',
            'end_time',
            'is_active',
        ]
        read_only_fields = fields


class WorkshopLocationWriteSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=6,
        required=False,
        default=Decimal('0.000000'),
    )
    longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=6,
        required=False,
        default=Decimal('0.000000'),
    )

    class Meta:
        model = WorkshopLocation
        fields = [
            'id',
            'name',
            'address',
            'district',
            'province',
            'department',
            'latitude',
            'longitude',
            'is_main',
        ]
        read_only_fields = ['id']


class WorkshopScheduleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopSchedule
        fields = [
            'id',
            'day_of_week',
            'start_time',
            'end_time',
            'is_active',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                'La hora de cierre debe ser mayor que la hora de apertura.'
            )

        return attrs


class WorkshopProfileSerializer(serializers.ModelSerializer):
    locations = WorkshopLocationWriteSerializer(many=True, required=False)
    schedules = WorkshopScheduleWriteSerializer(many=True, required=False)

    class Meta:
        model = Workshop
        fields = [
            'id',
            'name',
            'phone',
            'whatsapp',
            'website',
            'description',
            'large_description',
            'years_experience',
            'status',
            'locations',
            'schedules',
        ]

    def validate_locations(self, value):
        if not value:
            return value

        main_count = sum(1 for item in value if item.get('is_main'))
        if main_count != 1:
            raise serializers.ValidationError(
                'Debes marcar exactamente una ubicación principal.'
            )

        return value

    def validate_schedules(self, value):
        seen_slots = set()

        for item in value:
            slot_key = (item['day_of_week'], item['start_time'])
            if slot_key in seen_slots:
                raise serializers.ValidationError(
                    'No puedes repetir el mismo horario de inicio para un día.'
                )
            seen_slots.add(slot_key)

        return value

    def update(self, instance, validated_data):
        locations_data = validated_data.pop('locations', None)
        schedules_data = validated_data.pop('schedules', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.clean()
        instance.save()

        if locations_data is not None:
            self._replace_locations(instance, locations_data)

        if schedules_data is not None:
            self._replace_schedules(instance, schedules_data)

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['locations'] = WorkshopLocationSerializer(
            instance.locations.order_by('-is_main', 'id'),
            many=True,
        ).data
        data['schedules'] = WorkshopScheduleSerializer(
            instance.schedules.order_by('day_of_week', 'start_time'),
            many=True,
        ).data
        return data

    def _replace_locations(self, instance, locations_data):
        instance.locations.all().delete()
        WorkshopLocation.objects.bulk_create([
            WorkshopLocation(
                workshop=instance,
                name=item.get('name', ''),
                address=item['address'],
                district=item['district'],
                province=item['province'],
                department=item['department'],
                latitude=item.get('latitude', Decimal('0.000000')),
                longitude=item.get('longitude', Decimal('0.000000')),
                is_main=item.get('is_main', False),
            )
            for item in locations_data
        ])

    def _replace_schedules(self, instance, schedules_data):
        instance.schedules.all().delete()
        WorkshopSchedule.objects.bulk_create([
            WorkshopSchedule(
                workshop=instance,
                day_of_week=item['day_of_week'],
                start_time=item['start_time'],
                end_time=item['end_time'],
                is_active=item.get('is_active', True),
            )
            for item in schedules_data
        ])


class ServiceCatalogOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'id',
            'name',
            'description',
            'service_type',
            'complexity',
        ]
        read_only_fields = fields


class ServiceCategoryCatalogSerializer(serializers.ModelSerializer):
    services = ServiceCatalogOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceCategory
        fields = [
            'id',
            'name',
            'description',
            'icon',
            'order',
            'services',
        ]
        read_only_fields = fields


class WorkshopServiceConfigSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)
    category_id = serializers.IntegerField(source='service.category_id', read_only=True)
    category_name = serializers.CharField(source='service.category.name', read_only=True)
    service_type = serializers.CharField(source='service.service_type', read_only=True)
    complexity = serializers.CharField(source='service.complexity', read_only=True)

    class Meta:
        model = WorkshopService
        fields = [
            'id',
            'service',
            'service_name',
            'category_id',
            'category_name',
            'service_type',
            'complexity',
            'is_specialized',
            'min_price',
            'max_price',
            'currency',
            'estimated_time_min',
            'available',
            'has_warranty',
            'warranty_days',
        ]
        read_only_fields = [
            'id',
            'service_name',
            'category_id',
            'category_name',
            'service_type',
            'complexity',
        ]

    def validate(self, attrs):
        min_price = attrs.get('min_price')
        max_price = attrs.get('max_price')
        has_warranty = attrs.get('has_warranty', False)
        warranty_days = attrs.get('warranty_days', 0)

        if min_price is not None and max_price is not None and max_price < min_price:
            raise serializers.ValidationError(
                'El precio máximo debe ser mayor o igual al precio mínimo.'
            )

        if not has_warranty:
            attrs['warranty_days'] = 0

        if warranty_days < 0:
            raise serializers.ValidationError(
                'Los días de garantía no pueden ser negativos.'
            )

        return attrs


class WorkshopVehicleExpertiseConfigSerializer(serializers.ModelSerializer):
    granularity = serializers.CharField(read_only=True)
    label = serializers.SerializerMethodField()
    marca_nombre = serializers.SerializerMethodField()
    modelo_nombre = serializers.SerializerMethodField()

    class Meta:
        model = WorkshopVehicleExpertise
        fields = [
            'id',
            'marca',
            'marca_nombre',
            'modelo',
            'modelo_nombre',
            'granularity',
            'label',
            'expertise_level',
            'notes',
            'total_jobs',
            'last_job_date',
        ]
        read_only_fields = [
            'id',
            'marca_nombre',
            'modelo_nombre',
            'granularity',
            'label',
            'total_jobs',
            'last_job_date',
        ]

    def get_label(self, obj):
        return _vehicle_label(obj)

    def get_marca_nombre(self, obj):
        if obj.modelo_id:
            return obj.modelo.marca.nombre
        if obj.marca_id:
            return obj.marca.nombre
        return None

    def get_modelo_nombre(self, obj):
        if obj.modelo_id:
            return obj.modelo.nombre
        return None

    def validate(self, attrs):
        marca = attrs.get('marca')
        modelo = attrs.get('modelo')

        if bool(marca) == bool(modelo):
            raise serializers.ValidationError(
                'Debes elegir exactamente una marca o un modelo.'
            )

        return attrs


class WorkshopCatalogSerializer(serializers.Serializer):
    categories = ServiceCategoryCatalogSerializer(many=True, read_only=True)
    workshop_services = WorkshopServiceConfigSerializer(many=True, read_only=True)
    vehicle_expertise = WorkshopVehicleExpertiseConfigSerializer(many=True, read_only=True)


class WorkshopCatalogUpdateSerializer(serializers.Serializer):
    workshop_services = WorkshopServiceConfigSerializer(many=True, required=False)
    vehicle_expertise = WorkshopVehicleExpertiseConfigSerializer(many=True, required=False)

    def validate_workshop_services(self, value):
        service_ids = [item['service'].id for item in value]
        if len(service_ids) != len(set(service_ids)):
            raise serializers.ValidationError(
                'No puedes repetir el mismo servicio en el catálogo del taller.'
            )
        return value

    def validate_vehicle_expertise(self, value):
        keys = []
        for item in value:
            if item.get('modelo'):
                keys.append(('modelo', item['modelo'].id))
            elif item.get('marca'):
                keys.append(('marca', item['marca'].id))

        if len(keys) != len(set(keys)):
            raise serializers.ValidationError(
                'No puedes repetir la misma marca o modelo en expertise vehicular.'
            )
        return value


class ServiceListingSerializer(serializers.ModelSerializer):
    serviceSlug = serializers.SerializerMethodField()
    serviceName = serializers.CharField(source='service.name', read_only=True)
    category = serializers.CharField(source='service.category.name', read_only=True)
    serviceType = serializers.CharField(source='service.service_type', read_only=True)
    workshopId = serializers.IntegerField(source='workshop.id', read_only=True)
    workshopSlug = serializers.SerializerMethodField()
    workshopName = serializers.CharField(source='workshop.name', read_only=True)
    workshopHeadline = serializers.SerializerMethodField()
    mainLocation = serializers.SerializerMethodField()
    priceMin = serializers.SerializerMethodField()
    priceMax = serializers.SerializerMethodField()
    durationMin = serializers.IntegerField(source='estimated_time_min', read_only=True)
    verified = serializers.BooleanField(source='workshop.is_verified', read_only=True)
    specialized = serializers.BooleanField(source='is_specialized', read_only=True)
    erpIntegrated = serializers.BooleanField(source='workshop.has_erp_integration', read_only=True)
    certified = serializers.SerializerMethodField()
    totalDemand = serializers.IntegerField(source='history_total_demand', read_only=True)
    avgRating = serializers.SerializerMethodField()
    yearsExperience = serializers.IntegerField(source='workshop.years_experience', read_only=True)
    serviceLevel = serializers.CharField(source='workshop.service_level', read_only=True)
    commerceLevel = serializers.CharField(source='workshop.commerce_level', read_only=True)
    vehicleExpertise = serializers.SerializerMethodField()
    trustNotes = serializers.SerializerMethodField()
    workshopScore = serializers.DecimalField(
        source='workshop.score', max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = WorkshopService
        fields = [
            'id',
            'serviceSlug',
            'serviceName',
            'category',
            'serviceType',
            'workshopId',
            'workshopSlug',
            'workshopName',
            'workshopHeadline',
            'mainLocation',
            'priceMin',
            'priceMax',
            'durationMin',
            'verified',
            'specialized',
            'erpIntegrated',
            'certified',
            'totalDemand',
            'avgRating',
            'yearsExperience',
            'serviceLevel',
            'commerceLevel',
            'vehicleExpertise',
            'trustNotes',
            'workshopScore',
        ]
        read_only_fields = fields

    def get_serviceSlug(self, obj):
        return slugify(obj.service.name)

    def get_workshopSlug(self, obj):
        return slugify(obj.workshop.name)

    def get_workshopHeadline(self, obj):
        if obj.workshop.description:
            return obj.workshop.description
        return 'Taller con catálogo publicado en ECOMPARTS.'

    def get_mainLocation(self, obj):
        locations = getattr(obj.workshop, 'prefetched_locations', None)
        if locations:
            return WorkshopLocationSerializer(locations[0]).data
        return None

    def get_priceMin(self, obj):
        return float(obj.min_price) if obj.min_price is not None else None

    def get_priceMax(self, obj):
        return float(obj.max_price) if obj.max_price is not None else None

    def get_certified(self, obj):
        return bool(obj.workshop.certifications)

    def get_avgRating(self, obj):
        value = getattr(obj, 'history_avg_rating', None)
        return float(value) if value is not None else 0.0

    def get_vehicleExpertise(self, obj):
        expertise = getattr(obj.workshop, 'prefetched_vehicle_expertise', None)
        if expertise is None:
            expertise = obj.workshop.vehicle_expertise.select_related(
                'marca', 'modelo__marca',
            ).all()

        labels = []
        for item in expertise:
            label = _vehicle_label(item)
            if label and label not in labels:
                labels.append(label)
            if len(labels) == 5:
                break
        return labels

    def get_trustNotes(self, obj):
        notes = []
        expertise = getattr(obj.workshop, 'prefetched_vehicle_expertise', None)
        if expertise:
            top = next((item for item in expertise if item.total_jobs), None)
            if top:
                label = _vehicle_label(top)
                if label:
                    notes.append(f"{top.total_jobs} trabajos en {label}")

        if obj.has_warranty:
            notes.append(
                f"Garantía {obj.warranty_days} días"
                if obj.warranty_days
                else 'Garantía estructurada'
            )

        if obj.workshop.has_erp_integration:
            notes.append('ERP integrado')

        if obj.workshop.certifications:
            notes.append('Taller certificado')

        if not notes and getattr(obj, 'history_total_demand', 0):
            notes.append(f"{obj.history_total_demand} solicitudes registradas")

        if not notes:
            notes.append('Catálogo publicado')

        return notes[:3]


class ServicePublicDetailSerializer(serializers.ModelSerializer):
    serviceSlug = serializers.SerializerMethodField()
    serviceName = serializers.CharField(source='name', read_only=True)
    category = serializers.CharField(source='category.name', read_only=True)
    serviceType = serializers.CharField(source='service_type', read_only=True)
    relatedWorkshopsCount = serializers.SerializerMethodField()
    priceMin = serializers.SerializerMethodField()
    priceMax = serializers.SerializerMethodField()
    durationMin = serializers.SerializerMethodField()
    listings = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id',
            'serviceSlug',
            'serviceName',
            'category',
            'serviceType',
            'complexity',
            'description',
            'relatedWorkshopsCount',
            'priceMin',
            'priceMax',
            'durationMin',
            'listings',
        ]
        read_only_fields = fields

    def get_serviceSlug(self, obj):
        return slugify(obj.name)

    def get_relatedWorkshopsCount(self, obj):
        return len(self._listings(obj))

    def get_priceMin(self, obj):
        values = [ls.min_price for ls in self._listings(obj) if ls.min_price is not None]
        return float(min(values)) if values else None

    def get_priceMax(self, obj):
        values = [ls.max_price for ls in self._listings(obj) if ls.max_price is not None]
        return float(max(values)) if values else None

    def get_durationMin(self, obj):
        values = [ls.estimated_time_min for ls in self._listings(obj) if ls.estimated_time_min is not None]
        return min(values) if values else None

    def get_listings(self, obj):
        return ServiceListingSerializer(self._listings(obj), many=True, context=self.context).data

    def _listings(self, obj):
        return list(getattr(obj, 'public_listings', []))


class WorkshopPublicDetailSerializer(serializers.ModelSerializer):
    workshopSlug = serializers.SerializerMethodField()
    workshopName = serializers.CharField(source='name', read_only=True)
    workshopHeadline = serializers.SerializerMethodField()
    verified = serializers.BooleanField(source='is_verified', read_only=True)
    erpIntegrated = serializers.BooleanField(source='has_erp_integration', read_only=True)
    certified = serializers.SerializerMethodField()
    yearsExperience = serializers.IntegerField(source='years_experience', read_only=True)
    serviceLevel = serializers.CharField(source='service_level', read_only=True)
    commerceLevel = serializers.CharField(source='commerce_level', read_only=True)
    specialties = serializers.SerializerMethodField()
    vehicleExpertise = serializers.SerializerMethodField()
    totalDemand = serializers.SerializerMethodField()
    avgRating = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()

    class Meta:
        model = Workshop
        fields = [
            'id',
            'workshopSlug',
            'workshopName',
            'workshopHeadline',
            'phone',
            'whatsapp',
            'website',
            'verified',
            'erpIntegrated',
            'certified',
            'yearsExperience',
            'serviceLevel',
            'commerceLevel',
            'specialties',
            'vehicleExpertise',
            'totalDemand',
            'avgRating',
            'services',
            'locations',
        ]
        read_only_fields = fields

    def get_workshopSlug(self, obj):
        return slugify(obj.name)

    def get_workshopHeadline(self, obj):
        if obj.description:
            return obj.description
        specialties = self.get_specialties(obj)
        if specialties:
            return f"Especialistas en {', '.join(specialties[:3])}."
        return 'Taller con catálogo publicado en ECOMPARTS.'

    def get_certified(self, obj):
        return bool(obj.certifications)

    def get_specialties(self, obj):
        """Deriva las categorías únicas de los servicios publicados del taller."""
        seen: set = set()
        names: list = []
        for ws in self._services(obj):
            cat_name = ws.service.category.name
            if cat_name not in seen:
                seen.add(cat_name)
                names.append(cat_name)
        return names

    def get_vehicleExpertise(self, obj):
        expertise = getattr(obj, 'prefetched_vehicle_expertise', None)
        if expertise is None:
            expertise = obj.vehicle_expertise.select_related('marca', 'modelo__marca').all()

        labels = []
        for item in expertise:
            label = _vehicle_label(item)
            if label and label not in labels:
                labels.append(label)
            if len(labels) == 8:
                break
        return labels

    def get_totalDemand(self, obj):
        return sum(getattr(s, 'history_total_demand', 0) for s in self._services(obj))

    def get_avgRating(self, obj):
        ratings = [
            float(s.history_avg_rating)
            for s in self._services(obj)
            if getattr(s, 'history_avg_rating', None)
        ]
        return round(sum(ratings) / len(ratings), 2) if ratings else 0.0

    def get_services(self, obj):
        return ServiceListingSerializer(self._services(obj), many=True, context=self.context).data

    def get_locations(self, obj):
        locations = getattr(obj, 'prefetched_locations', None)
        if locations is None:
            locations = list(obj.locations.all())
        return WorkshopLocationSerializer(locations, many=True).data

    def _services(self, obj):
        return list(getattr(obj, 'public_services', []))
