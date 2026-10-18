from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from inventory.models import ProductCategory, Brand, Product
from orders.models import CartItem, Order, OrderItem


class OrderAndCartSecurityTests(TestCase):
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
            price=Decimal('1850.00'),
            stock_quantity=5,
            is_active=True
        )

    def test_cart_item_user_isolation(self):
        # user1 creates a cart item
        cart_item1 = CartItem.objects.create(user=self.user1, product=self.product, quantity=2)

        # Login as user2 and attempt to update user1's cart item
        self.client.login(username='customer2', password='Password@123')
        response = self.client.post(
            reverse('orders:update_cart_item', args=[cart_item1.id]),
            {'quantity': 4},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        # Should return 404 because user2 does not own cart_item1
        self.assertEqual(response.status_code, 404)
        cart_item1.refresh_from_db()
        self.assertEqual(cart_item1.quantity, 2)

    def test_cart_quantity_clamping_to_stock(self):
        self.client.login(username='customer1', password='Password@123')
        # Try to add more than available stock (5)
        response = self.client.post(reverse('orders:add_to_cart', args=[self.product.id]), {'quantity': 10})
        self.assertEqual(response.status_code, 302)
        cart_item = CartItem.objects.get(user=self.user1, product=self.product)
        # Should be clamped to max stock (5)
        self.assertEqual(cart_item.quantity, 5)

    def test_order_history_isolation(self):
        # Create order for user1
        order1 = Order.objects.create(
            user=self.user1,
            full_name='Customer One',
            email='cust1@example.com',
            shipping_address='Street 1',
            city='Delhi',
            state='Delhi',
            pincode='110001',
            subtotal=Decimal('1850.00'),
            total_amount=Decimal('1850.00'),
            payment_status='paid'
        )

        # Log in as user2 and view orders
        self.client.login(username='customer2', password='Password@123')
        response = self.client.get(reverse('orders:order_history'))
        self.assertEqual(response.status_code, 200)
        # user1's order must NOT appear in user2's order history
        self.assertNotContains(response, order1.order_number)
