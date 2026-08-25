from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.analytics_dashboard, name='dashboard'),
    path('vehicle/<int:pk>/', views.vehicle_stats, name='vehicle_stats'),  # <-- NUEVA LÍNEA
]
