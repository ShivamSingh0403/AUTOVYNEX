import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from services.models import (
    ServiceCategory, Service, ServiceProvider, ProviderService,
    ProviderSchedule, ProviderUnavailableDate, ServiceBooking,
    ServiceBookingHistory, ServiceCompletionRecord, ServiceEnquiry
)
from services.scheduling import (
    get_available_slots, validate_and_reserve_slot,
    transition_booking_status, complete_service_booking
)
from vehicles.models import VehicleMake, VehicleModel, VehicleVariant
from garage.models import CustomerVehicle, MaintenanceRecord
from accounts.models import Notification


class ServiceCentreTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='service_customer',
            email='customer@example.com',
            password='Password@123'
        )
        self.provider_staff = User.objects.create_user(
            username='workshop_mgr',
            email='workshop@example.com',
            password='Password@123',
            is_staff=True
        )

        # Vehicle Brand & Model
        self.make = VehicleMake.objects.create(name='Hyundai', slug='hyundai')
        self.vmodel = VehicleModel.objects.create(make=self.make, name='Creta', slug='creta', body_type='suv')
        self.variant = VehicleVariant.objects.create(
            model=self.vmodel,
            name='SX (O) Diesel AT',
            fuel_type='diesel',
            transmission='automatic',
            engine_cc=1493
        )

        # Garage Vehicle
        self.garage_vehicle = CustomerVehicle.objects.create(
            user=self.user,
            variant=self.variant,
            nickname='Creta Beast',
            registration_number='KA-01-MJ-9999',
            current_mileage=35000,
            is_default=True
        )

        # Category
        self.category = ServiceCategory.objects.create(
            name='General servicing',
            icon_name='wrench',
            description='Periodic multi-point checkup',
            sort_order=1
        )

        # Service
        self.service = Service.objects.create(
            name='Periodic Major Service',
            category='general',
            category_ref=self.category,
            estimated_duration='3 hours',
            estimated_duration_minutes=180,
            starting_price=Decimal('3499.00'),
            description='Comprehensive checkup and filter change',
            is_popular=True
        )

        # Service Provider
        self.provider = ServiceProvider.objects.create(
            owner=self.provider_staff,
            name='AUTOVYNEX Precision Hub',
            city='Bengaluru',
            state='Karnataka',
            postal_code='560038',
            address='80ft Road, Indiranagar',
            contact_number='+91 80 9876 5432',
            email='indiranagar@autovynex.com',
            operating_hours='Mon - Sat: 9:00 AM - 6:00 PM',
            facilities='Lounge, Wi-Fi, Card Payment, Express Bay',
            status='active',
            is_demo=True,
            is_verified=False
        )
        self.provider.supported_brands.add(self.make)

        # Configure Weekly Operating Schedule (Monday to Saturday open, Sunday closed)
        for day in range(7):
            is_sun = (day == 6)
            ProviderSchedule.objects.create(
                provider=self.provider,
                weekday=day,
                is_closed=is_sun,
                open_time=datetime.time(9, 0),
                close_time=datetime.time(18, 0),
                has_break=True,
                break_start=datetime.time(13, 0),
                break_end=datetime.time(14, 0),
                slot_duration_minutes=60,
                max_bookings_per_slot=2
            )

        # Provider custom pricing
        self.provider_service = ProviderService.objects.create(
            provider=self.provider,
            service=self.service,
            price=Decimal('3299.00'),
            duration_minutes=180,
            is_available=True
        )

    def test_marketplace_directory_view(self):
        """Test service centre directory listing, filters, and demo badging."""
        response = self.client.get(reverse('services:directory'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AUTOVYNEX Precision Hub')
        self.assertContains(response, 'Sample Listing (Demo)')
        self.assertContains(response, 'Bengaluru')

    def test_directory_server_side_filters(self):
        """Test directory filtering by city, brand, price, and category."""
        # City match
        res_blr = self.client.get(reverse('services:directory'), {'city': 'Bengaluru'})
        self.assertContains(res_blr, 'AUTOVYNEX Precision Hub')

        # City mismatch
        res_del = self.client.get(reverse('services:directory'), {'city': 'Delhi'})
        self.assertNotContains(res_del, 'AUTOVYNEX Precision Hub')

        # Category filter
        res_cat = self.client.get(reverse('services:directory'), {'category': self.category.slug})
        self.assertContains(res_cat, 'AUTOVYNEX Precision Hub')

        # Brand filter
        res_brand = self.client.get(reverse('services:directory'), {'brand': str(self.make.id)})
        self.assertContains(res_brand, 'AUTOVYNEX Precision Hub')

        # Price range
        res_price_ok = self.client.get(reverse('services:directory'), {'min_price': '3000', 'max_price': '4000'})
        self.assertContains(res_price_ok, 'AUTOVYNEX Precision Hub')

        res_price_high = self.client.get(reverse('services:directory'), {'min_price': '5000'})
        self.assertNotContains(res_price_high, 'AUTOVYNEX Precision Hub')

    def test_provider_detail_view_and_enquiry(self):
        """Test workshop detail page and contact/enquiry form submission."""
        response = self.client.get(reverse('services:provider_detail', kwargs={'slug': self.provider.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.provider.name)
        self.assertContains(response, 'Periodic Major Service')
        self.assertContains(response, '3299')

        # Submit Enquiry
        post_data = {
            'submit_enquiry': '1',
            'name': 'Rahul Sharma',
            'phone': '+91 9988776655',
            'email': 'rahul@example.com',
            'message': 'Do you offer pickup service near Defence Colony?'
        }
        res_post = self.client.post(reverse('services:provider_detail', kwargs={'slug': self.provider.slug}), post_data)
        self.assertEqual(res_post.status_code, 302)
        self.assertTrue(ServiceEnquiry.objects.filter(name='Rahul Sharma', provider=self.provider).exists())

    def test_slot_generation_engine(self):
        """Test scheduling engine slot generation, break exclusion, and holiday closures."""
        # Find next Monday (weekday 0)
        today = datetime.date.today()
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + datetime.timedelta(days=days_ahead)

        result = get_available_slots(self.provider, next_monday)
        self.assertTrue(result['is_open'])
        slots = result['slots']
        # Hours: 9-13 (4 slots) and 14-18 (4 slots) = 8 total slots (13-14 is break)
        self.assertEqual(len(slots), 8)
        # Verify no slot overlaps 13:00 - 14:00
        for s in slots:
            self.assertNotIn('01:00 PM - 02:00 PM', s['slot_label'])

        # Test Sunday closure
        next_sunday = next_monday + datetime.timedelta(days=6)
        res_sun = get_available_slots(self.provider, next_sunday)
        self.assertFalse(res_sun['is_open'])
        self.assertIn("regularly closed", res_sun['reason'])

        # Test Holiday closure
        holiday_date = next_monday + datetime.timedelta(days=2)
        ProviderUnavailableDate.objects.create(
            provider=self.provider,
            date=holiday_date,
            reason='Workshop Facility Sanitization'
        )
        res_hol = get_available_slots(self.provider, holiday_date)
        self.assertFalse(res_hol['is_open'])
        self.assertIn("Workshop Facility Sanitization", res_hol['reason'])

    def test_double_booking_and_capacity_prevention(self):
        """Test slot reservation prevents bookings once max_bookings_per_slot is reached."""
        target_date = datetime.date.today() + datetime.timedelta(days=5)
        slot_label = '09:00 AM - 10:00 AM'

        # Ensure day is open
        sch = ProviderSchedule.objects.get(provider=self.provider, weekday=target_date.weekday())
        sch.is_closed = False
        sch.max_bookings_per_slot = 1
        sch.save()

        # First reservation passes
        ok, t_start, t_end = validate_and_reserve_slot(self.provider, target_date, slot_label)
        self.assertTrue(ok)

        # Create booking for that slot
        ServiceBooking.objects.create(
            user=self.user,
            provider=self.provider,
            service=self.service,
            booking_date=target_date,
            time_slot=slot_label,
            status='confirmed',
            customer_phone='+91 99999 11111'
        )

        # Second reservation must fail because capacity = 1
        ok2, err, _ = validate_and_reserve_slot(self.provider, target_date, slot_label)
        self.assertFalse(ok2)
        self.assertIn("already fully booked", err)

    def test_booking_workflow_submission(self):
        """Test customer multi-step booking submission creates booking, snapshot, and history."""
        self.client.login(username='service_customer', password='Password@123')
        target_date = datetime.date.today() + datetime.timedelta(days=3)
        # Ensure not Sunday
        if target_date.weekday() == 6:
            target_date += datetime.timedelta(days=1)

        post_data = {
            'provider': str(self.provider.id),
            'service': str(self.service.id),
            'vehicle_source': 'garage',
            'customer_vehicle_id': str(self.garage_vehicle.id),
            'booking_date': target_date.strftime('%Y-%m-%d'),
            'time_slot': '10:00 AM - 11:00 AM',
            'customer_phone': '+91 98765 00000',
            'customer_address': 'Flat 202, Palm Meadows, Bengaluru',
            'problem_description': 'Brake shudder at high speed'
        }

        res = self.client.post(reverse('services:book'), post_data)
        self.assertEqual(res.status_code, 302)

        booking = ServiceBooking.objects.filter(user=self.user, provider=self.provider).first()
        self.assertIsNotNone(booking)
        self.assertEqual(booking.customer_vehicle, self.garage_vehicle)
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.payment_status, 'unpaid')
        self.assertEqual(booking.price_estimate_snapshot, Decimal('3299.00'))
        self.assertTrue(booking.history_logs.filter(new_status='pending').exists())

    def test_booking_status_transitions_and_audit_history(self):
        """Test status transitions: pending -> confirmed -> in_progress -> completed."""
        booking = ServiceBooking.objects.create(
            user=self.user,
            provider=self.provider,
            service=self.service,
            booking_date=datetime.date.today() + datetime.timedelta(days=2),
            time_slot='11:00 AM - 12:00 PM',
            status='pending',
            customer_phone='+91 98765 43210'
        )

        # Pending -> Confirmed
        ok, msg = transition_booking_status(booking, 'confirmed', actor=self.provider_staff, customer_note='Bay 3 reserved')
        self.assertTrue(ok)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')
        self.assertTrue(Notification.objects.filter(user=self.user, title__icontains='Confirmed').exists())

        # Confirmed -> In Progress
        ok, msg = transition_booking_status(booking, 'in_progress', actor=self.provider_staff, customer_note='Work started')
        self.assertTrue(ok)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'in_progress')

        # Invalid transition: In Progress cannot jump directly back to pending
        invalid_ok, err = transition_booking_status(booking, 'pending')
        self.assertFalse(invalid_ok)

    def test_service_completion_and_digital_garage_sync(self):
        """Test workshop completion records labour/parts and creates MaintenanceRecord in Digital Garage."""
        booking = ServiceBooking.objects.create(
            user=self.user,
            provider=self.provider,
            service=self.service,
            customer_vehicle=self.garage_vehicle,
            booking_date=datetime.date.today(),
            time_slot='02:00 PM - 03:00 PM',
            status='in_progress',
            customer_phone='+91 98765 43210',
            price_estimate_snapshot=Decimal('3299.00')
        )

        comp = complete_service_booking(
            booking=booking,
            actor=self.provider_staff,
            labour_charges=Decimal('1500.00'),
            parts_charges=Decimal('2500.00'),
            other_charges=Decimal('200.00'),
            odometer_reading=38500,
            work_performed='Full 40-point service, synthetic oil swap, caliper greasing',
            parts_replaced='Castrol Edge 5W-40 (4L), OEM Filter',
            technician_notes='Front brake pads 70% life remaining',
            next_service_date=datetime.date.today() + datetime.timedelta(days=180),
            next_service_odometer=48500
        )

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'completed')
        self.assertEqual(booking.final_amount, Decimal('4200.00'))
        self.assertEqual(booking.payment_status, 'paid_at_workshop')

        # Verify auto-synced MaintenanceRecord in customer's Digital Garage
        maint_record = MaintenanceRecord.objects.filter(customer_vehicle=self.garage_vehicle).first()
        self.assertIsNotNone(maint_record)
        self.assertEqual(maint_record.cost, Decimal('4200.00'))
        self.assertEqual(maint_record.mileage, 38500)
        self.assertEqual(maint_record.workshop_name, self.provider.name)

        # Verify CustomerVehicle mileage was updated
        self.garage_vehicle.refresh_from_db()
        self.assertEqual(self.garage_vehicle.current_mileage, 38500)

    def test_customer_cancellation_and_rescheduling(self):
        """Test customer actions to cancel and reschedule an appointment."""
        self.client.login(username='service_customer', password='Password@123')
        booking = ServiceBooking.objects.create(
            user=self.user,
            provider=self.provider,
            service=self.service,
            booking_date=datetime.date.today() + datetime.timedelta(days=4),
            time_slot='09:00 AM - 10:00 AM',
            status='confirmed',
            customer_phone='+91 98765 43210'
        )

        # Cancel appointment
        cancel_url = reverse('services:cancel_booking', kwargs={'booking_number': booking.booking_number})
        res_cancel = self.client.post(cancel_url, {'cancellation_reason': 'Out of town travel'})
        self.assertEqual(res_cancel.status_code, 302)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')
        self.assertEqual(booking.cancellation_reason, 'Out of town travel')

    def test_provider_dashboard_metrics_and_actions(self):
        """Test workshop portal metrics, status updating, and schedule management."""
        self.client.login(username='workshop_mgr', password='Password@123')

        # View Dashboard
        dash_res = self.client.get(reverse('services:provider_dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, self.provider.name)

        # Workshop Updates Booking Status to In Progress
        booking = ServiceBooking.objects.create(
            user=self.user,
            provider=self.provider,
            service=self.service,
            booking_date=datetime.date.today(),
            time_slot='03:00 PM - 04:00 PM',
            status='confirmed',
            customer_phone='+91 98765 43210'
        )

        update_url = reverse('services:provider_update_status', kwargs={'booking_number': booking.booking_number})
        res_update = self.client.post(update_url, {'status': 'in_progress', 'staff_note': 'Vehicle checked in'})
        self.assertEqual(res_update.status_code, 302)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'in_progress')
