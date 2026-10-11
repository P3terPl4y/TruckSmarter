import logging
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from vehicles.models import Vehicle
from .models import VehicleView

logger = logging.getLogger(__name__)


def get_view_cache_key(vehicle_id, request):
    if request.user.is_authenticated:
        identifier = f"user_{request.user.pk}"
    else:
        if not request.session.session_key:
            request.session.create()
        identifier = f"session_{request.session.session_key}"
    return f"vehicle_view_{vehicle_id}_{identifier}"


def has_recent_view(vehicle_id, request):
    try:
        return cache.get(get_view_cache_key(vehicle_id, request)) is not None
    except Exception:
        logger.warning("Caché de visitas no disponible", exc_info=True)
        return False


def mark_view_as_seen(vehicle_id, request):
    try:
        cache.set(
            get_view_cache_key(vehicle_id, request),
            True,
            timeout=settings.VIEW_EXPIRY_SECONDS,
        )
    except Exception:
        logger.warning("No se pudo guardar la visita en caché", exc_info=True)


def record_vehicle_view(vehicle_id, request):
    if has_recent_view(vehicle_id, request):
        return
    identity = (
        {"user_id": request.user.pk}
        if request.user.is_authenticated
        else {"user__isnull": True, "session_key": request.session.session_key}
    )
    since = timezone.now() - timedelta(seconds=settings.VIEW_EXPIRY_SECONDS)
    with transaction.atomic():
        vehicle = Vehicle.objects.select_for_update().get(pk=vehicle_id)
        if not VehicleView.objects.filter(
            vehicle=vehicle, viewed_at__gte=since, **identity
        ).exists():
            VehicleView.objects.create(
                vehicle=vehicle,
                user=request.user if request.user.is_authenticated else None,
                session_key=(
                    None
                    if request.user.is_authenticated
                    else request.session.session_key
                ),
            )
            Vehicle.objects.filter(pk=vehicle_id).update(view_count=F("view_count") + 1)
        transaction.on_commit(lambda: mark_view_as_seen(vehicle_id, request))
