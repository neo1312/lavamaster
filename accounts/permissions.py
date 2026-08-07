from rest_framework.permissions import BasePermission

CASHIER = 'cashier'
ADMIN = 'admin'


def has_role(user, *roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.role in roles


class IsCashierOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, CASHIER, ADMIN)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, ADMIN)
