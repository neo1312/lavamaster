from rest_framework import serializers

from customers.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    active_orders = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = (
            'id', 'name', 'phone', 'email', 'rfc', 'notes', 'blacklisted',
            'created_at', 'updated_at', 'active_orders',
        )
