from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_vehicle_year(value):
    if not 1886 <= value <= timezone.now().year + 1:
        raise ValidationError("El año debe estar entre 1886 y el próximo año.")


def validate_image_size(value):
    if getattr(value, "_committed", False):
        return
    if value.size > getattr(settings, "MAX_IMAGE_UPLOAD_BYTES", 5 * 1024 * 1024):
        raise ValidationError("La imagen no puede superar los 5 MB.")
