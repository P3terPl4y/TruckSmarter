"""from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VehicleView
from django.db.models.signals import post_delete
from django.db.models import F

@receiver(post_save, sender=VehicleView)
def increment_vehicle_view_count(sender, instance, created, **kwargs):
    if created:
        # Actualizar el contador del vehículo usando F() para evitar race conditions
        Vehicle = instance.vehicle.__class__
        Vehicle.objects.filter(pk=instance.vehicle.pk).update(view_count=F('view_count') + 1)

# analytics/signals.py
@receiver(post_delete, sender=VehicleView)
def decrement_vehicle_view_count(sender, instance, **kwargs):
    Vehicle = instance.vehicle.__class__
    Vehicle.objects.filter(pk=instance.vehicle.pk).update(view_count=F('view_count') - 1)
"""
