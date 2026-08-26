from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    path("reserve/<int:vehicle_id>/", views.reserve_vehicle, name="reserve"),
    path('cancel-reservation/<int:vehicle_id>/', views.cancel_reservation, name='cancel_reservation'),
    path("history/", views.purchase_history, name="history"),
]
