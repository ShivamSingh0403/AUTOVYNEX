from django.db import models
from django.utils.text import slugify


class VehicleMake(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    logo = models.ImageField(upload_to='makes/', blank=True, null=True)
    country = models.CharField(max_length=100, default='India')
    is_popular = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class VehicleModel(models.Model):
    BODY_TYPES = [
        ('Hatchback', 'Hatchback'),
        ('Sedan', 'Sedan'),
        ('SUV', 'SUV / Compact SUV'),
        ('MUV', 'MUV / MPV'),
        ('Coupe', 'Coupe'),
        ('Convertible', 'Convertible'),
    ]

    make = models.ForeignKey(VehicleMake, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    body_type = models.CharField(max_length=50, choices=BODY_TYPES, default='SUV')
    release_year = models.PositiveIntegerField(default=2020)
    is_popular = models.BooleanField(default=True)

    class Meta:
        ordering = ['make__name', 'name']
        unique_together = ('make', 'name')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.make.name}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.make.name} {self.name}"


class VehicleVariant(models.Model):
    FUEL_CHOICES = [
        ('Petrol', 'Petrol'),
        ('Diesel', 'Diesel'),
        ('CNG', 'CNG'),
        ('EV', 'Electric (EV)'),
        ('Hybrid', 'Strong/Mild Hybrid'),
    ]

    TRANSMISSION_CHOICES = [
        ('Manual', 'Manual'),
        ('Automatic', 'Automatic (AT/Torque Converter)'),
        ('DCT', 'Dual Clutch (DCT/DSG)'),
        ('CVT', 'CVT'),
        ('iMT', 'Intelligent Manual (iMT)'),
    ]

    model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=140, blank=True)
    year_from = models.PositiveIntegerField(default=2018)
    year_to = models.PositiveIntegerField(default=2025)
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES, default='Petrol')
    transmission = models.CharField(max_length=30, choices=TRANSMISSION_CHOICES, default='Manual')
    engine_cc = models.PositiveIntegerField(default=1197, help_text="Engine displacement in CC (or equivalent for EV)")
    power_hp = models.PositiveIntegerField(default=88, help_text="Brake Horsepower (BHP/HP)")

    class Meta:
        ordering = ['model__name', '-year_to', 'name']
        unique_together = ('model', 'name', 'fuel_type', 'transmission', 'year_from')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.model.make.name}-{self.model.name}-{self.name}-{self.fuel_type}-{self.year_from}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.model.make.name} {self.model.name} {self.name} ({self.fuel_type}, {self.year_from}-{self.year_to})"

    @property
    def display_name(self):
        return f"{self.model.make.name} {self.model.name} - {self.name} [{self.fuel_type} • {self.transmission} • {self.year_from}-{self.year_to}]"


def __getattr__(name):
    if name == 'CustomerVehicle':
        from garage.models import CustomerVehicle
        return CustomerVehicle
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
