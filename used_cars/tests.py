from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from used_cars.models import UsedCarListing, CarValuationRecord


class UsedCarsAndValuationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='seller1', email='seller@example.com', password='Password@123')

    def test_used_car_listing_creation(self):
        listing = UsedCarListing.objects.create(
            seller=self.user,
            title='2021 Hyundai Creta SX(O) Turbo Petrol',
            make_name='Hyundai',
            model_name='Creta',
            variant_name='1.4 Turbo SX(O) 7DCT',
            year=2021,
            fuel_type='Petrol',
            transmission='Automatic',
            mileage=32000,
            location_city='Bengaluru',
            registration_state='Karnataka (KA)',
            expected_price=Decimal('1475000.00'),
            description='Single owner, showroom maintained',
            is_verified=True
        )
        self.assertEqual(str(listing), f"2021 Hyundai Creta 1.4 Turbo SX(O) 7DCT (₹{listing.expected_price:,.0f})")
        self.assertTrue(listing.is_verified)

    def test_car_valuation_endpoint_and_record_persistence(self):
        response = self.client.post(reverse('core:car_valuation'), {
            'make_name': 'Hyundai',
            'model_name': 'Creta',
            'year': 2021,
            'fuel_type': 'Petrol',
            'transmission': 'Automatic',
            'condition': 'excellent',
            'mileage': 35000,
            'original_price': 1600000
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estimated Fair Market Value')
        # Check disclaimer notice
        self.assertContains(response, 'estimate rather than guaranteed market price')

        # Check database persistence
        records = CarValuationRecord.objects.filter(make_name='Hyundai', model_name='Creta', year=2021)
        self.assertEqual(records.count(), 1)
        record = records.first()
        self.assertGreater(record.estimated_price_min, 0)
        self.assertTrue(record.is_estimate_only)
