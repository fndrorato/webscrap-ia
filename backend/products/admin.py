from django.contrib import admin
from configurations.models import Configuration
from sites.models import Site
from products.models import Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ['image', 'original_url', 'created_at']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'site', 'status', 'has_images', 'created_at']
    list_filter = ['status', 'site', 'created_at']
    search_fields = ['name', 'description', 'search_query']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProductImageInline]
    
    def has_images(self, obj):
        return bool(obj.main_image or obj.images.exists())
    has_images.boolean = True
    has_images.short_description = 'Tem Imagens'