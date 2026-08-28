from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from core.mixins import OwnerOrAdminRequiredMixin, SellerRequiredMixin,AdminRequiredMixin

from .forms import VehicleForm
from .models import Vehicle
from django.shortcuts import redirect
from analytics.mixins import TrackVehicleViewMixin

class VehicleListView(ListView):
    model = Vehicle
    template_name = "vehicles/list.html"
    context_object_name = "vehicles"
    paginate_by = 12
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("brand", "created_by")
            .filter(is_active=True)
        )

        # Filtros con validación
        brand = self.request.GET.get("brand")
        if brand:
            qs = qs.filter(brand__name__icontains=brand)

        # Validar y sanitizar precios
        min_price = self.request.GET.get("min_price")
        if min_price and min_price.isdigit():
            qs = qs.filter(price__gte=int(min_price))

        max_price = self.request.GET.get("max_price")
        if max_price and max_price.isdigit():
            qs = qs.filter(price__lte=int(max_price))

        # Búsqueda por texto (opcional)
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(model__icontains=q)
                | Q(brand__name__icontains=q)
                | Q(description__icontains=q)
            )

        return qs


class VehicleDetailView(TrackVehicleViewMixin,DetailView):
    model = Vehicle
    template_name = "vehicles/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Verificar si el usuario puede editar este vehículo
        vehicle = self.get_object()
        user = self.request.user
        context["can_edit"] = user.is_authenticated and (
            user.role == "admin" or user.is_superuser or vehicle.created_by == user
        )
        return context


class VehicleCreateView(LoginRequiredMixin, SellerRequiredMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "vehicles/form.html"
    success_url = reverse_lazy("vehicles:list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "¡Vehículo publicado exitosamente!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, "Error al publicar el vehículo. Revisa los campos."
        )
        return super().form_invalid(form)


class VehicleUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "vehicles/form.html"
    success_url = reverse_lazy("vehicles:list")

    def form_valid(self, form):
        messages.success(self.request, "¡Vehículo actualizado exitosamente!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, "Error al actualizar el vehículo. Revisa los campos."
        )
        return super().form_invalid(form)


class VehicleDeleteView(LoginRequiredMixin, OwnerOrAdminRequiredMixin, DeleteView):
    model = Vehicle
    template_name = 'vehicles/confirm_delete.html'
    success_url = reverse_lazy('vehicles:list')

    def delete(self, request, *args, **kwargs):
        """Soft delete: marcar como inactivo en lugar de eliminar."""
        self.object = self.get_object()
        self.object.is_active = False
        self.object.sold = True  # Opcional
        self.object.save()
        messages.success(request, "Vehículo eliminado correctamente.")
        return redirect(self.success_url)
