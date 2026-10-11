"""Atomic business transitions. All operations lock Vehicle before touching Sale."""

import logging

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from core.permissions import is_admin
from vehicles.models import Vehicle
from .models import Sale
from . import services

logger = logging.getLogger(__name__)


def after_commit(callback, *args, **kwargs):
    def send():
        try:
            callback(*args, **kwargs)
        except Exception:
            logger.exception("No se pudo enviar la notificación comercial")

    transaction.on_commit(send)


def locked_vehicle(pk, **filters):
    return get_object_or_404(Vehicle.objects.select_for_update(), pk=pk, **filters)


def contact(user):
    return {
        "buyer_email": user.email,
        "buyer_phone": getattr(getattr(user, "profile", None), "phone", ""),
    }


def get_admin_user():
    from django.contrib.auth import get_user_model

    users = get_user_model().objects.filter(is_active=True)
    return (
        users.filter(is_superuser=True).order_by("pk").first()
        or users.filter(role="admin").order_by("pk").first()
    )


def close_alternatives(vehicle, excluded=None, pending_status="offer_rejected"):
    alternatives = Sale.objects.filter(vehicle=vehicle).exclude(pk=excluded)
    offers = list(alternatives.filter(status="offer_pending"))
    reservations = list(alternatives.filter(status="reserved"))
    alternatives.filter(status="offer_pending").update(
        status=pending_status, updated_at=timezone.now()
    )
    alternatives.filter(status="reserved").update(
        status="cancelled", updated_at=timezone.now()
    )
    for offer in offers:
        after_commit(services.send_offer_rejected_notification, offer)
    for reservation in reservations:
        after_commit(
            services.send_cancellation_notification, vehicle, reservation.buyer
        )


@transaction.atomic
def create_offer(pk, buyer, price, comment=""):
    vehicle = locked_vehicle(
        pk, is_active=True, sold=False, reserved=False, created_by__isnull=False
    )
    if vehicle.created_by_id == buyer.pk:
        raise ValueError("No puedes hacer una oferta en tu propio vehículo.")
    if Sale.objects.filter(
        vehicle=vehicle, buyer=buyer, status="offer_pending"
    ).exists():
        raise ValueError("Ya tienes una oferta pendiente para este vehículo.")
    if (
        not price.is_finite()
        or price <= 0
        or price >= vehicle.price
        or price.as_tuple().exponent < -2
        or len(comment) > 650
    ):
        raise ValueError(
            "La oferta debe ser positiva, tener hasta dos decimales y ser menor al precio publicado."
        )
    last = (
        Sale.objects.filter(vehicle=vehicle, buyer=buyer, offered_price__isnull=False)
        .order_by("-created_at", "-pk")
        .first()
    )
    if last and price > last.offered_price:
        raise ValueError("Tu nueva oferta no puede ser mayor que tu última oferta.")
    sale = Sale.objects.create(
        vehicle=vehicle,
        buyer=buyer,
        seller=vehicle.created_by,
        amount=vehicle.price,
        offered_price=price,
        notes=comment,
        **contact(buyer),
    )
    after_commit(
        services.send_offer_notifications, vehicle, buyer, vehicle.created_by, sale
    )
    return sale


@transaction.atomic
def reserve(pk, buyer):
    vehicle = locked_vehicle(
        pk, is_active=True, sold=False, reserved=False, created_by__isnull=False
    )
    if vehicle.created_by_id == buyer.pk:
        raise ValueError("No puedes reservar tu propio vehículo.")
    sale = Sale.objects.create(
        vehicle=vehicle,
        buyer=buyer,
        seller=vehicle.created_by,
        amount=vehicle.price,
        status="reserved",
        **contact(buyer),
    )
    vehicle.reserved = True
    vehicle.reserved_by = buyer
    vehicle.save(update_fields=["reserved", "reserved_by", "updated_at"])
    after_commit(
        services.send_reservation_notifications, vehicle, buyer, get_admin_user(), sale
    )
    return sale


