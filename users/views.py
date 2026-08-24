from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.views.generic import ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from .froms import CustomUserCreationForm, UserAdminForm

User = get_user_model()

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registro exitoso. Bienvenido!')
            return redirect('vehicles:list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/register.html', {'form': form})

class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = 'users/admin/user_list.html'
    context_object_name = 'users'
    permission_required = 'users.can_manage_users'

class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = User
    form_class = UserAdminForm
    template_name = 'users/admin/user_form.html'
    permission_required = 'users.can_manage_users'
    success_url = reverse_lazy('users:admin_list')