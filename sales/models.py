from django.conf import settings
from django.db import models

from vehicles.models import Vehicle


class Sale(models.Model):
    STATUS_CHOICES = (
        ("reserved", "Reservada"),
        ("offer_pending", "Oferta pendiente"),
        ("offer_accepted", "Oferta aceptada"),
        ("offer_rejected", "Oferta rechazada"),
        ("completed", "Completada"),
        ("cancelled", "Cancelada"),
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name="sales")
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchases"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales"
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2
    )  # Precio original del vehículo
    offered_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )  # Precio ofertado
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="offer_pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    buyer_phone = models.CharField(max_length=20, blank=True)
    buyer_email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Venta de {self.vehicle} - {self.buyer.username}"

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle", "buyer"],
                condition=models.Q(status="offer_pending"),
                name="one_pending_offer_per_buyer",
            ),
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=models.Q(status="reserved"),
                name="one_reservation_per_vehicle",
            ),
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=models.Q(status__in=["offer_accepted", "completed"]),
                name="one_final_sale_per_vehicle",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="sale_amount_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(offered_price__isnull=True)
                | (
                    models.Q(offered_price__gt=0)
                    & models.Q(offered_price__lt=models.F("amount"))
                ),
                name="sale_offer_valid",
            ),
        ]
