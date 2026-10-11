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
        validators=[validate_email_domain],
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


class UserAdminCreationForm(UserCreationForm):
    email = forms.EmailField(validators=[validate_email_domain])

    class Meta:
        model = User
        fields = ("username", "email", "role", "is_active")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return email


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "role", "is_active", "is_staff", "is_superuser")

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not actor or not actor.is_superuser:
            self.fields.pop("is_staff")
            self.fields.pop("is_superuser")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if (
            User.objects.filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise ValidationError("Este correo electrónico ya está registrado.")
        return email


class ProfileForm(forms.ModelForm):
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    payment_email = forms.EmailField(required=False, validators=[validate_email_domain])
    bank_account = forms.CharField(max_length=100, required=False)
    payment_phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            profile = Profile.objects.filter(user=self.instance).first()
            if profile:
                for name in (
                    "phone",
                    "address",
                    "payment_email",
                    "bank_account",
                    "payment_phone",
                ):
                    self.initial[name] = getattr(profile, name)

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
        from django.db import transaction
        from .models import EmailVerification

        user = super().save(commit=False)
        if commit:
            with transaction.atomic():
                user.save()
                profile, _ = Profile.objects.get_or_create(user=user)
                for name in (
                    "phone",
                    "address",
                    "payment_email",
                    "bank_account",
                    "payment_phone",
                ):
                    setattr(profile, name, self.cleaned_data[name])
                profile.save()
                EmailVerification.objects.filter(user=user).exclude(
                    email__iexact=user.email
                ).delete()
        return user
