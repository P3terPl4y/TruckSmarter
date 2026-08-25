# core/mixins.py
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class SellerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user and user.is_authenticated and user.role in ['seller', 'admin']
    
    def handle_no_permission(self):
        if self.request.user and self.request.user.is_authenticated:
            raise PermissionDenied("Necesitas ser comerciante o administrador para realizar esta acción.")
        return super().handle_no_permission()


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user and user.is_authenticated and user.role == 'admin'
    
    def handle_no_permission(self):
        if self.request.user and self.request.user.is_authenticated:
            raise PermissionDenied("Necesitas ser administrador para realizar esta acción.")
        return super().handle_no_permission()


class OwnerOrAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        obj = self.get_object() if hasattr(self, 'get_object') else None
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return False
        
        if user.is_superuser or user.role == 'admin':
            return True
        
        if obj and hasattr(obj, 'created_by'):
            return obj.created_by == user
        
        return False
    
    def handle_no_permission(self):
        if self.request.user and self.request.user.is_authenticated:
            raise PermissionDenied("No tienes permiso para modificar este vehículo.")
        return super().handle_no_permission()
# core/mixins.py
class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_superuser or user.role == 'admin')

    def handle_no_permission(self):
        raise PermissionDenied("No tienes permisos para acceder a esta sección.")
