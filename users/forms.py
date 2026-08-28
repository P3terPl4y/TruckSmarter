from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Profile, User
from .services import verify_email_api
from .validators import validate_email_domain


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
        validators=[validate_email_domain],  # <-- Agregar validador
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not verify_email_api(email):
            raise ValidationError("El correo electrónico no parece ser válido.")
        if email:
            email = email.lower()  # Normalizar a minúsculas
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError("Este correo electrónico ya está registrado.")
        return email

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
    payment_email = forms.EmailField(required=False, validators=[validate_email_domain])
    bank_account = forms.CharField(max_length=100, required=False)
    payment_phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not verify_email_api(email):
            raise ValidationError("El correo electrónico no parece ser válido.")
        if email:
            email = email.lower()
            # Excluir al propio usuario de la consulta (cuando se edita)
            if self.instance and self.instance.pk:
                if (
                    User.objects.filter(email__iexact=email)
                    .exclude(pk=self.instance.pk)
                    .exists()
                ):
                    raise ValidationError(
                        "Este correo electrónico ya está registrado por otro usuario."
                    )
            else:
                # Caso de creación (aunque no se usa aquí)
                if User.objects.filter(email__iexact=email).exists():
                    raise ValidationError("Este correo electrónico ya está registrado.")
        return email

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
