# sales/services.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_purchase_notifications(vehicle, buyer, seller, sale):
    """
    Envía emails de confirmación al comprador y al vendedor después de una compra.
    
    Args:
        vehicle: Objeto Vehicle vendido
        buyer: Objeto User comprador
        seller: Objeto User vendedor
        sale: Objeto Sale creado
    """
    
    # Datos del vehículo
    vehicle_details = {
        'brand': vehicle.brand.name,
        'model': vehicle.model,
        'year': vehicle.year,
        'price': vehicle.price,
        'description': vehicle.description[:200],  # Resumen
    }
    
    # Datos del comprador (para el vendedor)
    buyer_details = {
        'full_name': buyer.get_full_name() or buyer.username,
        'email': buyer.email,
        'phone': buyer.profile.phone if hasattr(buyer, 'profile') else 'No especificado',
        'address': buyer.profile.address if hasattr(buyer, 'profile') else 'No especificada',
    }
    
    # Datos del vendedor (para el comprador)
    seller_details = {
        'full_name': seller.get_full_name() or seller.username,
        'email': seller.email,
        'phone': seller.profile.phone if hasattr(seller, 'profile') else 'No especificado',
        'address': seller.profile.address if hasattr(seller, 'profile') else 'No especificada',
    }
    
    context = {
        'vehicle': vehicle_details,
        'buyer': buyer_details,
        'seller': seller_details,
        'sale_id': sale.id,
        'sale_amount': sale.amount,
        'sale_date': sale.created_at,
        'site_name': 'TruckSmarter',
        'site_url': 'http://localhost:8000',  # En producción, usar variable de entorno
    }
    
    # 1. Email para el comprador (confirmación)
    send_email(
        subject=f'¡Compra confirmada! Has comprado {vehicle_details["brand"]} {vehicle_details["model"]}',
        template_name='emails/purchase_confirmation.html',
        context=context,
        to=[buyer.email],
        from_email=settings.DEFAULT_FROM_EMAIL,
    )
    
    # 2. Email para el vendedor (notificación de venta)
    send_email(
        subject=f'¡Tu vehículo ha sido vendido! {vehicle_details["brand"]} {vehicle_details["model"]}',
        template_name='emails/sale_notification.html',
        context=context,
        to=[seller.email],
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
