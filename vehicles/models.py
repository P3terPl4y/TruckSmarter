from django.conf import settings
from django.contrib.auth import get_user_model
from decimal import Decimal

from django.core.validators import FileExtensionValidator, MinValueValidator
from core.validators import validate_image_size, validate_vehicle_year
from django.db import models, transaction

User = get_user_model()


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(
        upload_to="brands/", blank=True, null=True, validators=[validate_image_size]
    )

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    TRANSMISSION_CHOICES = (
        ("manual", "Manual"),
        ("automatic", "Automática"),
        ("cvt", "CVT"),
    )
    FUEL_CHOICES = (
        ("gasoline", "Gasolina"),
        ("diesel", "Diésel"),
        ("electric", "Eléctrico"),
        ("hybrid", "Híbrido"),
    )
    STATUS_CHOICES = (
        ("new", "Nuevo"),
        ("used", "Usado"),
    )

    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="vehicles")
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField(validators=[validate_vehicle_year])
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    mileage = models.PositiveIntegerField(help_text="Kilometraje (km)")
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="used")
    description = models.TextField(blank=True)
    main_image = models.ImageField(
        upload_to="vehicles/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "gif"]),
            validate_image_size,
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name="vehicles_created"
    )
    is_active = models.BooleanField(default=True)
    sold = models.BooleanField(default=False)
    reserved = models.BooleanField(default=False)
    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reserved_vehicles",
    )
    view_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.brand.name} {self.model} ({self.year})"

    class Meta:
        indexes = [
            models.Index(
                fields=["is_active", "sold", "-created_at"], name="vehicle_catalog_idx"
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gt=0), name="vehicle_price_positive"
            )
        ]

    def mark_as_sold(self, buyer):
        from sales.workflow import complete_purchase

        sale = complete_purchase(self.pk, buyer)
        self.refresh_from_db()
        return sale


class VehicleImage(models.Model):
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="vehicles/", validators=[validate_image_size])
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Imagen de {self.vehicle}"
