from django import forms

class EsewaForm(forms.Form):
    amount = forms.DecimalField(label="Amount (NPR)", min_value=1, decimal_places=2)
