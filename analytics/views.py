from django.db.models import Avg, Max, Sum
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from datetime import timedelta

from core.permissions import admin_required
from vehicles.models import Vehicle
from .models import VehicleView


@admin_required
def analytics_dashboard(request):
    metrics = Vehicle.objects.aggregate(
        total_views=Sum("view_count"),
        avg_views=Avg("view_count"),
        max_views=Max("view_count"),
    )
    total_views = metrics["total_views"] or 0
    average = round(metrics["avg_views"] or 0, 2)
    top = list(
        Vehicle.objects.select_related("brand").order_by("-view_count", "-pk")[:10]
    )
    context = {
        "total_vehicles": Vehicle.objects.count(),
        "total_views": total_views,
        "total_views_all": total_views,
        "avg_views_per_vehicle": average,
        "avg_views": average,
        "max_views": metrics["max_views"] or 0,
        "top_vehicles": top,
        "most_viewed_vehicle": top[0] if top else None,
        "views_last_week": VehicleView.objects.filter(
            viewed_at__gte=timezone.now() - timedelta(days=7)
        ).count(),
    }
    return render(request, "analytics/dashboard.html", context)


@admin_required
def vehicle_stats(request, pk):
    vehicle = get_object_or_404(Vehicle.objects.select_related("brand"), pk=pk)
    recent_views = vehicle.views.select_related("user").order_by("-viewed_at", "-pk")[
        :10
    ]
    return render(
        request,
        "analytics/vehicle_stats.html",
        {"vehicle": vehicle, "recent_views": recent_views},
    )
