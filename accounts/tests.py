from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import CustomerProfile


class AccountsAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_customer_registration_creates_profile(self):
        response = self.client.post(reverse('accounts:register'), {
            'full_name': 'Meera Sen',
            'email': 'meera@example.com',
            'phone': '+91 98450 12345',
            'city': 'Chennai',
            'password': 'SecurePassword@123',
            'confirm_password': 'SecurePassword@123'
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='meera@example.com')
        # Check profile was created
        profile = CustomerProfile.objects.get(user=user)
        self.assertEqual(profile.phone, '+91 98450 12345')
        self.assertEqual(profile.city, 'Chennai')

    def test_password_is_securely_hashed_never_plaintext(self):
        raw_password = 'PlaintextPass@2026'
        user = User.objects.create_user(username='testsec', email='sec@example.com', password=raw_password)
        # Verify user.password is a strong hash and not raw password
        self.assertNotEqual(user.password, raw_password)
        self.assertTrue(user.password.startswith('pbkdf2_sha256$') or user.password.startswith('argon2') or user.password.startswith('bcrypt'))
        self.assertTrue(user.check_password(raw_password))
