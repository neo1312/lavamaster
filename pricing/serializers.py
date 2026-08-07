from rest_framework import serializers

from pricing.models import ServiceCategory, ServiceType


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ('id', 'name', 'emoji', 'sort_order')


class ServiceTypeSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.all(), required=False, allow_null=True,
    )
    category_name = serializers.CharField(
        source='category.name', read_only=True, default=''
    )
    unit_display = serializers.CharField(
        source='get_unit_display', read_only=True
    )

    class Meta:
        model = ServiceType
        fields = (
            'id', 'name', 'description', 'category', 'category_name',
            'unit', 'unit_display', 'min_weight_kg', 'max_weight_kg',
            'rate_per_kg', 'estimated_days', 'active', 'sort_order',
            'created_at', 'updated_at',
        )
