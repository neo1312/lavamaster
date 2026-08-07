from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsCashierOrAdmin
from orders.models import Order, Payment, ACTIVE_STATUSES
from orders.serializers import (
    OrderSerializer,
    OrderStatusSerializer,
    PaymentSerializer,
)


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Order.objects.select_related('customer', 'received_by').prefetch_related(
        'lines', 'lines__service_type', 'payments'
    )
    serializer_class = OrderSerializer
    permission_classes = [IsCashierOrAdmin]
    filterset_fields = ('status', 'customer')

    def get_queryset(self):
        queryset = super().get_queryset()
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(received_at__date=date)
        today = self.request.query_params.get('today')
        if today == '1':
            from django.utils import timezone
            queryset = queryset.filter(received_at__date=timezone.localdate())
        active = self.request.query_params.get('active')
        if active == '1':
            queryset = queryset.filter(status__in=ACTIVE_STATUSES)
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsCashierOrAdmin])
    def status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order.transition_status(serializer.validated_data['status'])
        except ValidationError as exc:
            return Response(
                {'detail': exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(OrderSerializer(order, context=self.get_serializer_context()).data)

    @action(detail=True, methods=['get', 'post'], permission_classes=[IsCashierOrAdmin])
    def payments(self, request, pk=None):
        order = self.get_object()
        if request.method == 'POST':
            serializer = PaymentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            try:
                payment = serializer.save(order=order, received_by=request.user)
            except ValidationError as exc:
                return Response(
                    {'detail': exc.messages[0]}, status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                PaymentSerializer(payment).data, status=status.HTTP_201_CREATED
            )
        return Response(PaymentSerializer(order.payments.all(), many=True).data)

    @action(detail=True, methods=['get'])
    def ticket(self, request, pk=None):
        from orders.ticket import ticket_html
        order = self.get_object()
        return ticket_html(request, order)

    @action(detail=True, methods=['get'])
    def ticket_pdf(self, request, pk=None):
        from orders.ticket import ticket_pdf
        order = self.get_object()
        return ticket_pdf(order)
