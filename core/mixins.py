# core/mixins.py
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class SellerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in ['seller', 'admin']
    
    def handle_no_permission(self):
        raise PermissionDenied("Necesitas ser comerciante o administrador para realizar esta acción.")

class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'

class OwnerOrAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object() if hasattr(self, 'get_object') else None
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return True
        # Asumimos que el modelo tiene un campo 'created_by' o 'user'
        return hasattr(obj, 'created_by') and obj.created_by == user

    def handle_no_permission(self):
        raise PermissionDenied("No tienes permiso para modificar este vehículo.")
