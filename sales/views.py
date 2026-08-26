from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.urls import reverse
from vehicles.models import Vehicle
from .models import Sale
from django.shortcuts import get_object_or_404, redirect
from .services import send_reservation_notifications, send_cancellation_notification, send_admin_cancellation_notification
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

def get_admin_user():
    """Obtiene el primer superusuario o usuario con role='admin'."""
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.filter(role='admin').first()
    return admin
    
@login_required
@transaction.atomic
def reserve_vehicle(request, vehicle_id):
    vehicle = get_object_or_404(
        Vehicle.objects.select_for_update(),
        id=vehicle_id,
        is_active=True,
        sold=False,
        reserved=False,
    )

    if vehicle.created_by == request.user:
        messages.error(request, "No puedes reservar tu propio vehículo.")
        return redirect("vehicles:detail", pk=vehicle_id)

    # Crear la venta
    sale = Sale.objects.create(
        vehicle=vehicle,
        buyer=request.user,
        seller=vehicle.created_by,
        amount=vehicle.price,
        status="reserved",
        buyer_phone=request.user.profile.phone if hasattr(request.user, "profile") else "",
        buyer_email=request.user.email,
    )

    # Marcar vehículo como reservado
    vehicle.reserved = True
    vehicle.reserved_by = request.user
    vehicle.save()

    # Obtener administrador
    admin_user = get_admin_user()

    # Enviar notificaciones
    try:
        send_reservation_notifications(
            vehicle=vehicle,
            buyer=request.user,
            admin_user=admin_user,
            sale=sale
        )
    except Exception as e:
        logger.error(f"Error al enviar email de reserva: {e}")
        # No interrumpir el flujo

    messages.success(
        request,
        f"¡Vehículo reservado! {vehicle.brand.name} {vehicle.model} ha sido reservado."
    )
    return redirect("vehicles:detail", pk=vehicle_id)

@login_required
@transaction.atomic
def cancel_reservation(request, vehicle_id):
    vehicle = get_object_or_404(
        Vehicle.objects.select_for_update(),
        id=vehicle_id,
        reserved=True,
        reserved_by=request.user,
    )

    # Obtener la venta asociada
    sale = Sale.objects.filter(vehicle=vehicle, buyer=request.user, status="reserved").first()
    if sale:
        sale.status = "cancelled"
        sale.save()

    # Liberar vehículo
    vehicle.reserved = False
    vehicle.reserved_by = None
    vehicle.save()

    # Obtener administrador
    admin_user = get_admin_user()

    # Enviar email de cancelación al comprador
    try:
        send_cancellation_notification(vehicle, request.user)
    except Exception as e:
        logger.error(f"Error al enviar email de cancelación al comprador: {e}")

    # Enviar email de cancelación al administrador
    if admin_user:
        try:
            send_admin_cancellation_notification(vehicle, request.user, admin_user)
        except Exception as e:
            logger.error(f"Error al enviar email de cancelación al admin: {e}")

    messages.info(request, f"Has cancelado la reserva de {vehicle.brand.name} {vehicle.model}.")
    return redirect("vehicles:detail", pk=vehicle_id)

@login_required
def purchase_history(request):
    """Ver historial de compras del usuario."""
    sales = Sale.objects.filter(buyer=request.user).select_related("vehicle", "seller")
    return render(request, "sales/history.html", {"sales": sales})
