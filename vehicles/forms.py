from django import forms

from .models import Vehicle, VehicleImage,Brand


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
