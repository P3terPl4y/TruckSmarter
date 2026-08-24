from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('admin/users/', views.UserListView.as_view(), name='admin_list'),
    path('admin/users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='admin_edit'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
	path('change-role/', views.ChangeRoleView.as_view(), name='change_role'),
]
