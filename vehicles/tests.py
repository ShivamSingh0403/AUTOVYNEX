from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from vehicles.models import VehicleMake, VehicleModel, VehicleVariant
from accounts.models import CustomerProfile


class VehicleCascadeAndSelectionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.make = VehicleMake.objects.create(name='Maruti Suzuki', country='India')
        self.model = VehicleModel.objects.create(make=self.make, name='Swift', body_type='Hatchback')
        self.variant_petrol = VehicleVariant.objects.create(
            model=self.model,
            name='ZXi Plus',
            fuel_type='Petrol',
            transmission='Manual',
            year_from=2018,
            year_to=2024
        )
        self.variant_diesel = VehicleVariant.objects.create(
            model=self.model,
            name='ZDi Plus',
            fuel_type='Diesel',
            transmission='Manual',
            year_from=2018,
            year_to=2020
        )
        self.user = User.objects.create_user(username='testdriver', password='Password@123')

    def test_api_models_by_make(self):
        response = self.client.get(reverse('vehicles:api_models'), {'make_id': self.make.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['models']), 1)
        self.assertEqual(data['models'][0]['name'], 'Swift')

    def test_api_years_by_model(self):
        response = self.client.get(reverse('vehicles:api_years'), {'model_id': self.model.id})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(2018, data['years'])
        self.assertIn(2024, data['years'])

    def test_api_fuels_by_model_and_year(self):
        # In 2023, only Petrol was available (Diesel stopped at 2020)
        response = self.client.get(reverse('vehicles:api_fuels'), {
            'model_id': self.model.id,
            'year': 2023
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('Petrol', data['fuels'])
        self.assertNotIn('Diesel', data['fuels'])

        # In 2019, both Petrol and Diesel were available
        response_2019 = self.client.get(reverse('vehicles:api_fuels'), {
            'model_id': self.model.id,
            'year': 2019
        })
        data_2019 = response_2019.json()
        self.assertIn('Petrol', data_2019['fuels'])
        self.assertIn('Diesel', data_2019['fuels'])

    def test_api_variants_filtered_by_fuel_and_year(self):
        response = self.client.get(reverse('vehicles:api_variants'), {
            'model_id': self.model.id,
            'year': 2019,
            'fuel_type': 'Diesel'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['variants']), 1)
        self.assertEqual(data['variants'][0]['name'], 'ZDi Plus')

    def test_select_vehicle_guest_session(self):
        response = self.client.post(
            reverse('vehicles:select_vehicle_session'),
            {'variant_id': self.variant_petrol.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session.get('selected_variant_id'), self.variant_petrol.id)

    def test_select_vehicle_authenticated_user_persists_to_profile(self):
        self.client.login(username='testdriver', password='Password@123')
        response = self.client.post(
            reverse('vehicles:select_vehicle_session'),
            {'variant_id': self.variant_petrol.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        # Verify CustomerProfile persistence
        profile = CustomerProfile.objects.get(user=self.user)
        self.assertEqual(profile.selected_vehicle, self.variant_petrol)

    def test_clear_vehicle_session(self):
        self.client.login(username='testdriver', password='Password@123')
        # First set vehicle
        self.client.post(reverse('vehicles:select_vehicle_session'), {'variant_id': self.variant_petrol.id})
        # Clear vehicle
        response = self.client.post(reverse('vehicles:clear_vehicle_session'))
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.client.session.get('selected_variant_id'))
        profile = CustomerProfile.objects.get(user=self.user)
        self.assertIsNone(profile.selected_vehicle)
