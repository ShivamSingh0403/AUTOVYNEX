from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from inventory.models import ProductCategory, Brand, Product, ProductImage, ProductFitment
from vehicles.models import VehicleMake, VehicleModel, VehicleVariant


class InventoryModelAndFitmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = ProductCategory.objects.create(name='Filters', icon_name='filter')
        self.brand = Brand.objects.create(name='Bosch', origin_country='Germany')
        self.product = Product.objects.create(
            name='Bosch High Performance Oil Filter',
            sku='BSH-OIL-001',
            category=self.category,
            brand=self.brand,
            price=Decimal('799.00'),
            stock_quantity=25,
            condition='new',
            is_active=True
        )
        self.make = VehicleMake.objects.create(name='Honda', country='Japan')
        self.model = VehicleModel.objects.create(make=self.make, name='City', body_type='Sedan')
        self.variant = VehicleVariant.objects.create(
            model=self.model,
            name='1.5 i-VTEC ZX',
            fuel_type='Petrol',
            transmission='Manual',
            year_from=2020,
            year_to=2026
        )
        self.other_variant = VehicleVariant.objects.create(
            model=self.model,
            name='1.5 i-DTEC',
            fuel_type='Diesel',
            transmission='Manual',
            year_from=2020,
            year_to=2026
        )

    def test_product_attributes_and_defaults(self):
        self.assertEqual(self.product.condition, 'new')
        self.assertTrue(self.product.slug)
        self.assertEqual(str(self.product), f"Bosch High Performance Oil Filter ({self.product.sku})")

    def test_product_image_relationship(self):
        img = ProductImage.objects.create(
            product=self.product,
            alt_text='Filter front view',
            is_primary=True
        )
        self.assertEqual(self.product.gallery_images.count(), 1)
        self.assertEqual(self.product.gallery_images.first(), img)

    def test_unverified_compatibility_when_no_fitment_record(self):
        # Product without any ProductFitment record for self.variant
        session = self.client.session
        session['selected_variant_id'] = self.variant.id
        session.save()

        response = self.client.get(reverse('inventory:product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        # Should be unverified because no fitment record exists
        self.assertEqual(response.context['fitment_status'], 'unverified')
        self.assertContains(response, 'Compatibility not verified')

    def test_verified_compatibility_when_fitment_exists(self):
        # Add fitment
        ProductFitment.objects.create(
            product=self.product,
            variant=self.variant,
            fitment_status='compatible'
        )
        session = self.client.session
        session['selected_variant_id'] = self.variant.id
        session.save()

        response = self.client.get(reverse('inventory:product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['fitment_status'], 'compatible')
