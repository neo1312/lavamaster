from django.contrib import admin

from .models import ServiceType


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'rate_per_kg', 'estimated_days', 'active', 'sort_order')
    list_filter = ('active',)
    search_fields = ('name',)
    list_editable = ('rate_per_kg', 'estimated_days', 'active', 'sort_order')
