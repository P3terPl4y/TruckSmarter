from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from .models import Vehicle
from .froms import VehicleForm  # crea un ModelForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import UpdateView, DeleteView

class VehicleListView(ListView):
    model = Vehicle
    template_name = 'vehicles/list.html'
    context_object_name = 'vehicles'
    paginate_by = 12
    ordering = ['-created_at']
    def get_queryset(self):
        qs = super().get_queryset().filter(is_active=True)
        # Aplicar filtros desde GET
        brand = self.request.GET.get('brand')
        if brand:
            qs = qs.filter(brand__name__icontains=brand)
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        # ... más filtros
        return qs

class VehicleDetailView(DetailView):
    model = Vehicle
    template_name = 'vehicles/detail.html'


class VehicleCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/form.html'
    success_url = reverse_lazy('vehicles:list')

    def test_func(self):
        user = self.request.user
        # Permitir solo a comerciantes y administradores
        return user.is_authenticated and user.role in ['seller', 'admin']

    def handle_no_permission(self):
        raise PermissionDenied("Solo comerciantes y administradores pueden publicar vehículos.")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class VehicleUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/form.html'
    success_url = reverse_lazy('vehicles:list')

    def test_func(self):
        vehicle = self.get_object()
        user = self.request.user
        # Admin o superusuario pueden editar cualquier vehículo
        if user.is_superuser or user.role == 'admin':
            return True
        # Comerciante solo puede editar los suyos
        return vehicle.created_by == user

    def handle_no_permission(self):
        raise PermissionDenied("No tienes permiso para editar este vehículo.")

class VehicleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Vehicle
    success_url = reverse_lazy('vehicles:list')
    template_name = 'vehicles/confirm_delete.html'

    def test_func(self):
        vehicle = self.get_object()
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return True
        return vehicle.created_by == user

    def handle_no_permission(self):
        raise PermissionDenied("No tienes permiso para eliminar este vehículo.")
