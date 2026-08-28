import re
import dns.resolver
from django.conf import settings
from django.core.exceptions import ValidationError

def validate_email_domain(value):
    if '@' not in value:
        raise ValidationError("Correo electrónico inválido.")
    domain = value.split('@')[1]
    if '.' not in domain:
        raise ValidationError("El dominio debe tener un punto (ej: gmail.com)")
    
    # Solo hacer verificación DNS si no estamos en DEBUG (producción)
    if not settings.DEBUG:
        try:
            dns.resolver.resolve(domain, 'MX', lifetime=2)  # timeout 2 segundos
        except Exception:
            # Si falla la resolución DNS, lanzar error solo en producción
            raise ValidationError("El dominio del correo electrónico no es válido o no tiene servidores de correo.")
    # En desarrollo, omitimos la verificación DNS
