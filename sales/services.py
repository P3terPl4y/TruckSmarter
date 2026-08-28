# sales/services.py
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def send_offer_notifications(vehicle, buyer, admin_user, sale):
    # Notificación al comprador
    send_email(
        subject=f"Oferta enviada: {vehicle.brand.name} {vehicle.model}",
        template_name="emails/offer_confirmation.html",
        context={
            "vehicle": {
                "brand": vehicle.brand.name,
                "model": vehicle.model,
                "year": vehicle.year,
            },
            "buyer": {
                "full_name": buyer.get_full_name() or buyer.username,
                "email": buyer.email,
            },
            "offered_price": sale.offered_price,
            "site_name": "TruckSmarter",
        },
        to=[buyer.email],
    )

    # Notificación al admin
    if admin_user:
        send_email(
            subject=f"Nueva oferta: {vehicle.brand.name} {vehicle.model}",
            template_name="emails/admin_offer_notification.html",
            context={
                "vehicle": {
                    "brand": vehicle.brand.name,
                    "model": vehicle.model,
                    "year": vehicle.year,
                },
                "buyer": {
                    "full_name": buyer.get_full_name() or buyer.username,
                    "email": buyer.email,
                },
                "offered_price": sale.offered_price,
                "sale_id": sale.id,
                "site_url": "https://tudominio.com",
            },
            to=[admin_user.email],
        )


def send_offer_accepted_notification(sale):
    send_email(
        subject=f"Oferta aceptada: {sale.vehicle.brand.name} {sale.vehicle.model}",
        template_name="emails/offer_accepted.html",
        context={
            "vehicle": {"brand": sale.vehicle.brand.name, "model": sale.vehicle.model},
            "offered_price": sale.offered_price,
            "site_name": "TruckSmarter",
        },
        to=[sale.buyer.email],
    )


def send_offer_rejected_notification(sale):
    send_email(
        subject=f"Oferta rechazada: {sale.vehicle.brand.name} {sale.vehicle.model}",
        template_name="emails/offer_rejected.html",
        context={
            "vehicle": {"brand": sale.vehicle.brand.name, "model": sale.vehicle.model},
            "offered_price": sale.offered_price,
            "site_name": "TruckSmarter",
        },
        to=[sale.buyer.email],
    )


def send_reservation_notifications(vehicle, buyer, admin_user, sale):
    """
    Envía email de confirmación al comprador y notificación al administrador.
    """
    # Datos del vehículo
    vehicle_details = {
        "brand": vehicle.brand.name,
        "model": vehicle.model,
        "year": vehicle.year,
        "price": vehicle.price,
        "description": vehicle.description[:200],
    }

    # Datos del comprador
    buyer_details = {
        "full_name": buyer.get_full_name() or buyer.username,
        "email": buyer.email,
        "phone": (
            buyer.profile.phone if hasattr(buyer, "profile") else "No especificado"
        ),
        "address": (
            buyer.profile.address if hasattr(buyer, "profile") else "No especificada"
        ),
    }

    context = {
        "vehicle": vehicle_details,
        "buyer": buyer_details,
        "sale_id": sale.id,
        "sale_amount": sale.amount,
        "sale_date": sale.created_at,
        "site_name": "TruckSmarter",
        "site_url": "https://tudominio.com",  # Cambiar por tu dominio
    }
    # 1. Email para el administrador (notificación de nueva reserva)
    if admin_user:
        send_email(
            subject=f'Nueva reserva: {vehicle_details["brand"]} {vehicle_details["model"]}',
            template_name="emails/admin_reservation_notification.html",
            context=context,
            to=[admin_user.email],
            from_email=settings.DEFAULT_FROM_EMAIL,
        )
    # 2. Email para el comprador (confirmación de reserva)
    send_email(
        subject=f'Reserva confirmada: {vehicle_details["brand"]} {vehicle_details["model"]}',
        template_name="emails/reservation_confirmation.html",
        context=context,
        to=[buyer.email],
        from_email=settings.DEFAULT_FROM_EMAIL,
    )


def send_email(subject, template_name, context, to, from_email=None):
    """
    Función auxiliar para enviar emails con plantillas HTML y texto plano.
    """
    try:
        # Renderizar HTML
        html_message = render_to_string(template_name, context)
        # Crear versión texto plano (para clientes que no soportan HTML)
        plain_message = strip_tags(html_message)

        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=to,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email enviado a {', '.join(to)}: {subject}")
    except Exception as e:
        logger.error(f"Error al enviar email a {', '.join(to)}: {str(e)}")
        # No lanzamos excepción para no interrumpir la compra


def send_cancellation_notification(vehicle, user):
    context = {
        "vehicle": {
            "brand": vehicle.brand.name,
            "model": vehicle.model,
            "year": vehicle.year,
        },
        "user": {
            "full_name": user.get_full_name() or user.username,
            "email": user.email,
        },
        "site_name": "TruckSmarter",
        "site_url": "https://tudominio.com",
    }
    send_email(
        subject=f"Reserva cancelada: {vehicle.brand.name} {vehicle.model}",
        template_name="emails/reservation_cancelled.html",
        context=context,
        to=[user.email],
        from_email=settings.DEFAULT_FROM_EMAIL,
    )


def send_admin_cancellation_notification(vehicle, user, admin_user):
    context = {
        "vehicle": {
            "brand": vehicle.brand.name,
            "model": vehicle.model,
            "year": vehicle.year,
        },
        "user": {
            "full_name": user.get_full_name() or user.username,
            "email": user.email,
        },
        "site_name": "TruckSmarter",
        "site_url": "https://tudominio.com",
    }
    send_email(
        subject=f"Reserva cancelada por {user.get_full_name() or user.username}: {vehicle.brand.name} {vehicle.model}",
        template_name="emails/admin_reservation_cancelled.html",
        context=context,
        to=[admin_user.email],
        from_email=settings.DEFAULT_FROM_EMAIL,
    )
