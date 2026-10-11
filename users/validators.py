import dns.resolver
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


def validate_email_domain(value):
    validate_email(value)
    if getattr(settings, "EMAIL_VALIDATE_DNS", not settings.DEBUG):
        try:
            dns.resolver.resolve(value.rsplit("@", 1)[1], "MX", lifetime=2)
        except dns.exception.DNSException as exc:
            raise ValidationError(
                "El dominio del correo no tiene servidores de correo disponibles."
            ) from exc
