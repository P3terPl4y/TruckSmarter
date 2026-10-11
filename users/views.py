import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import ListView, UpdateView
from django_ratelimit.decorators import ratelimit

from core.mixins import AdminRequiredMixin
from core.permissions import is_admin
from .forms import CustomUserCreationForm, ProfileForm, UserAdminForm
from .models import EmailVerification, Profile
from .services import send_verification_email

User = get_user_model()
logger = logging.getLogger(__name__)


def notify_verification(user, token):
    try:
        send_verification_email(user, token)
    except Exception:
        logger.exception("No se pudo enviar el correo de verificación")


@ratelimit(key="ip", rate="5/m", method="POST", block=False)
def register(request):
    if getattr(request, "limited", False):
        return HttpResponse(
            "Demasiados intentos. Intenta de nuevo en un minuto.", status=429
        )
    form = CustomUserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                token = EmailVerification.objects.create(user=user, email=user.email)
                transaction.on_commit(lambda: notify_verification(user, token))
        except IntegrityError:
            form.add_error(None, "El usuario o correo electrónico ya está registrado.")
        else:
            login(request, user)
            messages.success(
                request, "Registro exitoso. Revisa tu email para verificar tu cuenta."
            )
            return redirect("vehicles:list")
    return render(request, "users/register.html", {"form": form})


class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "dashboard/user_list.html"
    context_object_name = "users"
    ordering = ["-date_joined", "-pk"]
    paginate_by = 25


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserAdminForm
    template_name = "dashboard/user_form.html"
    success_url = reverse_lazy("users:admin_list")

    def get_queryset(self):
        qs = super().get_queryset()
        return (
            qs
            if self.request.user.is_superuser
            else qs.filter(is_superuser=False, is_staff=False)
        )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "actor": self.request.user}


class CustomLoginView(LoginView):
    template_name = "users/login.html"
    redirect_authenticated_user = True

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=False))
    def dispatch(self, request, *args, **kwargs):
        if getattr(request, "limited", False):
            return HttpResponse(
                "Demasiados intentos. Intenta de nuevo en un minuto.", status=429
            )
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.get_redirect_url() or reverse(
            "dashboard:home" if is_admin(self.request.user) else "vehicles:list"
        )


class CustomLogoutView(LogoutView):
    next_page = "vehicles:list"


class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "users/profile.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"], _ = Profile.objects.get_or_create(user=self.request.user)
        if (
            self.request.user.role in ["seller", "admin"]
            or self.request.user.is_superuser
        ):
            context["vehicles"] = self.request.user.vehicles_created.filter(
                is_active=True
            ).select_related("brand")
        return context

    def form_valid(self, form):
        messages.success(self.request, "¡Perfil actualizado correctamente!")
        return super().form_valid(form)


@transaction.atomic
def verify_email(request, token):
    verification = (
        EmailVerification.objects.select_for_update()
        .select_related("user")
        .filter(token=token, is_verified=False)
        .first()
    )
    if (
        verification is None
        or verification.expires_at <= timezone.now()
        or verification.email.lower() != verification.user.email.lower()
    ):
        messages.error(request, "Enlace inválido, expirado o ya utilizado.")
    else:
        verification.is_verified = True
        verification.save(update_fields=["is_verified"])
        messages.success(request, "Email verificado correctamente.")
    return redirect("users:login")
