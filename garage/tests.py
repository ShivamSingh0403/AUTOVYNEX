from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from vehicles.models import VehicleMake, VehicleModel, VehicleVariant
from garage.models import CustomerVehicle, MaintenanceRecord, MaintenanceReminder, VehicleDocument


class GarageSecurityAndValidationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='garagist', email='gara@example.com', password='Password@123')
        self.intruder = User.objects.create_user(username='intruder', email='intruder@example.com', password='Password@123')

        self.make = VehicleMake.objects.create(name='Tata', country='India')
        self.model = VehicleModel.objects.create(make=self.make, name='Harrier', body_type='SUV')
        self.variant = VehicleVariant.objects.create(
            model=self.model,
            name='XZ Plus Dark Edition',
            fuel_type='Diesel',
            transmission='Manual',
            year_from=2021,
            year_to=2026
        )

        self.vehicle = CustomerVehicle.objects.create(
            user=self.user,
            variant=self.variant,
            registration_number='DL-01-AB-1234',
            nickname='The Beast',
            current_mileage=24500
        )

    def test_garage_access_requires_login(self):
        response = self.client.get(reverse('garage:index'))
        self.assertEqual(response.status_code, 302)

    def test_private_vehicle_isolation(self):
        # Intruder attempts to view user's vehicle details
        self.client.login(username='intruder', password='Password@123')
        response = self.client.get(reverse('garage:vehicle_detail', args=[self.vehicle.id]))
        self.assertEqual(response.status_code, 404)

    def test_document_file_validation_invalid_extension(self):
        self.client.login(username='garagist', password='Password@123')
        # Attempt to upload an executable .exe file
        fake_file = SimpleUploadedFile("malicious.exe", b"binary content", content_type="application/octet-stream")
        response = self.client.post(reverse('garage:upload_document', args=[self.vehicle.id]), {
            'doc_type': 'rc',
            'title': 'RC Copy',
            'document_file': fake_file
        })
        self.assertEqual(response.status_code, 302)
        # Should not have created any vehicle document
        self.assertEqual(VehicleDocument.objects.filter(customer_vehicle=self.vehicle).count(), 0)

    def test_document_file_validation_valid_pdf(self):
        self.client.login(username='garagist', password='Password@123')
        valid_pdf = SimpleUploadedFile("registration_certificate.pdf", b"%PDF-1.4 sample content", content_type="application/pdf")
        response = self.client.post(reverse('garage:upload_document', args=[self.vehicle.id]), {
            'doc_type': 'rc',
            'title': 'RC Certificate',
            'document_file': valid_pdf
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(VehicleDocument.objects.filter(customer_vehicle=self.vehicle).count(), 1)

    def test_maintenance_record_and_reminder(self):
        record = MaintenanceRecord.objects.create(
            customer_vehicle=self.vehicle,
            service_date=date.today(),
            service_type='Scheduled Service',
            notes='20,000 KM major maintenance',
            mileage=20000,
            cost=Decimal('8500.00'),
            workshop_name='Tata Motors Authorized Service'
        )
        self.assertEqual(record.customer_vehicle.user, self.user)
        self.assertEqual(record.cost, Decimal('8500.00'))
