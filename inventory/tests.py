from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from inventory.models import ProductCategory, Brand, Product, ProductImage, ProductFitment
from vehicles.models import VehicleMake, VehicleModel, VehicleVariant


class InventoryFilteringAndFitmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat_filters = ProductCategory.objects.create(name='Filters', icon_name='filter')
        self.cat_brakes = ProductCategory.objects.create(name='Braking', icon_name='disc')

        self.brand_bosch = Brand.objects.create(name='Bosch', origin_country='Germany')
        self.brand_brembo = Brand.objects.create(name='Brembo', origin_country='Italy')

        # Product 1: In stock, discount valid
        self.product1 = Product.objects.create(
            name='Bosch High Performance Oil Filter',
            sku='BSH-OIL-001',
            category=self.cat_filters,
            brand=self.brand_bosch,
            price=Decimal('1000.00'),
            discount_price=Decimal('800.00'),
            stock_quantity=20,
            condition='new',
            is_active=True
        )

        # Product 2: In stock, no discount
        self.product2 = Product.objects.create(
            name='Brembo Ceramic Front Brake Pads',
            sku='BRM-BRK-002',
            category=self.cat_brakes,
            brand=self.brand_brembo,
            price=Decimal('4500.00'),
            stock_quantity=10,
            condition='new',
            is_active=True
        )

        # Product 3: Out of stock
        self.product3 = Product.objects.create(
            name='Bosch Premium Fuel Filter',
            sku='BSH-FL-003',
            category=self.cat_filters,
            brand=self.brand_bosch,
            price=Decimal('1200.00'),
            stock_quantity=0,
            condition='new',
            is_active=True
        )

        # Vehicle setup
        self.make = VehicleMake.objects.create(name='Hyundai', country='South Korea')
        self.model = VehicleModel.objects.create(make=self.make, name='Creta', body_type='SUV')
        self.variant = VehicleVariant.objects.create(
            model=self.model,
            name='1.5 SX(O)',
            fuel_type='Petrol',
            transmission='Automatic',
            year_from=2020,
            year_to=2025
        )

        # Fitment: product1 is compatible with variant; product2 has fitment with another variant
        self.other_variant = VehicleVariant.objects.create(
            model=self.model,
            name='1.5 CRDi Diesel',
            fuel_type='Diesel',
            transmission='Manual',
            year_from=2020,
            year_to=2025
        )
        ProductFitment.objects.create(
            product=self.product1,
            variant=self.variant,
            fitment_status='compatible'
        )
        ProductFitment.objects.create(
            product=self.product2,
            variant=self.other_variant,
            fitment_status='compatible'
        )
        # Note: product3 has NO fitment records in DB

    def test_has_valid_discount(self):
        self.assertTrue(self.product1.has_valid_discount)
        self.assertEqual(self.product1.discount_percent, 20)
        self.assertFalse(self.product2.has_valid_discount)

        # Test invalid discount where discount_price >= price
        self.product2.discount_price = Decimal('5000.00')
        self.product2.save()
        self.assertFalse(self.product2.has_valid_discount)

    def test_search_by_keyword(self):
        response = self.client.get(reverse('inventory:shop'), {'q': 'Brembo'})
        self.assertEqual(response.status_code, 200)
        results = response.context['products']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].sku, 'BRM-BRK-002')

    def test_filter_by_category(self):
        response = self.client.get(reverse('inventory:shop'), {'category': self.cat_filters.slug})
        self.assertEqual(response.status_code, 200)
        results = response.context['products']
        self.assertEqual(len(results), 2)

    def test_filter_by_brand(self):
        response = self.client.get(reverse('inventory:shop'), {'brand': 'Bosch'})
        self.assertEqual(response.status_code, 200)
        results = response.context['products']
        self.assertEqual(len(results), 2)

    def test_filter_by_price_range(self):
        response = self.client.get(reverse('inventory:shop'), {'min_price': '2000', 'max_price': '5000'})
        self.assertEqual(response.status_code, 200)
        results = response.context['products']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].sku, 'BRM-BRK-002')

    def test_filter_in_stock_only(self):
        response = self.client.get(reverse('inventory:shop'), {'in_stock': '1'})
        self.assertEqual(response.status_code, 200)
        results = response.context['products']
        self.assertEqual(len(results), 2)
        skus = [p.sku for p in results]
        self.assertNotIn('BSH-FL-003', skus)

    def test_vehicle_fitment_states_in_shop(self):
        session = self.client.session
        session['selected_variant_id'] = self.variant.id
        session.save()

        response = self.client.get(reverse('inventory:shop'))
        self.assertEqual(response.status_code, 200)
        products_map = {p.sku: p.fitment_state for p in response.context['products']}

        # product1 is explicitly compatible
        self.assertEqual(products_map.get('BSH-OIL-001'), 'compatible')
        # product2 has fitments for other cars, not this variant -> incompatible
        self.assertEqual(products_map.get('BRM-BRK-002'), 'incompatible')
        # product3 has 0 fitments in database -> unverified
        self.assertEqual(products_map.get('BSH-FL-003'), 'unverified')

    def test_compatibility_filter(self):
        session = self.client.session
        session['selected_variant_id'] = self.variant.id
        session.save()

        # Filter strictly for compatible
        response = self.client.get(reverse('inventory:shop'), {'compatibility': 'compatible'})
        self.assertEqual(response.status_code, 200)
        results = response.context['products']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].sku, 'BSH-OIL-001')
