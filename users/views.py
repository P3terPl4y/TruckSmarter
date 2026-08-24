from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.mixins import (LoginRequiredMixin,
                                        PermissionRequiredMixin)
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView

from .forms import CustomUserCreationForm, ProfileForm, UserAdminForm
from .models import Profile, User

User = get_user_model()


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registro exitoso. Bienvenido!")
            return redirect("vehicles:list")
    else:
        form = CustomUserCreationForm()
    return render(request, "users/register.html", {"form": form})


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = "users/admin/user_list.html"
    context_object_name = "users"
    permission_required = "users.can_manage_users"


class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = User
    form_class = UserAdminForm
    template_name = "users/admin/user_form.html"
    permission_required = "users.can_manage_users"
    success_url = reverse_lazy("users:admin_list")


class CustomLoginView(LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True


class CustomLogoutView(LogoutView):
    next_page = "vehicles:list"


def logout_view(request):
    logout(request)
    return redirect("vehicles:list")


class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "users/profile.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Crear perfil si no existe
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        context["profile"] = profile

        # Mostrar vehículos si es comerciante o admin
        if self.request.user.role in ["seller", "admin"]:
            from vehicles.models import Vehicle

            context["vehicles"] = Vehicle.objects.filter(
                created_by=self.request.user, is_active=True
            ).select_related("brand")

        return context

    def form_valid(self, form):
        messages.success(self.request, "¡Perfil actualizado correctamente!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, "Error al actualizar el perfil. Revisa los campos."
        )
        return super().form_invalid(form)


class ChangeRoleView(LoginRequiredMixin, UpdateView):
    model = User
    fields = []  # no hay campos, solo cambiamos el rol
    template_name = "users/change_role.html"  # opcional, puedes redirigir
    success_url = reverse_lazy("users:profile")

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        user = self.get_object()
        # Solo permitir cambiar si es cliente -> comerciante (o puedes permitir ambos)
        if user.role == "customer":
            user.role = "seller"
            user.save()
            messages.success(
                request,
                "¡Felicidades! Ahora eres comerciante y puedes publicar vehículos.",
            )
        else:
            # Si ya es comerciante, podrías permitir volver a cliente (opcional)
            # user.role = 'customer'
            # user.save()
            # messages.info(request, 'Has vuelto a ser cliente.')
            messages.info(request, "Ya eres comerciante.")
        return redirect(self.success_url)
