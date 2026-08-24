from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from .models import Vehicle
from .froms import VehicleForm  # crea un ModelForm

class VehicleListView(ListView):
    model = Vehicle
    template_name = 'vehicles/list.html'
    context_object_name = 'vehicles'
    paginate_by = 12

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

class VehicleCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/form.html'
    permission_required = 'vehicles.add_vehicle'
    success_url = reverse_lazy('vehicles:list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class VehicleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = 'vehicles/form.html'
    permission_required = 'vehicles.change_vehicle'
    success_url = reverse_lazy('vehicles:list')

class VehicleDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Vehicle
    permission_required = 'vehicles.delete_vehicle'
    success_url = reverse_lazy('vehicles:list')
    template_name = 'vehicles/confirm_delete.html'
