from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse


class SellerRequiredMixin(UserPassesTestMixin):
    """Permite acceso solo a comerciantes y administradores."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in [
            "seller",
            "admin",
        ]

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(
                self.request,
                "Necesitas ser comerciante o administrador para realizar esta acción.",
            )
            return redirect("vehicles:list")
        return redirect("users:login")


class AdminRequiredMixin(UserPassesTestMixin):
    """Permite acceso solo a administradores."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(
                self.request, "Necesitas ser administrador para realizar esta acción."
            )
            return redirect("vehicles:list")
        return redirect("users:login")


class OwnerOrAdminRequiredMixin(UserPassesTestMixin):
    """Permite acceso al propietario del objeto o a administradores."""

    def test_func(self):
        obj = self.get_object() if hasattr(self, "get_object") else None
        user = self.request.user

        # Administradores y superusuarios siempre pueden
        if user.is_superuser or user.role == "admin":
            return True

        # Verificar si el objeto tiene el atributo 'created_by'
        if obj and hasattr(obj, "created_by"):
            return obj.created_by == user

        # Si no tiene 'created_by', denegar acceso
        return False

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(
                self.request, "No tienes permiso para modificar este vehículo."
            )
            return redirect("vehicles:list")
        return redirect("users:login")
