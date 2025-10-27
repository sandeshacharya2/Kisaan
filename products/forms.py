from django import forms
from .models import Product
from django.utils.translation import gettext_lazy as _
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['main_category', 'sub_category', 'quantity', 'unit', 'image', 'price', 'description']