from django.utils.decorators import method_decorator

from .decorators import track_vehicle_view


class TrackVehicleViewMixin:
    """
    Mixin para agregar a una DetailView de Vehicle.
    Registra automáticamente la vista del vehículo.
    """

    @method_decorator(track_vehicle_view)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
