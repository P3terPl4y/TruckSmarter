from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Profile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("TruckSmarter", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("TruckSmarter", {"fields": ("email", "role")}),
    )
    list_display = ("username", "email", "role", "is_active", "is_staff")


admin.site.register(Profile)
