from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from enquiries.models import MissingPartEnquiry, EnquiryImage, EnquiryStatusHistory


class EnquiriesValidationAndWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_enquiry_submission_with_history(self):
        response = self.client.post(reverse('enquiries:missing_part_request'), {
            'part_name': 'Transmission Control Module',
            'vehicle_details': '2019 Skoda Octavia 1.8 TSI',
            'category': 'Electrical & Sensors',
            'description': 'TCM communication bus error fault code P0700',
            'contact_name': 'Dev Sharma',
            'contact_email': 'dev@example.com',
            'contact_phone': '+91 98765 11122',
            'contact_preference': 'email'
        })
        self.assertEqual(response.status_code, 302)
        enquiry = MissingPartEnquiry.objects.get(part_name='Transmission Control Module')
        self.assertTrue(enquiry.reference_code.startswith('AVX-ENQ-'))
        # Check initial status history record was created
        history = EnquiryStatusHistory.objects.filter(enquiry=enquiry)
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().status, 'submitted')

    def test_enquiry_file_upload_validation_rejects_disallowed_type(self):
        fake_script = SimpleUploadedFile("script.py", b"print('exploit')", content_type="text/x-python")
        response = self.client.post(reverse('enquiries:missing_part_request'), {
            'part_name': 'Suspension Lower Arm',
            'vehicle_details': 'Maruti Suzuki Swift',
            'category': 'Suspension & Steering',
            'description': 'Bent lower control arm after pothole hit',
            'contact_name': 'Rajesh Kumar',
            'contact_email': 'rajesh@example.com',
            'contact_phone': '+91 99999 88888',
            'sample_photo': fake_script
        })
        self.assertEqual(response.status_code, 302)
        # Enquiry should NOT be created due to validation failure
        self.assertFalse(MissingPartEnquiry.objects.filter(part_name='Suspension Lower Arm').exists())

    def test_enquiry_image_model(self):
        enquiry = MissingPartEnquiry.objects.create(
            part_name='Fuel Injector',
            vehicle_details='Mahindra XUV700',
            contact_name='Vijay',
            contact_email='vijay@example.com',
            contact_phone='+91 98765 00000'
        )
        img = EnquiryImage.objects.create(
            enquiry=enquiry,
            caption='Injector nozzle close-up'
        )
        self.assertEqual(enquiry.additional_images.count(), 1)
        self.assertEqual(enquiry.additional_images.first(), img)
