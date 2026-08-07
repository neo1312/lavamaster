from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsCashierOrAdmin, IsAdmin
from customers.models import Customer
from customers.serializers import CustomerSerializer


class CustomerViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsCashierOrAdmin]
    filterset_fields = ('blacklisted',)
    search_fields = ('name', 'phone', 'email', 'rfc')

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('search')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset

    @action(detail=False, methods=['get'])
    def search(self, request):
        q = request.query_params.get('q', '').strip()
        if len(q) < 2:
            return Response([])
        matches = self.queryset.filter(name__icontains=q)[:10]
        return Response(CustomerSerializer(matches, many=True).data)
