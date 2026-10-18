from django.db import models
from django.contrib.auth.models import User
from inventory.models import Product
import uuid


class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items')
    session_key = models.CharField(max_length=64, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_entries')
    quantity = models.PositiveIntegerField(default=1)
    buy_and_install = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def unit_price(self):
        return self.product.final_price

    @property
    def item_subtotal(self):
        base = self.unit_price * self.quantity
        if self.buy_and_install and self.product.is_installable:
            base += self.product.installation_fee * self.quantity
        return base

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Session: {self.session_key[:8]})"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Order Confirmed'),
        ('processing', 'Processing & Packing'),
        ('shipped', 'Shipped via Express Logistics'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHODS = [
        ('simulated_card', 'Credit/Debit Card (Demonstration Simulation)'),
        ('simulated_upi', 'UPI / QR Code (Demonstration Simulation)'),
        ('simulated_netbanking', 'Net Banking (Demonstration Simulation)'),
        ('cod', 'Cash on Delivery (Verified Demo)'),
    ]

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='confirmed')
    
    # Customer Details
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    shipping_address = models.TextField()
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    pincode = models.CharField(max_length=10)

    # Order Totals in INR
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    installation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='simulated_upi')
    payment_status = models.CharField(max_length=30, default='Simulated Payment Success')
    is_simulated = models.BooleanField(default=True, help_text="Order and payment are simulated for project demo")
    tracking_courier = models.CharField(max_length=80, default='AUTOVYNEX Express Fleet')
    tracking_number = models.CharField(max_length=40, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"AVX-ORD-{uuid.uuid4().hex[:8].upper()}"
        if not self.tracking_number:
            self.tracking_number = f"AVXTRK{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} by {self.full_name} (₹{self.total_amount})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    product_name = models.CharField(max_length=220)
    product_sku = models.CharField(max_length=60)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    buy_and_install = models.BooleanField(default=False)
    installation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.quantity}x {self.product_name} in {self.order.order_number}"
