# users/validators.py
import re
import dns.resolver
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _



def validate_email_domain(value):
    try:
        domain = value.split('@')[1]
        dns.resolver.resolve(domain, 'MX')
    except (IndexError, dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        raise ValidationError("El dominio del correo electrónico no es válido o no tiene servidores de correo.")
    except dns.resolver.NoNameservers:
        # Dominio sin servidores DNS, probablemente inválido
        raise ValidationError("El dominio del correo electrónico no es válido.")
