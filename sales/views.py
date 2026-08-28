import logging
# sales/views.py
from decimal import Decimal  # <-- Agregar esta línea

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.mixins import AdminRequiredMixin
from vehicles.models import Vehicle

from .models import Sale
from .services import (send_admin_cancellation_notification,
                       send_cancellation_notification,
                       send_offer_accepted_notification,
                       send_offer_notifications,
                       send_offer_rejected_notification,
                       send_reservation_notifications)

User = get_user_model()
logger = logging.getLogger(__name__)


def get_admin_user():
    """Obtiene el primer superusuario o usuario con role='admin'."""
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.filter(role="admin").first()
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
        buyer_phone=(
            request.user.profile.phone if hasattr(request.user, "profile") else ""
        ),
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
            vehicle=vehicle, buyer=request.user, admin_user=admin_user, sale=sale
        )
    except Exception as e:
        logger.error(f"Error al enviar email de reserva: {e}")
        # No interrumpir el flujo

    messages.success(
        request,
        f"¡Vehículo reservado! {vehicle.brand.name} {vehicle.model} ha sido reservado.",
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
    sale = Sale.objects.filter(
        vehicle=vehicle, buyer=request.user, status="reserved"
    ).first()
    if sale:
        sale.status = "cancelled"
        sale.save()

    # Liberar vehículo
    vehicle.reserved = False
    vehicle.reserved_by = None
    vehicle.save()

    # Obtener administrador
    admin_user = get_admin_user()

    # Enviar email de cancelación al administrador
    if admin_user:
        try:
            send_admin_cancellation_notification(vehicle, request.user, admin_user)
        except Exception as e:
            logger.error(f"Error al enviar email de cancelación al admin: {e}")
    # Enviar email de cancelación al comprador
    try:
        send_cancellation_notification(vehicle, request.user)
    except Exception as e:
        logger.error(f"Error al enviar email de cancelación al comprador: {e}")

    messages.info(
        request, f"Has cancelado la reserva de {vehicle.brand.name} {vehicle.model}."
    )
    return redirect("vehicles:detail", pk=vehicle_id)


@login_required
def purchase_history(request):
    """Ver historial de compras del usuario."""
    sales = Sale.objects.filter(buyer=request.user).select_related("vehicle", "seller")
    return render(request, "sales/history.html", {"sales": sales})


@login_required
@transaction.atomic
def make_offer(request, vehicle_id):
    vehicle = get_object_or_404(
        Vehicle.objects.select_for_update(),
        id=vehicle_id,
        is_active=True,
        sold=False,
    )

    if vehicle.created_by == request.user:
        messages.error(request, "No puedes hacer una oferta en tu propio vehículo.")
        return redirect("vehicles:detail", pk=vehicle_id)

    # Verificar si ya hay una oferta pendiente
    pending_offer = Sale.objects.filter(vehicle=vehicle, status="offer_pending").first()
    if pending_offer:
        messages.error(request, "Ya hay una oferta pendiente para este vehículo.")
        return redirect("vehicles:detail", pk=vehicle_id)

    # Obtener la última oferta del usuario
    last_offer = (
        Sale.objects.filter(vehicle=vehicle, buyer=request.user)
        .order_by("-created_at")
        .first()
    )

    if request.method == "POST":
        offered_price = request.POST.get("offered_price")
        offer_comment = request.POST.get("offer_comment", "")  # <-- Recoger comentario

        if not offered_price:
            messages.error(request, "Debes ingresar un precio.")
            return redirect("vehicles:detail", pk=vehicle_id)

        try:
            offered_price = Decimal(offered_price)
            if offered_price <= 0:
                raise ValueError
            if offered_price >= vehicle.price:
                messages.error(
                    request, "El precio ofertado debe ser menor al precio publicado."
                )
                return redirect("vehicles:detail", pk=vehicle_id)

            if last_offer and offered_price > last_offer.offered_price:
                messages.error(
                    request,
                    f"Tu nueva oferta no puede ser mayor que tu última oferta de ${last_offer.offered_price}.",
                )
                return redirect("vehicles:detail", pk=vehicle_id)

        except (ValueError, TypeError):
            messages.error(request, "Ingresa un precio válido.")
            return redirect("vehicles:detail", pk=vehicle_id)

        # Crear la oferta con el comentario
        sale = Sale.objects.create(
            vehicle=vehicle,
            buyer=request.user,
            seller=vehicle.created_by,
            amount=vehicle.price,
            offered_price=offered_price,
            status="offer_pending",
            buyer_phone=(
                request.user.profile.phone if hasattr(request.user, "profile") else ""
            ),
            buyer_email=request.user.email,
            notes=offer_comment,  # <-- Guardar comentario aquí
        )

        # Obtener administrador
        admin_user = get_admin_user()

        # Enviar notificaciones
        try:
            send_offer_notifications(vehicle, request.user, admin_user, sale)
        except Exception as e:
            logger.error(f"Error al enviar email de oferta: {e}")

        messages.success(
            request,
            f"¡Oferta enviada! {vehicle.brand.name} {vehicle.model} - Tu oferta de ${offered_price} está en revisión.",
        )
        return redirect("vehicles:detail", pk=vehicle_id)

    return redirect("vehicles:detail", pk=vehicle_id)

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == "admin")


@login_required
@user_passes_test(is_admin)
@transaction.atomic
def accept_offer(request, sale_id):
    sale = get_object_or_404(
        Sale.objects.select_for_update(), id=sale_id, status="offer_pending"
    )
    sale.status = "offer_accepted"
    sale.save()

    vehicle = sale.vehicle
    vehicle.sold = True
    vehicle.is_active = False
    vehicle.reserved = False
    vehicle.reserved_by = None
    vehicle.save()

    try:
        send_offer_accepted_notification(sale)
    except Exception as e:
        logger.error(f"Error al enviar email de aceptación: {e}")

    messages.success(
        request, f"Oferta aceptada para {vehicle.brand.name} {vehicle.model}."
    )
    return redirect("dashboard:offer_list")


@login_required
@user_passes_test(is_admin)
@transaction.atomic
def reject_offer(request, sale_id):
    sale = get_object_or_404(
        Sale.objects.select_for_update(), id=sale_id, status="offer_pending"
    )
    sale.status = "offer_rejected"
    sale.save()

    vehicle = sale.vehicle
    vehicle.reserved = False
    vehicle.reserved_by = None
    vehicle.save()

    try:
        send_offer_rejected_notification(sale)
    except Exception as e:
        logger.error(f"Error al enviar email de rechazo: {e}")

    messages.info(
        request, f"Oferta rechazada para {vehicle.brand.name} {vehicle.model}."
    )
    return redirect("dashboard:offer_list")
