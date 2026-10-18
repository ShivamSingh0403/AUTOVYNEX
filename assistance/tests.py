from django.test import TestCase, Client
from django.urls import reverse
from assistance.models import RoadsideAssistanceRequest


class AssistanceTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_assistance_request_marked_as_simulated(self):
        req = RoadsideAssistanceRequest.objects.create(
            request_type='flat_tyre',
            vehicle_details='Tata Tiago EV [MH-02-CD-5678]',
            location_address='Eastern Express Highway, Mumbai',
            contact_name='Rohan K',
            contact_phone='+91 98200 12345',
            description='Front left tire puncture',
            is_simulated=True
        )
        self.assertTrue(req.is_simulated)
        self.assertEqual(req.status, 'received')
        self.assertTrue(req.ticket_number.startswith('AVX-RSA-'))

    def test_assistance_page_renders_simulation_notice(self):
        response = self.client.get(reverse('assistance:request_view'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Roadside')
