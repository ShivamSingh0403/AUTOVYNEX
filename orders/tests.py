from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from inventory.models import ProductCategory, Brand, Product, InventoryRecord
from orders.models import CartItem, Order, OrderItem
from services.models import InstallationRequest


class ComprehensiveEcommerceTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='customer1', email='cust1@example.com', password='Password@123')
        self.user2 = User.objects.create_user(username='customer2', email='cust2@example.com', password='Password@123')

        self.category = ProductCategory.objects.create(name='Spark Plugs')
        self.brand = Brand.objects.create(name='NGK')
        
        self.product = Product.objects.create(
            name='NGK Iridium Spark Plug Set',
            sku='NGK-SPK-001',
            category=self.category,
            brand=self.brand,
            price=Decimal('2000.00'),
            stock_quantity=10,
            is_active=True,
            is_installable=True,
            installation_fee=Decimal('350.00')
        )

        self.cheap_product = Product.objects.create(
            name='Wiper Blade Set',
            sku='WPR-BLD-002',
            category=self.category,
            brand=self.brand,
            price=Decimal('500.00'),
            stock_quantity=5,
            is_active=True
        )

    def test_guest_cart_and_add_to_cart(self):
        # Guest user adds item
        response = self.client.post(reverse('orders:add_to_cart', args=[self.product.id]), {'quantity': 2})
        self.assertEqual(response.status_code, 302)
        session_key = self.client.session.session_key
        guest_item = CartItem.objects.filter(session_key=session_key, product=self.product).first()
        self.assertIsNotNone(guest_item)
        self.assertEqual(guest_item.quantity, 2)

    def test_authenticated_cart_quantity_clamping_to_stock(self):
        self.client.login(username='customer1', password='Password@123')
        # Try to add more than stock (10)
        response = self.client.post(reverse('orders:add_to_cart', args=[self.product.id]), {'quantity': 15})
        self.assertEqual(response.status_code, 302)
        cart_item = CartItem.objects.get(user=self.user1, product=self.product)
        self.assertEqual(cart_item.quantity, 10)

    def test_update_cart_item_actions(self):
        self.client.login(username='customer1', password='Password@123')
        cart_item = CartItem.objects.create(user=self.user1, product=self.product, quantity=2)

        # Increment
        self.client.post(reverse('orders:update_cart_item', args=[cart_item.id]), {'action': 'increment'})
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)

        # Decrement
        self.client.post(reverse('orders:update_cart_item', args=[cart_item.id]), {'action': 'decrement'})
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)

        # Set quantity directly
        self.client.post(reverse('orders:update_cart_item', args=[cart_item.id]), {'action': 'set_quantity', 'quantity': 5})
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 5)

        # Remove item
        self.client.post(reverse('orders:update_cart_item', args=[cart_item.id]), {'action': 'remove'})
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

    def test_cart_item_isolation_between_users(self):
        cart_item1 = CartItem.objects.create(user=self.user1, product=self.product, quantity=2)
        self.client.login(username='customer2', password='Password@123')
        # user2 tries to alter user1's cart item -> 404
        response = self.client.post(reverse('orders:update_cart_item', args=[cart_item1.id]), {'action': 'increment'})
        self.assertEqual(response.status_code, 404)

    def test_server_side_calculation_rules(self):
        from orders.views import _calculate_cart_totals
        # Subtotal = 500 (< 1499), Shipping should be 149, Discount should be 0
        cart_item = CartItem.objects.create(user=self.user1, product=self.cheap_product, quantity=1)
        totals = _calculate_cart_totals(CartItem.objects.filter(user=self.user1))
        self.assertEqual(totals['subtotal'], Decimal('500.00'))
        self.assertEqual(totals['shipping_fee'], Decimal('149.00'))
        self.assertEqual(totals['discount'], Decimal('0.00'))
        # Subtotal - Discount = 500. Tax 18% = 90. Total = 500 + 149 + 90 = 739.00
        self.assertEqual(totals['tax'], Decimal('90.00'))
        self.assertEqual(totals['total'], Decimal('739.00'))

        # Subtotal = 2 * 2000 = 4000 (>= 3000), Discount should be 200, Shipping should be FREE (0.00)
        cart_item.product = self.product
        cart_item.quantity = 2
        cart_item.save()
        totals2 = _calculate_cart_totals(CartItem.objects.filter(user=self.user1))
        self.assertEqual(totals2['subtotal'], Decimal('4000.00'))
        self.assertEqual(totals2['shipping_fee'], Decimal('0.00'))
        self.assertEqual(totals2['discount'], Decimal('200.00'))
        # Subtotal - Discount = 3800. Tax 18% = 684. Total = 3800 + 684 = 4484.00
        self.assertEqual(totals2['tax'], Decimal('684.00'))
        self.assertEqual(totals2['total'], Decimal('4484.00'))

    def test_buy_now_flow(self):
        self.client.login(username='customer1', password='Password@123')
        response = self.client.post(reverse('orders:buy_now', args=[self.product.id]), {'quantity': 1})
        self.assertRedirects(response, reverse('orders:checkout'))
        self.assertTrue(CartItem.objects.filter(user=self.user1, product=self.product).exists())

    def test_checkout_validation_failures(self):
        self.client.login(username='customer1', password='Password@123')
        CartItem.objects.create(user=self.user1, product=self.product, quantity=1)

        # Invalid PIN (not 6 digits) and missing confirmation
        response = self.client.post(reverse('orders:checkout'), {
            'full_name': 'Test Cust',
            'email': 'cust1@example.com',
            'phone': '9876543210',
            'shipping_address': 'Flat 101, Main Road',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'pincode': '123', # Invalid!
            'payment_method': 'cod',
            'confirm_order': '0', # Invalid!
        })
        self.assertEqual(response.status_code, 200)
        # Order should NOT have been created
        self.assertEqual(Order.objects.filter(user=self.user1).count(), 0)

    def test_secure_order_creation_atomic_and_stock_deduction(self):
        self.client.login(username='customer1', password='Password@123')
        CartItem.objects.create(user=self.user1, product=self.product, quantity=3, buy_and_install=True)

        initial_stock = self.product.stock_quantity # 10

        response = self.client.post(reverse('orders:checkout'), {
            'full_name': 'Customer One',
            'email': 'cust1@example.com',
            'phone': '9876543210',
            'shipping_address': 'Flat 101, Residency Road',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'pincode': '560001',
            'payment_method': 'simulated_upi',
            'demo_payment_status': 'success',
            'confirm_order': '1',
            'install_vehicle': 'Hyundai Creta 1.5 [KA01AB1234]',
        })
        self.assertEqual(response.status_code, 302)

        order = Order.objects.filter(user=self.user1).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.payment_status, 'Paid (Demo Simulated Gateway)')

        # Verify stock decrement
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock - 3)

        # Verify InventoryRecord audit trail
        audit = InventoryRecord.objects.filter(product=self.product, change_type='sale').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.quantity, -3)

        # Verify InstallationRequest was created
        install_req = InstallationRequest.objects.filter(user=self.user1, product_name=self.product.name).first()
        self.assertIsNotNone(install_req)

        # Verify cart items cleared
        self.assertEqual(CartItem.objects.filter(user=self.user1).count(), 0)

    def test_order_cancellation_and_atomic_stock_restoration(self):
        order = Order.objects.create(
            user=self.user1,
            full_name='Customer One',
            email='cust1@example.com',
            phone='9876543210',
            shipping_address='Road 1',
            city='Delhi',
            state='Delhi',
            pincode='110001',
            subtotal=Decimal('2000.00'),
            total_amount=Decimal('2000.00'),
            status='confirmed',
            payment_status='Paid (Demo Simulated Gateway)'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            product_sku=self.product.sku,
            unit_price=Decimal('2000.00'),
            quantity=2,
            total_price=Decimal('4000.00')
        )
        # Deduct stock first to simulate purchased state
        self.product.stock_quantity = 8
        self.product.save()

        self.client.login(username='customer1', password='Password@123')
        cancel_response = self.client.post(reverse('orders:cancel_order', args=[order.order_number]))
        self.assertEqual(cancel_response.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')

        # Stock should be restored: 8 + 2 = 10
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

        # Check restock audit record
        restock_audit = InventoryRecord.objects.filter(product=self.product, change_type='cancellation_restock').first()
        self.assertIsNotNone(restock_audit)
        self.assertEqual(restock_audit.quantity, 2)

    def test_customer_order_privacy(self):
        order = Order.objects.create(
            user=self.user1,
            full_name='Customer One',
            email='cust1@example.com',
            shipping_address='Road 1',
            city='Delhi',
            state='Delhi',
            pincode='110001',
            subtotal=Decimal('2000.00'),
            total_amount=Decimal('2000.00'),
            status='confirmed'
        )

        # Log in as user2
        self.client.login(username='customer2', password='Password@123')
        # Try to view user1's order detail -> 404
        response_detail = self.client.get(reverse('orders:order_detail', args=[order.order_number]))
        self.assertEqual(response_detail.status_code, 404)

        # Try to view user1's confirmation -> redirected to history with error
        response_conf = self.client.get(reverse('orders:order_confirmation', args=[order.order_number]))
        self.assertRedirects(response_conf, reverse('orders:order_history'))
