import logging
from functools import wraps
from .utils import record_vehicle_view

logger = logging.getLogger(__name__)


def track_vehicle_view(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        if (
            request.method == "GET"
            and getattr(response, "status_code", 200) == 200
            and "pk" in kwargs
        ):
            try:
                record_vehicle_view(kwargs["pk"], request)
            except Exception:
                logger.exception(
                    "Error al registrar vista de vehículo %s", kwargs["pk"]
                )
        return response

    return wrapper
