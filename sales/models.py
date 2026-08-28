from django.conf import settings
from django.db import models

from vehicles.models import Vehicle


class Sale(models.Model):
    STATUS_CHOICES = (
        ('offer_pending', 'Oferta pendiente'),
        ('offer_accepted', 'Oferta aceptada'),
        ('offer_rejected', 'Oferta rechazada'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='sales')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='purchases')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sales')
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # Precio original del vehículo
    offered_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # Precio ofertado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offer_pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    buyer_phone = models.CharField(max_length=20, blank=True)
    buyer_email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Venta de {self.vehicle} - {self.buyer.username}"

    class Meta:
        ordering = ["-created_at"]
