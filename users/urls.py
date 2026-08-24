from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('admin/users/', views.UserListView.as_view(), name='admin_list'),
    path('admin/users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='admin_edit'),
]