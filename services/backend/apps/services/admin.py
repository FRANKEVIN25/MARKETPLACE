from django.contrib import admin
from .models import (
    Workshop, ServiceCategory, Service,
    WorkshopService, WorkshopServiceHistory, WorkshopSchedule,
    WorkshopVehicleExpertise, WorkshopLocation, WorkshopReview,
)


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'ruc', 'service_level', 'commerce_level', 'status',
        'is_verified', 'is_active', 'created_at',
    )
    list_filter = ('service_level', 'commerce_level', 'status', 'is_verified', 'is_active')
    search_fields = ('name', 'ruc', 'owner__username', 'customer_profile__company_name', 'customer_profile__document_number')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('owner', 'customer_profile', 'provider')
    fieldsets = (
        ('Identificación', {
            'fields': ('owner', 'customer_profile', 'name', 'ruc', 'service_level', 'commerce_level', 'provider'),
        }),
        ('Sincronización Odoo', {
            'fields': ('odoo_partner_id', 'odoo_repair_id'),
            'classes': ('collapse',),
        }),
        ('Perfil', {
            'fields': ('description', 'large_description', 'years_experience', 'certifications', 'bays', 'employees', 'max_fleet_size'),
        }),
        ('Contacto', {
            'fields': ('phone', 'whatsapp', 'website'),
        }),
        ('Estado', {
            'fields': ('status', 'is_verified', 'is_active'),
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'order')
    ordering = ('order', 'name')
    search_fields = ('name',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'service_type', 'complexity')
    list_filter = ('category', 'service_type', 'complexity')
    search_fields = ('name',)


@admin.register(WorkshopService)
class WorkshopServiceAdmin(admin.ModelAdmin):
    list_display = (
        'workshop', 'service', 'is_specialized',
        'min_price', 'max_price', 'currency',
        'estimated_time_min', 'has_warranty', 'warranty_days', 'available',
    )
    list_filter = ('is_specialized', 'available', 'has_warranty', 'service__category')
    search_fields = ('workshop__name', 'service__name')
    raw_id_fields = ('workshop',)


@admin.register(WorkshopServiceHistory)
class WorkshopServiceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'workshop', 'service', 'total_demand',
        'total_ratings', 'avg_rating', 'last_jobs_date',
    )
    search_fields = ('workshop__name', 'service__name')
    raw_id_fields = ('workshop',)


@admin.register(WorkshopSchedule)
class WorkshopScheduleAdmin(admin.ModelAdmin):
    list_display = ('workshop', 'day_of_week', 'start_time', 'end_time', 'is_active')
    list_filter = ('day_of_week', 'is_active')
    search_fields = ('workshop__name',)
    raw_id_fields = ('workshop',)


@admin.register(WorkshopVehicleExpertise)
class WorkshopVehicleExpertiseAdmin(admin.ModelAdmin):
    list_display = (
        'workshop', 'granularity_display', 'vehicle_display',
        'expertise_level', 'total_jobs', 'last_job_date', 'created_at',
    )
    list_filter = ('expertise_level',)
    search_fields = (
        'workshop__name',
        'marca__nombre',
        'modelo__nombre',
    )
    raw_id_fields = ('workshop', 'marca', 'modelo')
    readonly_fields = ('created_at',)

    @admin.display(description='Nivel')
    def granularity_display(self, obj):
        icons = {'marca': '🏢', 'modelo': '🚗'}
        return f"{icons.get(obj.granularity, '')} {obj.granularity.capitalize()}"

    @admin.display(description='Vehículo')
    def vehicle_display(self, obj):
        if obj.modelo_id:
            return str(obj.modelo)
        return str(obj.marca)


@admin.register(WorkshopLocation)
class WorkshopLocationAdmin(admin.ModelAdmin):
    list_display = ('workshop', 'name', 'district', 'province', 'department', 'is_main')
    list_filter = ('is_main', 'department')
    search_fields = ('workshop__name', 'address', 'district')
    raw_id_fields = ('workshop',)


@admin.register(WorkshopReview)
class WorkshopReviewAdmin(admin.ModelAdmin):
    list_display = ('workshop', 'user', 'service', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('workshop__name', 'user__company_name', 'comment')
    raw_id_fields = ('workshop', 'user', 'service')
    readonly_fields = ('created_at',)
