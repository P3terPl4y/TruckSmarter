from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
	path('offer/<int:vehicle_id>/', views.make_offer, name='make_offer'),
    path("reserve/<int:vehicle_id>/", views.reserve_vehicle, name="reserve"),
    path('cancel-reservation/<int:vehicle_id>/', views.cancel_reservation, name='cancel_reservation'),
    path("history/", views.purchase_history, name="history"),
    path('accept-offer/<int:sale_id>/', views.accept_offer, name='accept_offer'),   # <-- Agregar
    path('reject-offer/<int:sale_id>/', views.reject_offer, name='reject_offer'), 
]
