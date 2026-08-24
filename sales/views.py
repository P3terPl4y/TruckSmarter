from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from vehicles.models import Vehicle
from .models import Sale

@login_required
def purchase_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, is_active=True)
    # No comprar el propio vehículo
    if vehicle.created_by == request.user:
        messages.error(request, "No puedes comprar tu propio vehículo.")
        return redirect('vehicles:detail', pk=vehicle.id)
    # Verificar que no esté ya vendido (podrías tener un campo sold en Vehicle)
    if hasattr(vehicle, 'sold') and vehicle.sold:
        messages.error(request, "Este vehículo ya ha sido vendido.")
        return redirect('vehicles:detail', pk=vehicle.id)
    
    if request.method == 'POST':
        # Crear la venta
        sale = Sale.objects.create(
            vehicle=vehicle,
            buyer=request.user,
            seller=vehicle.created_by,
            amount=vehicle.price,
            buyer_phone=request.POST.get('phone', ''),
            buyer_email=request.POST.get('email', ''),
            notes=request.POST.get('notes', '')
        )
        # Opcional: marcar vehículo como vendido (agregar campo sold en Vehicle)
        # vehicle.sold = True
        # vehicle.save()
        messages.success(request, f"¡Compra realizada con éxito! El vendedor se contactará contigo.")
        return redirect('vehicles:detail', pk=vehicle.id)
    
    return redirect('vehicles:detail', pk=vehicle.id)
