from django.contrib.auth.models import AbstractUser
from django.db import models

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    ROLE_CHOICES = (
        ('admin', 'Administrador'),
        ('seller', 'Vendedor'),
        ('customer', 'Cliente'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    # No definas groups ni user_permissions aquí, ya vienen de AbstractUser

    def __str__(self):
        return self.username

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    # otros campos que necesites

    def __str__(self):
        return f"Perfil de {self.user.username}"
