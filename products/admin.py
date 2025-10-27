# products/admin.py
from django.contrib import admin
from .models import Product, ProductSynonym

class ProductSynonymInline(admin.TabularInline):
    model = ProductSynonym
    extra = 1
    fields = ['language', 'synonym']
    verbose_name = "Synonym"
    verbose_name_plural = "Synonyms"

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'sub_category',
        'main_category',
        'farmer',
        'quantity',
        'unit',
        'price',
        'date_posted'
    ]
    list_filter = ['main_category', 'farmer', 'date_posted']
    search_fields = [
        'sub_category',
        'description',
        'productsynonym__synonym'  # ✅ Search by synonyms too!
    ]
    inlines = [ProductSynonymInline]  # ✅ This lets admin add synonyms on product page

# Also register ProductSynonym so it can be managed separately if needed
admin.site.register(ProductSynonym)