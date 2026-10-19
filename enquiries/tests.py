import os
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from enquiries.models import (
    MissingPartEnquiry,
    EnquiryImage,
    EnquiryStatusHistory,
    generate_unique_reference,
)
from accounts.models import Notification


class MissingPartEnquiryComprehensiveTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Customer A
        self.user_a = User.objects.create_user(
            username='arjun_patel',
            email='arjun@example.com',
            password='TestPassword123!'
        )
        # Customer B
        self.user_b = User.objects.create_user(
            username='rohit_singh',
            email='rohit@example.com',
            password='TestPassword123!'
        )
        # Staff Member
        self.staff_user = User.objects.create_user(
            username='staff_sourcing',
            email='sourcing@autovynex.com',
            password='TestPassword123!',
            is_staff=True
        )

        # Base enquiry created for Customer A
        self.enquiry = MissingPartEnquiry.objects.create(
            user=self.user_a,
            make='Maruti Suzuki',
            model_name='Baleno',
            year=2021,
            fuel_type='Petrol',
            variant_name='Alpha 1.2',
            registration_number='MH02DX1234',
            vin_chassis='MA3EWB21S00123456',
            part_name='Steering Rack Assembly',
            category='suspension_steering',
            brand_preference='OEM Genuine',
            part_number='48500M68P00',
            description='Excessive play in steering rack and abnormal vibration above 60 km/h.',
            urgency='high',
            budget_range='₹10,000 - ₹15,000',
            contact_name='Arjun Patel',
            contact_email='arjun@example.com',
            contact_phone='+91 98765 43210',
            contact_preference='phone',
            whatsapp_enabled=True,
            status='submitted',
            customer_notes='Sourcing initiated.'
        )
        EnquiryStatusHistory.objects.create(
            enquiry=self.enquiry,
            old_status='',
            status='submitted',
            notes='Initial enquiry logged in system.'
        )

    # 1. Unique reference generation
    def test_unique_reference_format_and_uniqueness(self):
        ref1 = generate_unique_reference()
        ref2 = generate_unique_reference()
        self.assertTrue(ref1.startswith('AVX-2026-'))
        self.assertEqual(len(ref1), 15)  # AVX-2026-XXXXXX is 9 + 6 = 15 chars
        self.assertNotEqual(ref1, ref2)

    # 2. Valid enquiry submission via POST
    def test_valid_enquiry_submission(self):
        self.client.login(username='arjun_patel', password='TestPassword123!')
        response = self.client.post(reverse('enquiries:missing_part_request'), {
            'make': 'Hyundai',
            'model_name': 'Creta',
            'year': '2020',
            'fuel_type': 'Diesel',
            'variant_name': 'SX (O) 1.5 CRDi',
            'registration_number': 'DL01AB9999',
            'vin_chassis': 'MALC381CLPM123456',
            'part_name': 'Turbocharger Wastegate Actuator',
            'category': 'engine_mechanical',
            'brand_preference': 'Garrett / OEM',
            'part_number': '28231-2A800',
            'description': 'Underboost code P0299, actuator rod sticking.',
            'urgency': 'critical',
            'budget_range': '₹15,000 - ₹25,000',
            'contact_name': 'Arjun Patel',
            'contact_email': 'arjun@example.com',
            'contact_phone': '+91 98765 43210',
            'contact_preference': 'whatsapp',
            'whatsapp_enabled': '1',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        enq = MissingPartEnquiry.objects.get(part_name='Turbocharger Wastegate Actuator')
        self.assertEqual(enq.user, self.user_a)
        self.assertTrue(enq.reference_code.startswith('AVX-2026-'))
        self.assertEqual(enq.status, 'submitted')
        self.assertEqual(enq.urgency, 'critical')
        self.assertTrue(enq.whatsapp_enabled)
        # Verify status history record created
        self.assertEqual(enq.status_history.count(), 1)
        self.assertEqual(enq.status_history.first().status, 'submitted')
        # Verify in-app notification created
        notif = Notification.objects.filter(user=self.user_a, notification_type='enquiry').first()
        self.assertIsNotNone(notif)
        self.assertIn(enq.reference_code, notif.title)

    # 3. Required field validation rejects incomplete data
    def test_missing_required_fields_rejected(self):
        response = self.client.post(reverse('enquiries:missing_part_request'), {
            'part_name': '',  # Missing required part name
            'description': 'Broken part',
            'contact_name': 'Arjun',
            'contact_email': 'arjun@example.com',
            'contact_phone': '9876543210',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MissingPartEnquiry.objects.filter(description='Broken part').exists())

    # 4. Multiple image upload handling
    def test_multiple_image_upload_saving(self):
        img1 = SimpleUploadedFile("part1.jpg", b"fake_jpeg_content_1", content_type="image/jpeg")
        img2 = SimpleUploadedFile("part2.png", b"fake_png_content_2", content_type="image/png")
        img3 = SimpleUploadedFile("part3.webp", b"fake_webp_content_3", content_type="image/webp")

        response = self.client.post(reverse('enquiries:missing_part_request'), {
            'make': 'Tata',
            'model_name': 'Nexon',
            'year': '2022',
            'fuel_type': 'Petrol',
            'part_name': 'Alternator Decoupler Pulley',
            'category': 'electrical_sensors',
            'description': 'Squealing noise on cold start.',
            'contact_name': 'Arjun',
            'contact_email': 'arjun@example.com',
            'contact_phone': '9876543210',
            'part_images': [img1, img2, img3],
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        enq = MissingPartEnquiry.objects.get(part_name='Alternator Decoupler Pulley')
        self.assertTrue(bool(enq.damaged_part_image))
        # Additional images should contain the other 2 photos
        self.assertEqual(enq.additional_images.count(), 2)

    # 5. Invalid image rejection (disallowed extension & oversized file)
    def test_invalid_image_extension_rejected(self):
        fake_executable = SimpleUploadedFile("exploit.sh", b"echo hack", content_type="application/x-sh")
        response = self.client.post(reverse('enquiries:missing_part_request'), {
            'part_name': 'EGR Valve',
            'description': 'Faulty EGR valve',
            'contact_name': 'Test User',
            'contact_email': 'test@example.com',
            'contact_phone': '9876543210',
            'part_images': [fake_executable],
        })
        self.assertFalse(MissingPartEnquiry.objects.filter(part_name='EGR Valve').exists())

    def test_oversized_image_rejected(self):
        large_bytes = b"x" * (6 * 1024 * 1024)  # 6MB (exceeds 5MB limit)
        oversized_img = SimpleUploadedFile("large_photo.jpg", large_bytes, content_type="image/jpeg")
        response = self.client.post(reverse('enquiries:missing_part_request'), {
            'part_name': 'Brake Booster',
            'description': 'Leaking vacuum diaphragm',
            'contact_name': 'Test User',
            'contact_email': 'test@example.com',
            'contact_phone': '9876543210',
            'part_images': [oversized_img],
        })
        self.assertFalse(MissingPartEnquiry.objects.filter(part_name='Brake Booster').exists())

    # 6. Customer ownership isolation: User B cannot view User A's enquiry
    def test_customer_ownership_privacy_enforced(self):
        self.client.login(username='rohit_singh', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.get(url)
        # Should return 403 Forbidden for unauthorized user
        self.assertEqual(response.status_code, 403)

    # 7. Customer can view their own enquiry
    def test_customer_can_view_own_enquiry(self):
        self.client.login(username='arjun_patel', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.enquiry.reference_code)
        self.assertContains(response, 'Steering Rack Assembly')

    # 8. Staff can view any customer's enquiry
    def test_staff_can_view_any_enquiry(self):
        self.client.login(username='staff_sourcing', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    # 9. Private staff notes are NOT visible to customers
    def test_private_staff_notes_never_leaked_to_customer(self):
        self.enquiry.internal_notes = "CONFIDENTIAL_SUPPLIER_PRICE_RS_1200"
        self.enquiry.customer_notes = "PUBLIC_UPDATE_SEARCHING_PUNE_HUB"
        self.enquiry.save()

        self.client.login(username='arjun_patel', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "CONFIDENTIAL_SUPPLIER_PRICE_RS_1200")
        self.assertContains(response, "PUBLIC_UPDATE_SEARCHING_PUNE_HUB")

    # 10. Customer adds additional information and extra photo
    def test_customer_additional_info_submission(self):
        self.enquiry.status = 'info_required'
        self.enquiry.save()

        extra_photo = SimpleUploadedFile("extra_angle.jpg", b"fake_extra_angle", content_type="image/jpeg")

        self.client.login(username='arjun_patel', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.post(url, {
            'action': 'add_info',
            'additional_info': 'The steering rack has 24 teeth on the pinion shaft.',
            'additional_photos': [extra_photo]
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.enquiry.refresh_from_db()
        self.assertIn('24 teeth on the pinion shaft', self.enquiry.description)
        # Should transition status back to under_review
        self.assertEqual(self.enquiry.status, 'under_review')
        self.assertEqual(self.enquiry.additional_images.count(), 1)

    # 11. Customer cancellation of eligible enquiry
    def test_customer_can_cancel_eligible_enquiry(self):
        self.client.login(username='arjun_patel', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.post(url, {
            'action': 'cancel_enquiry'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, 'cancelled')

    # 12. Customer cannot cancel completed enquiry
    def test_customer_cannot_cancel_completed_enquiry(self):
        self.enquiry.status = 'completed'
        self.enquiry.save()

        self.client.login(username='arjun_patel', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.post(url, {
            'action': 'cancel_enquiry'
        }, follow=True)

        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, 'completed')  # Must remain completed

    # 13. Sourcing quote preparation, expiry, and acceptance workflow
    def test_quote_workflow_accept_and_decline(self):
        # Prepare Quote
        self.enquiry.quote_amount = Decimal('12500.00')
        self.enquiry.quote_brand = 'Maruti Genuine Parts'
        self.enquiry.quote_part_number = '48500M68P00'
        self.enquiry.quote_expires_at = timezone.now() + timedelta(days=7)
        self.enquiry.status = 'quote_prepared'
        self.enquiry.quote_status = 'pending'
        self.enquiry.save()

        self.assertFalse(self.enquiry.is_quote_expired)
        self.assertTrue(self.enquiry.is_quote_available)

        # Customer Accepts Quote
        self.client.login(username='arjun_patel', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.post(url, {
            'action': 'accept_quote'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.quote_status, 'accepted')
        self.assertEqual(self.enquiry.status, 'customer_accepted')
        self.assertIsNotNone(self.enquiry.quote_decision_at)

    def test_expired_quote_cannot_be_accepted(self):
        # Set Quote Expired
        self.enquiry.quote_amount = Decimal('8000.00')
        self.enquiry.quote_expires_at = timezone.now() - timedelta(days=1)  # Expired yesterday
        self.enquiry.status = 'quote_prepared'
        self.enquiry.quote_status = 'pending'
        self.enquiry.save()

        self.assertTrue(self.enquiry.is_quote_expired)

        self.client.login(username='arjun_patel', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.post(url, {
            'action': 'accept_quote'
        }, follow=True)

        self.enquiry.refresh_from_db()
        # Must not be accepted
        self.assertNotEqual(self.enquiry.quote_status, 'accepted')
        self.assertEqual(self.enquiry.status, 'quote_prepared')

    # 14. Customer declines quote
    def test_customer_can_decline_quote(self):
        self.enquiry.quote_amount = Decimal('14000.00')
        self.enquiry.quote_expires_at = timezone.now() + timedelta(days=5)
        self.enquiry.status = 'quote_prepared'
        self.enquiry.save()

        self.client.login(username='arjun_patel', password='TestPassword123!')
        url = reverse('enquiries:enquiry_detail', args=[self.enquiry.reference_code])
        response = self.client.post(url, {
            'action': 'decline_quote'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.quote_status, 'declined')

    # 15. Status transition permission check
    def test_status_transition_permissions(self):
        # Customer cannot transition to staff status like 'sourcing' or 'completed'
        self.assertFalse(self.enquiry.can_transition_to('sourcing', self.user_a))
        self.assertFalse(self.enquiry.can_transition_to('completed', self.user_a))
        # Customer CAN cancel when in submitted status
        self.assertTrue(self.enquiry.can_transition_to('cancelled', self.user_a))
        # Staff member CAN transition to 'sourcing'
        self.assertTrue(self.enquiry.can_transition_to('sourcing', self.staff_user))
