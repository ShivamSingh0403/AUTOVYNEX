from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import CustomerProfile
from vehicles.models import VehicleMake, VehicleModel, VehicleVariant
from inventory.models import ProductCategory, Brand, Product, ProductFitment
from orders.models import CartItem, Order, OrderItem
from garage.models import CustomerVehicle, MaintenanceRecord
from services.models import Service, ServiceProvider, ServiceBooking
from enquiries.models import MissingPartEnquiry


class AutoVynexPlatformTestSuite(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. User accounts
        self.password = 'Secure@12345'
        self.user = User.objects.create_user(
            username='arjun',
            email='arjun.sharma@example.com',
            password=self.password,
            first_name='Arjun',
            last_name='Sharma'
        )

        self.other_user = User.objects.create_user(
            username='priya',
            email='priya@example.com',
            password=self.password,
            first_name='Priya'
        )

        self.staff_user = User.objects.create_user(
            username='staff_admin',
            email='staff@autovynex.com',
            password=self.password,
            is_staff=True
        )

        # 2. Vehicles
        self.make = VehicleMake.objects.create(name='Hyundai', country='South Korea')
        self.model = VehicleModel.objects.create(make=self.make, name='Creta', body_type='SUV')
        self.variant = VehicleVariant.objects.create(
            model=self.model,
            name='1.5 CRDi AT',
            fuel_type='Diesel',
            transmission='Automatic',
            year_from=2020,
            year_to=2026,
            engine_cc=1493,
            power_hp=114
        )

        self.other_model = VehicleModel.objects.create(make=self.make, name='i20', body_type='Hatchback')
        self.other_variant = VehicleVariant.objects.create(
            model=self.other_model,
            name='1.2 Kappa MT',
            fuel_type='Petrol',
            transmission='Manual',
            year_from=2020,
            year_to=2026
        )

        # 3. Product & Fitment
        self.category = ProductCategory.objects.create(name='Brake Pads & Rotors', icon_name='disc')
        self.brand = Brand.objects.create(name='Brembo', origin_country='Italy')
        self.product = Product.objects.create(
            name='Brembo Ceramic Front Brake Pads Set',
            sku='AVX-BRK-TEST',
            category=self.category,
            brand=self.brand,
            price=Decimal('3500.00'),
            discount_price=Decimal('3000.00'),
            stock_quantity=10,
            short_description='Low dust ceramic pads',
            full_description='Detailed OEM replacement pads description',
            is_active=True,
            is_installable=True,
            installation_fee=Decimal('450.00')
        )

        ProductFitment.objects.create(
            product=self.product,
            variant=self.variant,
            fitment_status='compatible',
            notes='Front axle set'
        )

        # 4. Service Provider & Service
        self.provider = ServiceProvider.objects.create(
            name='AUTOVYNEX TechCenter Indiranagar',
            city='Bengaluru',
            address='100 Feet Road, Indiranagar',
            contact_number='+91 80 4125 9901'
        )
        self.service = Service.objects.create(
            name='Comprehensive Periodic Maintenance',
            category='general',
            starting_price=Decimal('3499.00'),
            description='Complete 60 point checkup'
        )

    # 1. Registration & Login
    def test_registration_and_login(self):
        # Register new account
        response = self.client.post(reverse('accounts:register'), {
            'full_name': 'Karan Patel',
            'email': 'karan@example.com',
            'password': 'Password@123',
            'confirm_password': 'Password@123',
            'phone': '+91 9988776655',
            'city': 'Mumbai'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='karan@example.com').exists())

        # Logout & Login
        self.client.logout()
        login_res = self.client.post(reverse('accounts:login'), {
            'username': 'karan@example.com',
            'password': 'Password@123'
        })
        self.assertEqual(login_res.status_code, 302)

    # 2. Product Search & Filtering
    def test_product_search_and_filters(self):
        res = self.client.get(reverse('inventory:shop'), {'q': 'Brembo'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Brembo Ceramic Front Brake Pads')

        res_cat = self.client.get(reverse('inventory:shop'), {'category': self.category.slug})
        self.assertEqual(res_cat.status_code, 200)
        self.assertContains(res_cat, self.product.name)

    # 3. Vehicle Compatibility Check
    def test_vehicle_compatibility_status(self):
        # Test session selection
        session = self.client.session
        session['selected_variant_id'] = self.variant.id
        session.save()

        res = self.client.get(reverse('inventory:product_detail', args=[self.product.slug]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['fitment_status'], 'compatible')

        # Test incompatible variant
        session['selected_variant_id'] = self.other_variant.id
        session.save()
        res_incompat = self.client.get(reverse('inventory:product_detail', args=[self.product.slug]))
        self.assertEqual(res_incompat.status_code, 200)
        self.assertEqual(res_incompat.context['fitment_status'], 'incompatible')

    # 4. Cart Calculations
    def test_cart_calculations(self):
        self.client.login(username=self.user.username, password=self.password)
        # Add to cart
        self.client.post(reverse('orders:add_to_cart', args=[self.product.id]), {
            'quantity': 2,
            'buy_and_install': '1'
        })
        cart_item = CartItem.objects.filter(user=self.user, product=self.product).first()
        self.assertIsNotNone(cart_item)
        self.assertEqual(cart_item.quantity, 2)
        
        # Unit price = 3000 (discount price) + 450 (install fee) = 3450 * 2 = 6900
        expected_subtotal = (Decimal('3000.00') + Decimal('450.00')) * 2
        self.assertEqual(cart_item.item_subtotal, expected_subtotal)

    # 5. Order Creation & Inventory Validation (Atomic)
    def test_order_creation_and_inventory_deduction(self):
        self.client.login(username=self.user.username, password=self.password)
        initial_stock = self.product.stock_quantity

        # Add to cart
        self.client.post(reverse('orders:add_to_cart', args=[self.product.id]), {'quantity': 3})

        # Checkout
        checkout_res = self.client.post(reverse('orders:checkout'), {
            'full_name': 'Arjun Sharma',
            'email': 'arjun.sharma@example.com',
            'phone': '+91 98765 43210',
            'shipping_address': 'Flat 101, Test Road',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'pincode': '560001',
            'payment_method': 'simulated_upi'
        })
        self.assertEqual(checkout_res.status_code, 302)

        # Verify Order exists
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertTrue(order.order_number.startswith('AVX-ORD-'))

        # Verify stock was deducted
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock - 3)

    # 6. Missing Part Enquiry Submission
    def test_missing_part_enquiry_submission(self):
        res = self.client.post(reverse('enquiries:missing_part_request'), {
            'vehicle_details': '2023 Tata Nexon EV',
            'part_name': 'High Voltage Traction Battery Fuse',
            'category': 'Electrical & Sensors',
            'description': 'Blown main fuse following short circuit',
            'contact_name': 'Rohit Verma',
            'contact_email': 'rohit@example.com',
            'contact_phone': '+91 91234 56789',
            'contact_preference': 'whatsapp'
        })
        self.assertEqual(res.status_code, 302)
        enquiry = MissingPartEnquiry.objects.filter(part_name='High Voltage Traction Battery Fuse').first()
        self.assertIsNotNone(enquiry)
        self.assertTrue(enquiry.reference_code.startswith('AVX-ENQ-'))
        self.assertEqual(enquiry.status, 'submitted')

    # 7. Service Booking & Duplicate Slot Conflict Prevention
    def test_service_booking_conflict_prevention(self):
        self.client.login(username=self.user.username, password=self.password)
        book_date = date.today() + timedelta(days=5)
        slot = '09:00 - 11:00 AM'

        # First booking succeeds
        res1 = self.client.post(reverse('services:book'), {
            'service_id': self.service.id,
            'provider_id': self.provider.id,
            'booking_date': book_date,
            'time_slot': slot,
            'vehicle_info': 'Hyundai Creta [KA-01-AB-1234]',
            'customer_address': 'Indiranagar, Bengaluru',
            'customer_phone': '+91 98765 43210'
        })
        self.assertEqual(res1.status_code, 302)
        self.assertEqual(ServiceBooking.objects.filter(provider=self.provider, booking_date=book_date, time_slot=slot).count(), 1)

        # Second booking at exact same workshop, date, and slot must be prevented
        self.client.logout()
        self.client.login(username=self.other_user.username, password=self.password)
        res2 = self.client.post(reverse('services:book'), {
            'service_id': self.service.id,
            'provider_id': self.provider.id,
            'booking_date': book_date,
            'time_slot': slot,
            'vehicle_info': 'Another Car',
            'customer_address': 'Koramangala, Bengaluru',
            'customer_phone': '+91 90000 11111'
        })
        # Conflict causes error redirect
        self.assertEqual(res2.status_code, 302)
        # Count remains 1
        self.assertEqual(ServiceBooking.objects.filter(provider=self.provider, booking_date=book_date, time_slot=slot).count(), 1)

    # 8. Customer Data Isolation
    def test_customer_data_isolation(self):
        # Create vehicle in user's garage
        cv = CustomerVehicle.objects.create(
            user=self.user,
            variant=self.variant,
            registration_number='KA-04-XY-9999'
        )

        # Login as other_user and attempt to access user's vehicle detail
        self.client.login(username=self.other_user.username, password=self.password)
        res = self.client.get(reverse('garage:vehicle_detail', args=[cv.id]))
        # Must return 404
        self.assertEqual(res.status_code, 404)

    # 9. Administrator Permissions & Role-Based Access Control
    def test_administrator_role_permissions(self):
        # Regular user cannot access custom admin center
        self.client.login(username=self.user.username, password=self.password)
        res_user = self.client.get(reverse('custom_admin:dashboard_overview'))
        self.assertEqual(res_user.status_code, 302) # Redirected away to login

        # Staff user can access custom admin center
        self.client.logout()
        self.client.login(username=self.staff_user.username, password=self.password)
        res_staff = self.client.get(reverse('custom_admin:dashboard_overview'))
        self.assertEqual(res_staff.status_code, 200)
        self.assertContains(res_staff, 'Platform Administration Dashboard')
