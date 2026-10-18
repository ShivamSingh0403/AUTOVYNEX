from django.contrib import admin
from .models import ProductCategory, Brand, Product, ProductImage, ProductFitment, InventoryRecord, WishlistItem


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductFitmentInline(admin.TabularInline):
    model = ProductFitment
    extra = 1
    autocomplete_fields = ['variant']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'brand', 'price', 'discount_price', 'stock_quantity', 'condition', 'is_active', 'is_featured')
    list_filter = ('category', 'brand', 'condition', 'is_active', 'is_featured', 'is_installable')
    search_fields = ('name', 'sku', 'brand__name')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductFitmentInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'is_primary', 'alt_text', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('product__name', 'product__sku', 'alt_text')


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon_name', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'origin_country')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductFitment)
class ProductFitmentAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant', 'fitment_status')
    list_filter = ('fitment_status',)
    search_fields = ('product__name', 'variant__name', 'variant__model__name')


@admin.register(InventoryRecord)
class InventoryRecordAdmin(admin.ModelAdmin):
    list_display = ('product', 'change_type', 'quantity', 'previous_stock', 'new_stock', 'created_at')
    list_filter = ('change_type', 'created_at')


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
