from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from analytics.mixins import TrackVehicleViewMixin
from core.mixins import OwnerOrAdminRequiredMixin, SellerRequiredMixin
from core.permissions import can_manage_vehicle, is_admin
from sales.models import Sale
from .forms import VehicleForm
from .models import Vehicle


class VehicleListView(ListView):
    model = Vehicle
    template_name = "vehicles/list.html"
    context_object_name = "vehicles"
    paginate_by = 12
    ordering = ["-created_at", "-pk"]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("brand", "created_by")
            .filter(is_active=True, sold=False)
        )
        brand = self.request.GET.get("brand", "").strip()
        if brand:
            qs = qs.filter(brand__name__icontains=brand)
        for key, lookup in (("min_price", "price__gte"), ("max_price", "price__lte")):
            raw = self.request.GET.get(key, "").strip()
            if not raw:
                continue
            try:
                value = Decimal(raw)
                if not value.is_finite() or not 0 <= value <= Decimal("9999999999.99"):
                    raise ValueError
            except InvalidOperation, ValueError:
                messages.error(
                    self.request,
                    "Los filtros de precio deben ser números positivos válidos.",
                )
                return qs.none()
            qs = qs.filter(**{lookup: value})
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(model__icontains=query)
                | Q(brand__name__icontains=query)
                | Q(description__icontains=query)
            )
        return qs


class VehicleDetailView(TrackVehicleViewMixin, DetailView):
    model = Vehicle
    template_name = "vehicles/detail.html"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("brand", "created_by__profile")
            .prefetch_related("images")
        )
        if is_admin(self.request.user):
            return qs
        visible = Q(is_active=True, sold=False)
        if self.request.user.is_authenticated:
            visible |= Q(created_by=self.request.user) | Q(
                sales__buyer=self.request.user
            )
        return qs.filter(visible).distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle, user = self.object, self.request.user
        offer = None
        if user.is_authenticated:
            offer = Sale.objects.filter(
                vehicle=vehicle, buyer=user, status="offer_pending"
            ).first()
        context.update(
            user_pending_offer=offer,
            user_has_pending_offer=offer is not None,
            can_edit=can_manage_vehicle(user, vehicle) and not vehicle.sold,
            max_offer=vehicle.price - Decimal("0.01"),
            can_offer=user.is_authenticated
            and vehicle.is_active
            and not vehicle.sold
            and not vehicle.reserved
            and vehicle.created_by_id is not None
            and vehicle.created_by_id != user.pk
            and offer is None,
        )
        return context


class VehicleCreateView(LoginRequiredMixin, SellerRequiredMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "vehicles/form.html"
    success_url = reverse_lazy("vehicles:list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "¡Vehículo publicado exitosamente!")
        return response


class VehicleUpdateView(LoginRequiredMixin, OwnerOrAdminRequiredMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "vehicles/form.html"
    success_url = reverse_lazy("vehicles:list")

    def get_queryset(self):
        return super().get_queryset().filter(sold=False)

    def form_valid(self, form):
        from sales.workflow import update_listing

        try:
            update_listing(form.instance.pk, form.cleaned_data)
        except ValueError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "¡Vehículo actualizado exitosamente!")
        return redirect(self.success_url)


class VehicleDeleteView(LoginRequiredMixin, OwnerOrAdminRequiredMixin, DeleteView):
    model = Vehicle
    template_name = "vehicles/confirm_delete.html"
    success_url = reverse_lazy("vehicles:list")

    def form_valid(self, form):
        from sales.workflow import withdraw_listing

        try:
            withdraw_listing(self.object.pk)
        except ValueError as exc:
            messages.error(self.request, str(exc))
            return redirect("vehicles:detail", pk=self.object.pk)
        messages.success(self.request, "Vehículo retirado correctamente.")
        return redirect(self.success_url)