@transaction.atomic
def cancel_reservation(pk, buyer):
    vehicle = locked_vehicle(pk, reserved=True, reserved_by=buyer, sold=False)
    Sale.objects.filter(vehicle=vehicle, buyer=buyer, status="reserved").update(
        status="cancelled", updated_at=timezone.now()
    )
    vehicle.reserved = False
    vehicle.reserved_by = None
    vehicle.save(update_fields=["reserved", "reserved_by", "updated_at"])
    after_commit(services.send_cancellation_notification, vehicle, buyer)
    admin = get_admin_user()
    if admin:
        after_commit(
            services.send_admin_cancellation_notification, vehicle, buyer, admin
        )


@transaction.atomic
def decide_offer(pk, actor, accept):
    if not is_admin(actor):
        raise PermissionDenied
    vehicle_id = get_object_or_404(Sale, pk=pk).vehicle_id
    vehicle = locked_vehicle(vehicle_id, sold=False, is_active=True)
    sale = get_object_or_404(
        Sale.objects.select_for_update(), pk=pk, status="offer_pending"
    )
    sale.status = "offer_accepted" if accept else "offer_rejected"
    sale.save(update_fields=["status", "updated_at"])
    if accept:
        close_alternatives(vehicle, excluded=sale.pk)
        vehicle.sold = True
        vehicle.is_active = False
        vehicle.reserved = False
        vehicle.reserved_by = None
        vehicle.save(
            update_fields=["sold", "is_active", "reserved", "reserved_by", "updated_at"]
        )
    after_commit(
        (
            services.send_offer_accepted_notification
            if accept
            else services.send_offer_rejected_notification
        ),
        sale,
    )
    return sale


@transaction.atomic
def complete_purchase(pk, buyer):
    vehicle = locked_vehicle(pk)
    if not vehicle.is_active or vehicle.sold or vehicle.created_by_id is None:
        raise ValueError("El vehículo no está disponible para la compra.")
    if vehicle.created_by_id == buyer.pk or (
        vehicle.reserved and vehicle.reserved_by_id != buyer.pk
    ):
        raise ValueError("El comprador no puede adquirir este vehículo.")
    close_alternatives(vehicle)
    sale = Sale.objects.create(
        vehicle=vehicle,
        buyer=buyer,
        seller=vehicle.created_by,
        amount=vehicle.price,
        status="completed",
        **contact(buyer),
    )
    vehicle.sold = True
    vehicle.is_active = False
    vehicle.reserved = False
    vehicle.reserved_by = None
    vehicle.save(
        update_fields=["sold", "is_active", "reserved", "reserved_by", "updated_at"]
    )
    return sale


@transaction.atomic
def withdraw_listing(pk):
    vehicle = locked_vehicle(pk)
    if vehicle.sold:
        raise ValueError("No puedes retirar un vehículo vendido.")
    close_alternatives(vehicle, pending_status="cancelled")
    vehicle.is_active = False
    vehicle.reserved = False
    vehicle.reserved_by = None
    vehicle.save(update_fields=["is_active", "reserved", "reserved_by", "updated_at"])


@transaction.atomic
def update_listing(pk, values):
    vehicle = locked_vehicle(pk)
    if vehicle.sold:
        raise ValueError("No puedes editar un vehículo vendido.")
    if vehicle.reserved and values.get("price", vehicle.price) != vehicle.price:
        raise ValueError("Cancela la reserva antes de modificar el precio.")
    if not values.get("is_active", vehicle.is_active):
        withdraw_listing(pk)
        vehicle.refresh_from_db()
    for key, value in values.items():
        if key in (
            "brand",
            "model",
            "year",
            "price",
            "mileage",
            "transmission",
            "fuel_type",
            "status",
            "description",
            "main_image",
            "is_active",
        ):
            setattr(vehicle, key, value)
    vehicle.full_clean()
    vehicle.save()
    return vehicle
