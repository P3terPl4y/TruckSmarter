from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('purchase/<int:vehicle_id>/', views.purchase_vehicle, name='purchase'),
]
