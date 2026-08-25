from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg, Max
from django.utils import timezone
from datetime import timedelta
from vehicles.models import Vehicle
from analytics.models import VehicleView
from django.shortcuts import render, get_object_or_404

@staff_member_required  # Solo usuarios staff
def analytics_dashboard(request):
    # 1. Métricas generales
    total_vehicles = Vehicle.objects.count()
    total_views_all = Vehicle.objects.aggregate(total=Sum('view_count'))['total'] or 0
    avg_views = Vehicle.objects.aggregate(avg=Avg('view_count'))['avg'] or 0
    max_views = Vehicle.objects.aggregate(max=Max('view_count'))['max'] or 0
    most_viewed_vehicle = Vehicle.objects.order_by('-view_count').first()
    
    # 2. Vistas por vehículo (ordenadas de mayor a menor)
    vehicles_with_views = Vehicle.objects.filter(view_count__gt=0).order_by('-view_count')
    
    # 3. Vistas en los últimos 7 días (opcional)
    week_ago = timezone.now() - timedelta(days=7)
    views_last_week = VehicleView.objects.filter(viewed_at__gte=week_ago).count()
    
    # 4. Top 5 vehículos más vistos
    top_vehicles = Vehicle.objects.order_by('-view_count')[:5]
    
    context = {
        'total_vehicles': total_vehicles,
        'total_views_all': total_views_all,
        'avg_views': round(avg_views, 2),
        'max_views': max_views,
        'most_viewed_vehicle': most_viewed_vehicle,
        'vehicles_with_views': vehicles_with_views,
        'views_last_week': views_last_week,
        'top_vehicles': top_vehicles,
    }
    return render(request, 'analytics/dashboard.html', context)
@staff_member_required  # Solo personal autorizado (staff)
def dashboard(request):
    # Métricas generales
    total_vehicles = Vehicle.objects.count()
    total_views = VehicleView.objects.count()
    avg_views_per_vehicle = Vehicle.objects.aggregate(avg=Avg('view_count'))['avg'] or 0

    # Top 10 vehículos más vistos
    top_vehicles = Vehicle.objects.order_by('-view_count')[:10]

    context = {
        'total_vehicles': total_vehicles,
        'total_views': total_views,
        'avg_views_per_vehicle': round(avg_views_per_vehicle, 1),
        'top_vehicles': top_vehicles,
    }
    return render(request, 'analytics/dashboard.html', context)

@staff_member_required
def vehicle_detail_stats(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    # Últimas 10 vistas del vehículo
    recent_views = vehicle.views.all().order_by('-viewed_at')[:10]
    context = {
        'vehicle': vehicle,
        'recent_views': recent_views,
    }
    return render(request, 'analytics/vehicle_stats.html', context)
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from vehicles.models import Vehicle

@staff_member_required
def vehicle_stats(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    recent_views = vehicle.views.all().order_by('-viewed_at')[:10]
    context = {
        'vehicle': vehicle,
        'recent_views': recent_views,
    }
    return render(request, 'analytics/vehicle_stats.html', context)
