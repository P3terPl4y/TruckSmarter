import re

import dns.resolver
from django.core.exceptions import ValidationError


def validate_email_domain(value):
    try:
        domain = value.split("@")[1]
        dns.resolver.resolve(domain, "MX")
    except (IndexError, dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        raise ValidationError(
            "El dominio del correo electrónico no es válido o no tiene servidores de correo."
        )
    except dns.resolver.NoNameservers:
        raise ValidationError("El dominio del correo electrónico no es válido.")
