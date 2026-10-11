# dashboard/urls.py
from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/create/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_update"),
    path(
        "users/<int:pk>/password/",
        views.UserPasswordChangeView.as_view(),
        name="user_password",
    ),
    path("users/<int:pk>/delete/", views.UserDeleteView.as_view(), name="user_delete"),
    path("brands/", views.BrandListView.as_view(), name="brand_list"),
    path("brands/create/", views.BrandCreateView.as_view(), name="brand_create"),
    path("brands/<int:pk>/edit/", views.BrandUpdateView.as_view(), name="brand_update"),
    path(
        "brands/<int:pk>/delete/", views.BrandDeleteView.as_view(), name="brand_delete"
    ),
    path("offers/", views.OfferListView.as_view(), name="offer_list"),
]
