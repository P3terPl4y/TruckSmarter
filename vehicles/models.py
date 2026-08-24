from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)

    def __str__(self):
        return self.name

class Vehicle(models.Model):
    TRANSMISSION_CHOICES = (
        ('manual', 'Manual'),
        ('automatic', 'Automática'),
        ('cvt', 'CVT'),
    )
    FUEL_CHOICES = (
        ('gasoline', 'Gasolina'),
        ('diesel', 'Diésel'),
        ('electric', 'Eléctrico'),
        ('hybrid', 'Híbrido'),
    )
    STATUS_CHOICES = (
        ('new', 'Nuevo'),
        ('used', 'Usado'),
    )

    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='vehicles')
    model = models.CharField(max_length=100)
    year = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    mileage = models.PositiveIntegerField(help_text="Kilometraje (km)")
    transmission = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES)
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='used')
    description = models.TextField(blank=True)
    main_image = models.ImageField(upload_to='vehicles/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='vehicles_created')
    is_active = models.BooleanField(default=True)
    sold = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.brand.name} {self.model} ({self.year})"
        
    def mark_as_sold(self, buyer):
        """Marca el vehículo como vendido (con transacción)."""
        from sales.models import Sale
        with transaction.atomic():
            self.sold = True
            self.is_active = False
            self.save()
            return Sale.objects.create(
                vehicle=self,
                buyer=buyer,
                seller=self.created_by,
                amount=self.price,
                status='completed'
            )
class VehicleImage(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='vehicles/')
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Imagen de {self.vehicle}"
