from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from services.models import ServiceCategory, Service, ServiceProvider, ServiceBooking


class ServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='srvuser', email='srv@example.com', password='Password@123')
        self.category = ServiceCategory.objects.create(
            name='Brake Overhaul',
            icon_name='disc',
            description='Complete caliper rebuild and brake bleeding'
        )
        self.provider = ServiceProvider.objects.create(
            name='AUTOVYNEX Hub Indiranagar',
            city='Bengaluru',
            address='100ft Road',
            contact_number='+91 80 1234 5678'
        )
        self.service = Service.objects.create(
            name='Front & Rear Brake Caliper Service',
            category='brake',
            starting_price=Decimal('2800.00'),
            description='Inspection, cleaning, caliper pin greasing and fluid flush'
        )

    def test_service_category_model(self):
        self.assertEqual(str(self.category), 'Brake Overhaul')
        self.assertEqual(self.category.slug, 'brake-overhaul')

    def test_booking_status_default(self):
        from datetime import date
        booking = ServiceBooking.objects.create(
            user=self.user,
            service=self.service,
            provider=self.provider,
            booking_date=date.today(),
            time_slot='10:00 - 12:00 PM',
            vehicle_info='Maruti Suzuki Brezza [KA-05-MN-5678]',
            customer_address='Indiranagar',
            customer_phone='+91 98765 43210'
        )
        self.assertEqual(booking.status, 'confirmed')
        self.assertEqual(str(booking), f"{booking.booking_number} - {self.service.name} ({booking.booking_date} {booking.time_slot})")
