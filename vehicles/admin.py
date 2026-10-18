from django.contrib import admin
from .models import VehicleMake, VehicleModel, VehicleVariant


class VehicleModelInline(admin.TabularInline):
    model = VehicleModel
    extra = 1


@admin.register(VehicleMake)
class VehicleMakeAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'is_popular')
    search_fields = ('name',)
    inlines = [VehicleModelInline]


class VehicleVariantInline(admin.TabularInline):
    model = VehicleVariant
    extra = 1


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'make', 'body_type', 'release_year', 'is_popular')
    list_filter = ('make', 'body_type')
    search_fields = ('name', 'make__name')
    inlines = [VehicleVariantInline]


@admin.register(VehicleVariant)
class VehicleVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'model', 'fuel_type', 'transmission', 'year_from', 'year_to', 'engine_cc')
    list_filter = ('fuel_type', 'transmission', 'model__make')
    search_fields = ('name', 'model__name', 'model__make__name')
