from django import forms

from .models import Brand, Vehicle, VehicleImage


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "brand",
            "model",
            "year",
            "price",
            "mileage",
            "transmission",
            "fuel_type",
            "status",
            "description",
            "main_image",
            "is_active",
        ]
        labels = {
            "brand": "Marca",
            "model": "Modelo",
            "year": "Año",
            "price": "Precio",
            "mileage": "Kilometraje",
            "transmission": "Transmisión",
            "fuel_type": "Tipo de combustible",
            "status": "Estado",
            "description": "Descripción",
            "main_image": "Imagen principal",
            "is_active": "Activo",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class VehicleImageForm(forms.ModelForm):
    class Meta:
        model = VehicleImage
        fields = ["image", "is_primary"]


class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ["name", "logo"]
