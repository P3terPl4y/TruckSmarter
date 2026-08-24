from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from vehicles.models import Vehicle

from .models import Sale


@login_required
@transaction.atomic
def purchase_vehicle(request, vehicle_id):
    """
    Procesa la compra de un vehículo con transacción atómica para evitar race conditions.
    """
    # Bloquear la fila para evitar compras concurrentes
    vehicle = get_object_or_404(
        Vehicle.objects.select_for_update(), id=vehicle_id, is_active=True, sold=False
    )

    # No permitir comprar propio vehículo
    if vehicle.created_by == request.user:
        messages.error(request, "No puedes comprar tu propio vehículo.")
        return redirect("vehicles:detail", pk=vehicle_id)

    # Crear la venta
    sale = Sale.objects.create(
        vehicle=vehicle,
        buyer=request.user,
        seller=vehicle.created_by,
        amount=vehicle.price,  # Usar 'amount' como está en el modelo
        status="completed",
        buyer_phone=(
            request.user.profile.phone if hasattr(request.user, "profile") else ""
        ),
        buyer_email=request.user.email,
    )

    # Marcar el vehículo como vendido
    vehicle.sold = True
    vehicle.is_active = False  # Opcional: ocultar vehículos vendidos
    vehicle.save()

    messages.success(
        request,
        f"¡Felicidades! Has comprado {vehicle.brand.name} {vehicle.model} por ${vehicle.price}.",
    )

    # TODO: Enviar email de confirmación al comprador y vendedor

    return redirect("vehicles:detail", pk=vehicle_id)


@login_required
def purchase_history(request):
    """Ver historial de compras del usuario."""
    sales = Sale.objects.filter(buyer=request.user).select_related("vehicle", "seller")
    return render(request, "sales/history.html", {"sales": sales})
