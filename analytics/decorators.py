from functools import wraps
from django.db import transaction
from django.db.models import F
from django.core.exceptions import ObjectDoesNotExist
import logging
from .models import VehicleView
from .utils import has_recent_view, mark_view_as_seen

logger = logging.getLogger(__name__)

def track_vehicle_view(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 1. Obtener el vehículo (desde kwargs o desde el contexto de la vista)
        vehicle = None
        if 'pk' in kwargs:
            from vehicles.models import Vehicle
            try:
                vehicle = Vehicle.objects.get(pk=kwargs['pk'])
            except Vehicle.DoesNotExist:
                pass

        # Si no hay vehículo, continuar sin registrar
        if not vehicle:
            return view_func(request, *args, **kwargs)

        # 2. Excluir bots si usas django-user-agents
        # from user_agents import parse
        # if parse(request.META.get('HTTP_USER_AGENT', '')).is_bot:
        #     return view_func(request, *args, **kwargs)

        # 3. Verificar cache antes de consultar DB
        if not has_recent_view(vehicle.id, request):
            try:
                # 4. Transacción atómica: crear registro y actualizar contador
                with transaction.atomic():
                    VehicleView.objects.create(
                        vehicle=vehicle,
                        user=request.user if request.user.is_authenticated else None,
                        session_key=request.session.session_key if not request.user.is_authenticated else None,
                    )
                    # Usar F() para actualizar sin race conditions
                    Vehicle.objects.filter(pk=vehicle.pk).update(view_count=F('view_count') + 1)

                # 5. Marcar en cache para futuras visitas
                mark_view_as_seen(vehicle.id, request)

            except Exception as e:
                # Registrar error pero no interrumpir la respuesta
                logger.error(f"Error al registrar vista para vehículo {vehicle.id}: {e}")

        # 6. Pasar el vehículo al contexto de la vista (opcional)
        # Si la vista es una DetailView, ya tiene el objeto
        response = view_func(request, *args, **kwargs)
        return response

    return wrapper
