from django.urls import path

from . import views, api

app_name = "users"

urlpatterns = [
    path("api/token/", api.issue_token, name="api_token"),
    path("api/me/", api.current_user, name="api_me"),
    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("admin/users/", views.UserListView.as_view(), name="admin_list"),
    path(
        "admin/users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="admin_edit"
    ),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("verify/<uuid:token>/", views.verify_email, name="verify_email"),
]
