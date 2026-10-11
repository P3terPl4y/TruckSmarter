from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from core.mixins import AdminRequiredMixin
from sales.models import Sale
from users.views import UserUpdateView as BaseUserUpdateView
from .forms import BrandForm, UserAdminCreationForm
from vehicles.models import Brand

User = get_user_model()


class DashboardHomeView(AdminRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "dashboard/user_list.html"
    context_object_name = "users"
    ordering = ["-date_joined", "-pk"]
    paginate_by = 25


class UserCreateView(AdminRequiredMixin, CreateView):
    model = User
    form_class = UserAdminCreationForm
    template_name = "dashboard/user_form.html"
    success_url = reverse_lazy("dashboard:user_list")


class UserUpdateView(BaseUserUpdateView):
    success_url = reverse_lazy("dashboard:user_list")


class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    template_name = "dashboard/user_confirm_delete.html"
    success_url = reverse_lazy("dashboard:user_list")

    def get_queryset(self):
        qs = super().get_queryset()
        return (
            qs
            if self.request.user.is_superuser
            else qs.filter(is_superuser=False, is_staff=False)
        )

    def form_valid(self, form):
        if self.object == self.request.user:
            raise PermissionDenied("No puedes eliminar tu propia cuenta.")
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "Este usuario tiene vehículos o historial comercial. Puedes desactivar su cuenta desde Editar.",
            )
            return redirect(self.success_url)


class BrandListView(AdminRequiredMixin, ListView):
    model = Brand
    template_name = "dashboard/brand_list.html"
    context_object_name = "brands"
    ordering = ["name", "pk"]
    paginate_by = 25


class BrandCreateView(AdminRequiredMixin, CreateView):
    model = Brand
    form_class = BrandForm
    template_name = "dashboard/brand_form.html"
    success_url = reverse_lazy("dashboard:brand_list")


class BrandUpdateView(AdminRequiredMixin, UpdateView):
    model = Brand
    form_class = BrandForm
    template_name = "dashboard/brand_form.html"
    success_url = reverse_lazy("dashboard:brand_list")


class BrandDeleteView(AdminRequiredMixin, DeleteView):
    model = Brand
    template_name = "dashboard/brand_confirm_delete.html"
    success_url = reverse_lazy("dashboard:brand_list")

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar una marca que tiene vehículos asociados.",
            )
            return redirect(self.success_url)


class OfferListView(AdminRequiredMixin, ListView):
    model = Sale
    template_name = "dashboard/offer_list.html"
    context_object_name = "offers"
    queryset = Sale.objects.filter(status="offer_pending").select_related(
        "vehicle__brand", "buyer", "seller"
    )
    ordering = ["-created_at", "-pk"]
    paginate_by = 25
