from rest_framework import serializers

from customers.models import Customer
from orders.models import Order, OrderLine, Payment


class OrderLineSerializer(serializers.ModelSerializer):
    service_type_name = serializers.CharField(
        source='service_type.name', read_only=True
    )
    rate_per_kg = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = OrderLine
        fields = (
            'id', 'service_type', 'service_type_name', 'weight_kg',
            'rate_per_kg', 'subtotal', 'notes',
        )


class PaymentSerializer(serializers.ModelSerializer):
    payment_type_display = serializers.CharField(
        source='get_payment_type_display', read_only=True
    )
    method_display = serializers.CharField(
        source='get_method_display', read_only=True
    )
    received_by_name = serializers.CharField(
        source='received_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = Payment
        fields = (
            'id', 'amount', 'method', 'method_display', 'payment_type',
            'payment_type_display', 'reference', 'received_by_name',
            'received_at',
        )
        read_only_fields = ('payment_type',)


class OrderSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone', read_only=True)
    lines = OrderLineSerializer(many=True)
    payments = PaymentSerializer(many=True, read_only=True)
    paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    payment = PaymentSerializer(required=False, write_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'number', 'ticket_number', 'status', 'status_display',
            'customer', 'customer_name', 'customer_phone',
            'total_weight_kg', 'subtotal', 'paid', 'balance_due',
            'promised_at', 'notes', 'received_by', 'received_at',
            'delivered_at', 'completed_at', 'created_at', 'updated_at',
            'lines', 'payments', 'payment',
        )
        read_only_fields = (
            'number', 'ticket_number', 'status', 'total_weight_kg', 'subtotal',
            'paid', 'balance_due', 'received_by', 'received_at',
            'delivered_at', 'completed_at',
        )

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError('La orden requiere al menos una línea.')
        for line in lines:
            if line.get('weight_kg', 0) <= 0:
                raise serializers.ValidationError(
                    'El peso debe ser mayor a cero en todas las líneas.'
                )
        return lines

    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        lines_data = validated_data.pop('lines')
        payment_data = validated_data.pop('payment', None)
        validated_data['received_by'] = self.context['request'].user
        order = Order.objects.create(**validated_data)
        for line_data in lines_data:
            OrderLine.objects.create(order=order, **line_data)
        order.refresh_totals()
        if payment_data:
            Payment.objects.create(
                order=order,
                received_by=validated_data['received_by'],
                **payment_data,
            )
        return order

    def update(self, instance, validated_data):
        lines_data = validated_data.pop('lines', None)
        instance.customer = validated_data.get('customer', instance.customer)
        instance.promised_at = validated_data.get('promised_at', instance.promised_at)
        instance.notes = validated_data.get('notes', instance.notes)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line_data in lines_data:
                OrderLine.objects.create(order=instance, **line_data)
            instance.refresh_totals()
        return instance


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
