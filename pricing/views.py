from rest_framework import viewsets, mixins

from accounts.permissions import IsCashierOrAdmin, IsAdmin
from pricing.models import ServiceType
from pricing.serializers import ServiceTypeSerializer


class ServiceTypeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ServiceType.objects.filter(active=True)
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsCashierOrAdmin]
    filterset_fields = ('active',)

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return ServiceType.objects.all()
        return ServiceType.objects.filter(active=True)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdmin()]
        return super().get_permissions()
