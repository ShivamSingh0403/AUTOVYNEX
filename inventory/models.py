from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from vehicles.models import VehicleVariant


class ProductCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon_name = models.CharField(max_length=50, default='wrench', help_text="Lucide icon name")
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Product Categories'
        ordering = ['sort_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    origin_country = models.CharField(max_length=80, default='India')
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


Category = ProductCategory


class Product(models.Model):
    CONDITION_CHOICES = [
        ('new', 'Brand New (OEM)'),
        ('refurbished', 'Factory Refurbished'),
        ('oem_surplus', 'OEM Surplus'),
    ]

    name = models.CharField(max_length=220)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    sku = models.CharField(max_length=60, unique=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in INR (₹)")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Discounted price if on sale")
    stock_quantity = models.PositiveIntegerField(default=10)
    condition = models.CharField(max_length=30, choices=CONDITION_CHOICES, default='new')
    short_description = models.CharField(max_length=300)
    full_description = models.TextField()
    specifications = models.JSONField(default=dict, blank=True, help_text="Key-value pairs of technical specs")
    warranty_months = models.PositiveIntegerField(default=12, help_text="Warranty period in months")
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_installable = models.BooleanField(default=False, help_text="Eligible for Buy + Professional Installation")
    installation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Installation cost in INR")
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = f"{base_slug}-{slugify(self.sku)}"
        super().save(*args, **kwargs)

    @property
    def final_price(self):
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    @property
    def discount_percent(self):
        if self.discount_price and self.discount_price < self.price:
            savings = self.price - self.discount_price
            return int(round((savings / self.price) * 100))
        return 0

    @property
    def in_stock(self):
        return self.stock_quantity > 0

    def __str__(self):
        return f"{self.name} ({self.sku})"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='products/gallery/')
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductFitment(models.Model):
    FITMENT_STATUS = [
        ('compatible', 'Exact Verified Fit'),
        ('universal', 'Universal Fitment'),
        ('requires_modification', 'Requires Professional Modification'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='fitments')
    variant = models.ForeignKey(VehicleVariant, on_delete=models.CASCADE, related_name='product_fits')
    fitment_status = models.CharField(max_length=30, choices=FITMENT_STATUS, default='compatible')
    notes = models.CharField(max_length=255, blank=True, help_text="Fitment notes e.g., Front axle only")

    class Meta:
        unique_together = ('product', 'variant')
        indexes = [
            models.Index(fields=['product', 'variant']),
        ]

    def __str__(self):
        return f"{self.product.name} -> {self.variant} [{self.fitment_status}]"


class InventoryRecord(models.Model):
    CHANGE_TYPES = [
        ('restock', 'Stock Replenishment'),
        ('sale', 'Customer Order Deducted'),
        ('adjustment', 'Manual Inventory Audit'),
        ('return', 'Order Return Restocked'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_logs')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES)
    quantity = models.IntegerField(help_text="Positive for addition, negative for deduction")
    previous_stock = models.PositiveIntegerField()
    new_stock = models.PositiveIntegerField()
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.sku}: {self.change_type} ({self.quantity}) -> {self.new_stock}"


class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='in_wishlists')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
