from django.contrib import admin
from .models import Order, OrderItem, CartItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'product_sku', 'unit_price', 'quantity', 'total_price', 'buy_and_install', 'installation_fee')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'full_name', 'total_amount', 'status', 'payment_method', 'created_at', 'is_simulated')
    list_filter = ('status', 'payment_method', 'created_at', 'is_simulated')
    search_fields = ('order_number', 'full_name', 'email', 'phone', 'tracking_number')
    inlines = [OrderItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'user', 'product', 'quantity', 'buy_and_install', 'created_at')
