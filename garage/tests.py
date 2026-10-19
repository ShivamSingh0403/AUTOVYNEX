from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from vehicles.models import VehicleMake, VehicleModel, VehicleVariant
from garage.models import CustomerVehicle, MaintenanceRecord, MaintenanceReminder, VehicleDocument
from services.models import Service, ServiceProvider, ServiceBooking


class DigitalGarageComprehensiveTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='garagist', email='gara@example.com', password='Password@123')
        self.intruder = User.objects.create_user(username='intruder', email='intruder@example.com', password='Password@123')

        # Seed Vehicle Structure
        self.make = VehicleMake.objects.create(name='Tata', country='India')
        self.model = VehicleModel.objects.create(make=self.make, name='Harrier', body_type='SUV', release_year=2019)
        self.variant = VehicleVariant.objects.create(
            model=self.model,
            name='XZ Plus Dark Edition',
            fuel_type='Diesel',
            transmission='Manual',
            year_from=2019,
            year_to=2026,
            engine_cc=1956
        )

        # Primary vehicle for user
        self.vehicle1 = CustomerVehicle.objects.create(
            user=self.user,
            variant=self.variant,
            nickname='The Beast',
            registration_number='DL-01-AB-1234',
            vin_number='MAT12345678901234',
            purchase_year=2022,
            current_mileage=25000,
            color='Harrier Black',
            is_default=True
        )

        # Service Provider & Service for booking tests
        self.provider = ServiceProvider.objects.create(
            name='AUTOVYNEX Hub Indiranagar',
            city='Bengaluru',
            address='100 Feet Rd, Indiranagar',
            contact_number='9876543210',
            is_active=True
        )
        self.service = Service.objects.create(
            name='Comprehensive General Service',
            category='general',
            starting_price=Decimal('4999.00'),
            estimated_duration='4 hours'
        )

    # 1. Vehicle Creation and Editing Tests
    def test_add_vehicle_valid(self):
        self.client.login(username='garagist', password='Password@123')
        response = self.client.post(reverse('garage:add_vehicle'), {
            'variant_id': self.variant.id,
            'nickname': 'Weekend Cruiser',
            'registration_number': 'KA-05-MN-9988',
            'vin_number': 'VIN98765432101234',
            'purchase_year': 2023,
            'current_mileage': 12000,
            'color': 'Calypso Red',
            'is_default': '0'
        })
        self.assertEqual(response.status_code, 302)
        new_car = CustomerVehicle.objects.filter(nickname='Weekend Cruiser').first()
        self.assertIsNotNone(new_car)
        self.assertEqual(new_car.registration_number, 'KA-05-MN-9988')
        self.assertEqual(new_car.current_mileage, 12000)

    def test_add_vehicle_invalid_year_rejection(self):
        self.client.login(username='garagist', password='Password@123')
        # Model production is 2019 - 2026; attempt year 2010
        response = self.client.post(reverse('garage:add_vehicle'), {
            'variant_id': self.variant.id,
            'nickname': 'Ancient Year Car',
            'purchase_year': 2010,
            'current_mileage': 50000
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CustomerVehicle.objects.filter(nickname='Ancient Year Car').exists())

    def test_edit_vehicle_details(self):
        self.client.login(username='garagist', password='Password@123')
        response = self.client.post(reverse('garage:edit_vehicle', args=[self.vehicle1.id]), {
            'nickname': 'Night Raider',
            'registration_number': 'DL-01-AB-9999',
            'vin_number': self.vehicle1.vin_number,
            'purchase_year': 2022,
            'current_mileage': 28500,
            'color': 'Dark Stealth',
            'is_default': '1'
        })
        self.assertEqual(response.status_code, 302)
        self.vehicle1.refresh_from_db()
        self.assertEqual(self.vehicle1.nickname, 'Night Raider')
        self.assertEqual(self.vehicle1.registration_number, 'DL-01-AB-9999')
        self.assertEqual(self.vehicle1.current_mileage, 28500)

    # 2. Multiple Vehicles per Customer & Primary Vehicle Switching
    def test_multiple_vehicles_and_primary_promotion(self):
        self.client.login(username='garagist', password='Password@123')
        vehicle2 = CustomerVehicle.objects.create(
            user=self.user,
            variant=self.variant,
            nickname='Second Car',
            registration_number='HR-26-XX-5555',
            current_mileage=15000,
            is_default=False
        )
        self.assertEqual(CustomerVehicle.objects.filter(user=self.user).count(), 2)

        # Set vehicle2 as primary
        self.client.post(reverse('garage:set_default', args=[vehicle2.id]))
        self.vehicle1.refresh_from_db()
        vehicle2.refresh_from_db()
        self.assertFalse(self.vehicle1.is_default)
        self.assertTrue(vehicle2.is_default)

        # Deleting default vehicle should promote the remaining vehicle
        self.client.post(reverse('garage:delete_vehicle', args=[vehicle2.id]))
        self.vehicle1.refresh_from_db()
        self.assertTrue(self.vehicle1.is_default)

    # 3. Vehicle Ownership Restrictions
    def test_ownership_restrictions_on_read_and_mutation(self):
        self.client.login(username='intruder', password='Password@123')

        # Intruder cannot view user's vehicle
        resp = self.client.get(reverse('garage:vehicle_detail', args=[self.vehicle1.id]))
        self.assertEqual(resp.status_code, 404)

        # Intruder cannot edit user's vehicle
        resp = self.client.post(reverse('garage:edit_vehicle', args=[self.vehicle1.id]), {
            'nickname': 'Hacked'
        })
        self.assertEqual(resp.status_code, 404)
        self.vehicle1.refresh_from_db()
        self.assertEqual(self.vehicle1.nickname, 'The Beast')

        # Intruder cannot delete user's vehicle
        resp = self.client.post(reverse('garage:delete_vehicle', args=[self.vehicle1.id]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(CustomerVehicle.objects.filter(id=self.vehicle1.id).exists())

    # 4. Maintenance Expense Calculations & Decimal Precision
    def test_maintenance_expense_calculation_with_decimal_precision(self):
        self.client.login(username='garagist', password='Password@123')
        # Create record with labour=1500.50, parts=4250.25, other=350.25 -> Total=6101.00
        response = self.client.post(reverse('garage:add_record', args=[self.vehicle1.id]), {
            'service_title': '40,000 KM Periodic Inspection',
            'service_type': 'general_service',
            'service_date': '2026-05-10',
            'mileage': 26000,
            'workshop_name': 'Authorized Service Indiranagar',
            'labour_cost': '1500.50',
            'parts_cost': '4250.25',
            'other_cost': '350.25',
            'notes': 'Fully synthetic 5W-30 oil and new air filter.'
        })
        self.assertEqual(response.status_code, 302)
        rec = MaintenanceRecord.objects.filter(customer_vehicle=self.vehicle1).first()
        self.assertIsNotNone(rec)
        self.assertEqual(rec.labour_cost, Decimal('1500.50'))
        self.assertEqual(rec.parts_cost, Decimal('4250.25'))
        self.assertEqual(rec.other_cost, Decimal('350.25'))
        self.assertEqual(rec.cost, Decimal('6101.00'))

        # Odometer should update to 26000
        self.vehicle1.refresh_from_db()
        self.assertEqual(self.vehicle1.current_mileage, 26000)

        # Check total expenses aggregation on vehicle
        self.assertEqual(self.vehicle1.total_expenses, Decimal('6101.00'))

    # 5. Reminder Due-State Calculations
    def test_reminder_due_states(self):
        today = date.today()

        # Overdue by date
        r_overdue = MaintenanceReminder.objects.create(
            customer_vehicle=self.vehicle1,
            title='PUC Renewal',
            reminder_type='pollution_check',
            due_date=today - timedelta(days=5),
            priority='high'
        )
        self.assertEqual(r_overdue.status_state, 'overdue')

        # Due Soon by date (within 14 days)
        r_due_soon = MaintenanceReminder.objects.create(
            customer_vehicle=self.vehicle1,
            title='Insurance Expiry',
            reminder_type='insurance_renewal',
            due_date=today + timedelta(days=7),
            priority='urgent'
        )
        self.assertEqual(r_due_soon.status_state, 'due_soon')

        # Upcoming
        r_upcoming = MaintenanceReminder.objects.create(
            customer_vehicle=self.vehicle1,
            title='Tyre Rotation',
            reminder_type='tyre_service',
            due_date=today + timedelta(days=60),
            priority='low'
        )
        self.assertEqual(r_upcoming.status_state, 'upcoming')

        # Completed
        r_completed = MaintenanceReminder.objects.create(
            customer_vehicle=self.vehicle1,
            title='Battery Inspection',
            reminder_type='battery_check',
            due_date=today - timedelta(days=10),
            is_completed=True
        )
        self.assertEqual(r_completed.status_state, 'completed')

    # 6. Reminder Completion, Recurrence, and Postponement
    def test_reminder_postpone_and_recurring_completion(self):
        self.client.login(username='garagist', password='Password@123')
        today = date.today()

        reminder = MaintenanceReminder.objects.create(
            customer_vehicle=self.vehicle1,
            title='Synthetic Oil Change',
            reminder_type='oil_change',
            due_date=today + timedelta(days=10),
            due_mileage=30000,
            recurrence_months=6,
            recurrence_km=10000,
            priority='high'
        )

        # Postpone reminder
        self.client.post(reverse('garage:postpone_reminder', args=[reminder.id]), {
            'extend_days': 30,
            'extend_km': 1000
        })
        reminder.refresh_from_db()
        self.assertEqual(reminder.due_date, today + timedelta(days=40))
        self.assertEqual(reminder.due_mileage, 31000)

        # Complete reminder (should spawn recurring next cycle)
        self.client.post(reverse('garage:toggle_reminder', args=[reminder.id]))
        reminder.refresh_from_db()
        self.assertTrue(reminder.is_completed)

        # New reminder should have been spawned
        next_cycle = MaintenanceReminder.objects.filter(
            customer_vehicle=self.vehicle1,
            title='Synthetic Oil Change',
            is_completed=False
        ).first()
        self.assertIsNotNone(next_cycle)
        self.assertEqual(next_cycle.recurrence_months, 6)

    # 7. Document Upload Validation
    def test_document_upload_validation(self):
        self.client.login(username='garagist', password='Password@123')

        # Invalid file type
        bad_file = SimpleUploadedFile("payload.sh", b"echo hack", content_type="text/x-shellscript")
        response = self.client.post(reverse('garage:upload_document', args=[self.vehicle1.id]), {
            'doc_type': 'rc',
            'title': 'Shell Script',
            'document_file': bad_file
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(VehicleDocument.objects.filter(title='Shell Script').exists())

        # Valid PDF file
        valid_pdf = SimpleUploadedFile("car_rc.pdf", b"%PDF-1.4 sample stream", content_type="application/pdf")
        response = self.client.post(reverse('garage:upload_document', args=[self.vehicle1.id]), {
            'doc_type': 'rc',
            'title': 'Digital Registration Certificate',
            'document_file': valid_pdf,
            'expiry_date': '2035-12-31'
        })
        self.assertEqual(response.status_code, 302)
        doc = VehicleDocument.objects.filter(title='Digital Registration Certificate').first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.doc_type, 'rc')

    # 8. Private Document Access Restrictions
    def test_secure_document_access_isolation(self):
        valid_pdf = SimpleUploadedFile("private_policy.pdf", b"%PDF-1.4 private insurance", content_type="application/pdf")
        doc = VehicleDocument.objects.create(
            customer_vehicle=self.vehicle1,
            doc_type='insurance',
            title='Private Insurance Policy',
            document_file=valid_pdf
        )

        # Intruder attempts to view or download user's private document
        self.client.login(username='intruder', password='Password@123')
        resp_view = self.client.get(reverse('garage:view_document', args=[doc.id]))
        self.assertEqual(resp_view.status_code, 404)

        resp_dl = self.client.get(reverse('garage:download_document', args=[doc.id]))
        self.assertEqual(resp_dl.status_code, 404)

        # Owner has access
        self.client.login(username='garagist', password='Password@123')
        resp_owner = self.client.get(reverse('garage:view_document', args=[doc.id]))
        self.assertEqual(resp_owner.status_code, 200)

    # 9. Service Booking Validation & Slot Conflict Prevention
    def test_service_booking_slot_conflict_prevention(self):
        self.client.login(username='garagist', password='Password@123')
        booking_date = (date.today() + timedelta(days=2)).strftime('%Y-%m-%d')
        time_slot = '10:00 AM - 12:00 PM'

        # First booking succeeds
        resp1 = self.client.post(reverse('services:book'), {
            'service_id': self.service.id,
            'provider_id': self.provider.id,
            'vehicle_info': self.vehicle1.display_title,
            'booking_date': booking_date,
            'time_slot': time_slot,
            'customer_address': '123 Tech Park Road, Bengaluru',
            'customer_phone': '9876543210'
        })
        self.assertEqual(resp1.status_code, 302)
        self.assertTrue(ServiceBooking.objects.filter(provider=self.provider, booking_date=booking_date, time_slot=time_slot).exists())

        # Duplicate slot booking attempt by intruder is rejected due to conflict
        self.client.login(username='intruder', password='Password@123')
        resp2 = self.client.post(reverse('services:book'), {
            'service_id': self.service.id,
            'provider_id': self.provider.id,
            'vehicle_info': "Another Car",
            'booking_date': booking_date,
            'time_slot': time_slot,
            'customer_address': '456 MG Road',
            'customer_phone': '9123456780'
        })
        self.assertEqual(resp2.status_code, 302)
        # Still only 1 confirmed booking for that slot
        self.assertEqual(ServiceBooking.objects.filter(provider=self.provider, booking_date=booking_date, time_slot=time_slot).count(), 1)

    # 10. Customer Dashboard Digital Garage Aggregation
    def test_customer_dashboard_garage_aggregation(self):
        MaintenanceRecord.objects.create(
            customer_vehicle=self.vehicle1,
            service_date=date.today(),
            service_type='oil_change',
            service_title='Full Synthetic Engine Oil Change',
            mileage=25000,
            labour_cost=Decimal('500.00'),
            parts_cost=Decimal('2500.00'),
            workshop_name='Speedy Lube'
        )

        self.client.login(username='garagist', password='Password@123')
        response = self.client.get(reverse('dashboard:customer_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['primary_vehicle'], self.vehicle1)
        self.assertEqual(response.context['total_vehicles'], 1)
        self.assertEqual(response.context['total_maintenance_spent'], Decimal('3000.00'))
        self.assertEqual(len(response.context['recent_services']), 1)
