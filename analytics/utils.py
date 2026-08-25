from datetime import timedelta
from django.utils import timezone
from .models import VehicleView
from django.core.cache import cache
from django.conf import settings

def has_recent_view(vehicle, request, hours=24):
    """
    Retorna True si ya existe una vista para este vehículo
    con la misma sesión o usuario en las últimas 'hours' horas.
    """
    now = timezone.now()
    since = now - timedelta(hours=hours)

    # Construir filtro base
    filter_kwargs = {
        'vehicle': vehicle,
        'viewed_at__gte': since,
    }

    # Si el usuario está autenticado, usamos el usuario
    if request.user.is_authenticated:
        filter_kwargs['user'] = request.user
    # Si no, usamos la session_key
    elif request.session.session_key:
        filter_kwargs['session_key'] = request.session.session_key
    else:
        # Si no hay ni usuario ni sesión, no podemos evitar duplicados
        return False

    return VehicleView.objects.filter(**filter_kwargs).exists()

VIEW_EXPIRY_SECONDS = getattr(settings, 'VIEW_EXPIRY_SECONDS', 86400)  # 24h por defecto

def get_view_cache_key(vehicle_id, request):
    """Genera una clave única para cachear la vista de un vehículo por usuario/sesión."""
    if request.user.is_authenticated:
        identifier = f"user_{request.user.id}"
    elif request.session.session_key:
        identifier = f"session_{request.session.session_key}"
    else:
        identifier = f"ip_{request.META.get('REMOTE_ADDR', '0.0.0.0')}"
    return f"vehicle_view_{vehicle_id}_{identifier}"

def has_recent_view(vehicle_id, request):
    """Retorna True si ya existe un registro en cache para este vehículo/usuario."""
    key = get_view_cache_key(vehicle_id, request)
    return cache.get(key) is not None

def mark_view_as_seen(vehicle_id, request):
    """Marca en cache que este usuario ha visto el vehículo."""
    key = get_view_cache_key(vehicle_id, request)
    cache.set(key, True, timeout=VIEW_EXPIRY_SECONDS)
