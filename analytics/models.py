from django.conf import settings
from django.db import models

from vehicles.models import Vehicle


class VehicleView(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["vehicle", "viewed_at"]),
            models.Index(fields=["session_key", "vehicle"]),
        ]
        ordering = ["-viewed_at"]
