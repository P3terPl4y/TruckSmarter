from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect

from .models import Brand, Vehicle, VehicleImage


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """Use the same transactional editor from both administration interfaces."""

    list_display = ("model", "brand", "year", "price", "is_active", "sold", "reserved")
    list_select_related = ("brand",)
    actions = None

    def add_view(self, request, form_url="", extra_context=None):
        if not self.has_add_permission(request):
            raise PermissionDenied
        return redirect("vehicles:create")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        vehicle = self.get_object(request, object_id)
        if vehicle is None:
            raise Http404
        if not self.has_change_permission(request, vehicle):
            raise PermissionDenied
        return redirect(
            "vehicles:detail" if vehicle.sold else "vehicles:update", pk=vehicle.pk
        )

    def delete_view(self, request, object_id, extra_context=None):
        vehicle = self.get_object(request, object_id)
        if vehicle is None:
            raise Http404
        if not self.has_delete_permission(request, vehicle):
            raise PermissionDenied
        return redirect("vehicles:delete", pk=vehicle.pk)


admin.site.register(Brand)
admin.site.register(VehicleImage)
