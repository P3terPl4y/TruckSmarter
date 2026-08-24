from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from vehicles.models import Vehicle
from .models import Sale

@login_required
def purchase_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, is_active=True, sold=False)

    # No permitir comprar tu propio vehículo
    if vehicle.created_by == request.user:
        messages.error(request, 'No puedes comprar tu propio vehículo.')
        return redirect('vehicles:detail', pk=vehicle_id)

    # Crear la venta
    sale = Sale.objects.create(
        vehicle=vehicle,
        buyer=request.user,
        seller=vehicle.created_by,
        amount=vehicle.price,
        status='completed'  # O 'pending' si quieres flujo de pago
    )

    # Marcar el vehículo como vendido
    vehicle.sold = True
    vehicle.save()

    messages.success(request, f'¡Felicidades! Has comprado {vehicle.brand.name} {vehicle.model} por ${vehicle.price}.')
    return redirect('vehicles:detail', pk=vehicle_id)
