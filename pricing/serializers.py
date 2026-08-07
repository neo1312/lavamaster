from rest_framework import serializers

from pricing.models import ServiceType


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = (
            'id', 'name', 'description', 'rate_per_kg', 'estimated_days',
            'active', 'sort_order', 'created_at', 'updated_at',
        )
