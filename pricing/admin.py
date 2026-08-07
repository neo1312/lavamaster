from django.contrib import admin

from .models import ServiceCategory, ServiceType


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'emoji', 'sort_order')
    list_editable = ('emoji', 'sort_order')
    search_fields = ('name',)


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'unit', 'min_weight_kg', 'max_weight_kg',
        'rate_per_kg', 'estimated_days', 'active', 'sort_order',
    )
    list_filter = ('active', 'category', 'unit')
    search_fields = ('name',)
    list_editable = (
        'category', 'unit', 'min_weight_kg', 'max_weight_kg',
        'rate_per_kg', 'estimated_days', 'active', 'sort_order',
    )
