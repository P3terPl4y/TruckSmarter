from django import forms


class OfferForm(forms.Form):
    offered_price = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    offer_comment = forms.CharField(
        required=False, max_length=650, widget=forms.Textarea
    )
