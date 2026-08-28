from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from analytics.mixins import TrackVehicleViewMixin
from core.mixins import (AdminRequiredMixin, OwnerOrAdminRequiredMixin,
                         SellerRequiredMixin)
# vehicles/views.py
from sales.models import Sale  # <-- Agregar esta línea

from .forms import VehicleForm
from .models import Vehicle
from django.views import View

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


class VehicleDetailView(TrackVehicleViewMixin, DetailView):
    model = Vehicle
    template_name = "vehicles/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle = self.get_object()
        user = self.request.user

        # Oferta pendiente del usuario actual (si existe)
        user_pending_offer = None
        if user.is_authenticated:
            user_pending_offer = Sale.objects.filter(
                vehicle=vehicle, buyer=user, status="offer_pending"
            ).first()

        context["user_pending_offer"] = user_pending_offer
        context["user_has_pending_offer"] = user_pending_offer is not None

        # Oferta pendiente general (para otros usos, como mostrar el estado global)
        context["pending_offer"] = Sale.objects.filter(
            vehicle=vehicle, status="offer_pending"
        ).first()

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


class VehicleDeleteView(LoginRequiredMixin, OwnerOrAdminRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        vehicle = get_object_or_404(Vehicle, pk=pk)
        return render(request, 'vehicles/confirm_delete.html', {'object': vehicle})

    def post(self, request, pk, *args, **kwargs):
        vehicle = get_object_or_404(Vehicle, pk=pk)
        vehicle.is_active = False
        vehicle.sold = True
        vehicle.save()
        messages.success(request, "Vehículo eliminado correctamente.")
        return redirect('vehicles:list')
