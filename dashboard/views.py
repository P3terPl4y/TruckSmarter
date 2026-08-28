# dashboard/views.py
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import (CreateView, DeleteView, ListView,
                                  TemplateView, UpdateView)

from core.mixins import AdminRequiredMixin
# dashboard/views.py
from sales.models import Sale  # <-- Agregar esta línea
from users.forms import UserAdminForm
from vehicles.forms import BrandForm
from vehicles.models import Brand

User = get_user_model()


# Vista de inicio del dashboard
class DashboardHomeView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "dashboard/home.html"


# Gestión de usuarios
class UserListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = User
    template_name = "dashboard/user_list.html"
    context_object_name = "users"
    ordering = ["-date_joined"]


class UserCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = User
    form_class = UserAdminForm
    template_name = "dashboard/user_form.html"
    success_url = reverse_lazy("dashboard:user_list")


class UserUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserAdminForm
    template_name = "dashboard/user_form.html"
    success_url = reverse_lazy("dashboard:user_list")


class UserDeleteView(AdminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = User
    template_name = "dashboard/user_confirm_delete.html"
    success_url = reverse_lazy("dashboard:user_list")


# Gestión de marcas
class BrandListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = Brand
    template_name = "dashboard/brand_list.html"
    context_object_name = "brands"


class BrandCreateView(AdminRequiredMixin, LoginRequiredMixin, CreateView):
    model = Brand
    form_class = BrandForm
    template_name = "dashboard/brand_form.html"
    success_url = reverse_lazy("dashboard:brand_list")


class BrandUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Brand
    form_class = BrandForm
    template_name = "dashboard/brand_form.html"
    success_url = reverse_lazy("dashboard:brand_list")


class BrandDeleteView(AdminRequiredMixin, LoginRequiredMixin, DeleteView):
    model = Brand
    template_name = "dashboard/brand_confirm_delete.html"
    success_url = reverse_lazy("dashboard:brand_list")


class OfferListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = Sale
    template_name = "dashboard/offer_list.html"
    context_object_name = "offers"
    queryset = Sale.objects.filter(status="offer_pending").select_related(
        "vehicle", "buyer", "seller"
    )
    ordering = ["-created_at"]
