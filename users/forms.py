from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Profile, User


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=[
            ("customer", "Usuario"),
            ("seller", "Comerciante"),
        ],
        initial="customer",
        widget=forms.Select,
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "role")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "role", "is_active", "is_staff", "is_superuser")


# ----- ESTE ES EL FORMULARIO QUE DEBES USAR PARA EL PERFIL -----
class ProfileForm(forms.ModelForm):
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    payment_email = forms.EmailField(required=False)
    bank_account = forms.CharField(max_length=100, required=False)
    payment_phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def save(self, commit=True):
        user = super().save(commit=commit)
        profile, created = Profile.objects.get_or_create(user=user)
        profile.phone = self.cleaned_data["phone"]
        profile.address = self.cleaned_data["address"]
        profile.payment_email = self.cleaned_data["payment_email"]
        profile.bank_account = self.cleaned_data["bank_account"]
        profile.payment_phone = self.cleaned_data["payment_phone"]
        if commit:
            profile.save()
        return user
