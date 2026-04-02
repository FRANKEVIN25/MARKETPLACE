"""
Serializers públicos para servicios de taller.
"""
from rest_framework import serializers
from django.utils.text import slugify

from .models import ServiceCategory, Service, Workshop, WorkshopService, WorkshopLocation


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
