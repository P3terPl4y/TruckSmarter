"""Business roles shared by views and services."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def is_admin(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and (user.is_superuser or user.role == "admin")
    )


def is_seller(user):
    return bool(
        is_admin(user)
        or (user and user.is_authenticated and user.is_active and user.role == "seller")
    )


def can_manage_vehicle(user, vehicle):
    return bool(
        is_admin(user)
        or (
            user
            and user.is_authenticated
            and user.is_active
            and vehicle
            and vehicle.created_by_id == user.pk
        )
    )


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("No tienes permisos para acceder a esta sección.")
        return view(request, *args, **kwargs)

    return wrapped
