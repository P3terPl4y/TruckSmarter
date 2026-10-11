import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    ROLE_CHOICES = (
        ("admin", "Administrador"),
        ("seller", "Comerciante"),
        ("customer", "Cliente"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower("email"), name="user_email_ci_unique"
            )
        ]

    def __str__(self):
        return self.username


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    # Datos de pago para comerciantes
    payment_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email para recibir pagos (ej. PayPal, MercadoPago)",
    )
    bank_account = models.CharField(
        max_length=100, blank=True, null=True, help_text="Número de cuenta bancaria"
    )
    payment_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Teléfono para pagos (ej. Bizum, WhatsApp)",
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


def get_expiration_time():
    return timezone.now() + timedelta(hours=24)


class EmailVerification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verifications",
    )
    email = models.EmailField()
    token = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )  # <-- Agregar
    expires_at = models.DateTimeField(default=get_expiration_time)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Verificación de {self.user.email}"

    def is_expired(self):
        return timezone.now() > self.expires_at


class JWTGrant(models.Model):
    """Store only a SHA-256 fingerprint, bound to the issuing browser session."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    jti_digest = models.CharField(max_length=64, unique=True)
    session_key = models.CharField(max_length=40, db_index=True)
    auth_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
