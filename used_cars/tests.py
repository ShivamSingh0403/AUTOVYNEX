from decimal import Decimal
import io
from PIL import Image
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile


def get_test_image(name='test.jpg'):
    buf = io.BytesIO()
    img = Image.new('RGB', (60, 60), color='blue')
    img.save(buf, format='JPEG')
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')

from used_cars.models import (
    UsedCarListing,
    UsedCarImage,
    UsedCarWishlist,
    UsedCarEnquiry,
    UsedCarReport,
    UsedCarAdminLog,
    CarValuationRecord
)
from used_cars.valuation import estimate_resale_value


class UsedCarsComprehensiveTestSuite(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.password = 'Password@123'
        self.seller = User.objects.create_user(
            username='seller1', email='seller@example.com', password=self.password, first_name='Arun'
        )
        self.buyer = User.objects.create_user(
            username='buyer1', email='buyer@example.com', password=self.password, first_name='Rohan'
        )
        self.other_user = User.objects.create_user(
            username='stranger', email='stranger@example.com', password=self.password, first_name='Stranger'
        )
        self.staff_admin = User.objects.create_user(
            username='moderator', email='mod@autovynex.com', password=self.password, is_staff=True
        )

        # Baseline published listing
        self.listing = UsedCarListing.objects.create(
            seller=self.seller,
            title='2021 Hyundai Creta SX(O) Turbo Petrol',
            make_name='Hyundai',
            model_name='Creta',
            variant_name='1.4 Turbo SX(O) 7DCT',
            year=2021,
            fuel_type='Petrol',
            transmission='Automatic',
            mileage=32000,
            location_city='Bengaluru',
            location_state='Karnataka',
            registration_state='Karnataka (KA)',
            expected_price=Decimal('1475000.00'),
            condition='excellent',
            owners_count=1,
            description='Single owner, showroom maintained',
            status='published',
            is_approved=True,
            is_verified=True,
            is_sample_listing=False
        )

    # 1. Existing baseline test
    def test_used_car_listing_creation(self):
        self.assertEqual(str(self.listing), f"2021 Hyundai Creta 1.4 Turbo SX(O) 7DCT (₹{self.listing.expected_price:,.0f})")
        self.assertTrue(self.listing.is_verified)
        self.assertEqual(self.listing.status, 'published')
        self.assertTrue(self.listing.is_publicly_visible)

    # 2. Existing baseline core valuation test
    def test_car_valuation_endpoint_and_record_persistence(self):
        response = self.client.post(reverse('core:car_valuation'), {
            'make_name': 'Hyundai',
            'model_name': 'Creta',
            'year': 2021,
            'fuel_type': 'Petrol',
            'transmission': 'Automatic',
            'condition': 'excellent',
            'mileage': 35000,
            'original_price': 1600000
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estimated Fair Market Value')
        self.assertContains(response, 'estimate rather than guaranteed market price')

        records = CarValuationRecord.objects.filter(make_name='Hyundai', model_name='Creta', year=2021)
        self.assertEqual(records.count(), 1)
        record = records.first()
        self.assertGreater(record.estimated_price_min, 0)
        self.assertTrue(record.is_estimate_only)

    # 3. Listing Submission and Moderation Approval Workflow
    def test_listing_approval_workflow(self):
        self.client.login(username=self.seller.username, password=self.password)

        # Submit new listing
        res = self.client.post(reverse('used_cars:create_listing'), {
            'title': '2023 Tata Nexon Fearless DCA',
            'make_name': 'Tata',
            'model_name': 'Nexon',
            'variant_name': 'Fearless DCA',
            'year': 2023,
            'mileage': 18000,
            'fuel_type': 'Petrol',
            'transmission': 'Automatic',
            'condition': 'very_good',
            'owners_count': 1,
            'expected_price': 1250000,
            'location_city': 'Bengaluru',
            'location_state': 'Karnataka',
            'registration_state': 'Karnataka (KA)',
            'description': 'Pristine vehicle, zero scratches, fully dealer serviced.',
            'primary_image': get_test_image('cover.jpg'),
            'submit_for_review': '1'
        })
        self.assertEqual(res.status_code, 302)

        # Listing created as pending_review
        new_car = UsedCarListing.objects.filter(title='2023 Tata Nexon Fearless DCA').first()
        self.assertIsNotNone(new_car)
        self.assertEqual(new_car.status, 'pending_review')
        self.assertFalse(new_car.is_approved)
        self.assertFalse(new_car.is_publicly_visible)

        # Hidden from public marketplace catalog (logout seller to test clean visitor catalog)
        self.client.logout()
        res_public = self.client.get(reverse('used_cars:marketplace'))
        self.assertNotIn(new_car, res_public.context['listings'])
        self.assertNotContains(res_public, '2023 Tata Nexon Fearless DCA')

        # Staff admin approves listing
        self.client.login(username=self.staff_admin.username, password=self.password)

        res_action = self.client.post(reverse('custom_admin:admin_used_car_action', args=[new_car.id]), {
            'action': 'approve',
            'notes': 'Document verified and approved'
        })
        self.assertEqual(res_action.status_code, 302)

        new_car.refresh_from_db()
        self.assertEqual(new_car.status, 'published')
        self.assertTrue(new_car.is_approved)
        self.assertTrue(new_car.is_publicly_visible)

        # Audit log created
        log = UsedCarAdminLog.objects.filter(listing=new_car, action='Approved & Published').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin_user, self.staff_admin)

        # Now visible in public marketplace catalog
        res_public_after = self.client.get(reverse('used_cars:marketplace'))
        self.assertContains(res_public_after, '2023 Tata Nexon Fearless DCA')

    # 4. Listing Ownership Enforcement
    def test_listing_ownership_enforcement(self):
        # Other user attempts to edit seller's listing
        self.client.login(username=self.other_user.username, password=self.password)
        res_edit = self.client.post(reverse('used_cars:edit_listing', args=[self.listing.id]), {
            'title': 'Hacked Listing Title',
            'make_name': 'Hyundai',
            'model_name': 'Creta',
            'year': 2021,
            'mileage': 32000,
            'fuel_type': 'Petrol',
            'transmission': 'Automatic',
            'condition': 'excellent',
            'expected_price': 100000,
            'location_city': 'Bengaluru',
            'location_state': 'Karnataka',
            'registration_state': 'Karnataka (KA)',
            'description': 'Unauthorized modification attempt'
        })
        # Must redirect or block
        self.assertEqual(res_edit.status_code, 302)
        self.listing.refresh_from_db()
        self.assertNotEqual(self.listing.title, 'Hacked Listing Title')

        # Other user attempts to toggle active
        res_toggle = self.client.get(reverse('used_cars:toggle_listing_active', args=[self.listing.id]))
        self.assertEqual(res_toggle.status_code, 403)

        # Legitimate seller edits own listing
        self.client.logout()
        self.client.login(username=self.seller.username, password=self.password)
        res_valid_edit = self.client.post(reverse('used_cars:edit_listing', args=[self.listing.id]), {
            'title': '2021 Hyundai Creta 1.4 Turbo SX(O) - Price Dropped',
            'make_name': 'Hyundai',
            'model_name': 'Creta',
            'variant_name': '1.4 Turbo SX(O)',
            'year': 2021,
            'mileage': 32500,
            'fuel_type': 'Petrol',
            'transmission': 'Automatic',
            'condition': 'excellent',
            'expected_price': 1420000,
            'location_city': 'Bengaluru',
            'location_state': 'Karnataka',
            'registration_state': 'Karnataka (KA)',
            'description': 'Price dropped for quick sale.'
        })
        self.assertEqual(res_valid_edit.status_code, 302)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.expected_price, Decimal('1420000.00'))

    # 5. Search and Advanced Filters
    def test_search_and_advanced_filters(self):
        # Create distinct cars
        UsedCarListing.objects.create(
            seller=self.seller,
            title='2020 Maruti Swift ZXi',
            make_name='Maruti Suzuki',
            model_name='Swift',
            year=2020,
            mileage=45000,
            fuel_type='Petrol',
            transmission='Manual',
            expected_price=Decimal('620000.00'),
            location_city='Delhi',
            status='published',
            is_approved=True
        )
        UsedCarListing.objects.create(
            seller=self.seller,
            title='2022 Toyota Fortuner 4x4 AT',
            make_name='Toyota',
            model_name='Fortuner',
            year=2022,
            mileage=28000,
            fuel_type='Diesel',
            transmission='Automatic',
            expected_price=Decimal('3400000.00'),
            location_city='Mumbai',
            status='published',
            is_approved=True
        )

        # Keyword Search
        res_q = self.client.get(reverse('used_cars:marketplace'), {'q': 'Swift'})
        self.assertContains(res_q, 'Maruti Swift')
        self.assertNotContains(res_q, 'Toyota Fortuner')

        # Make Filter
        res_make = self.client.get(reverse('used_cars:marketplace'), {'make': 'Toyota'})
        self.assertContains(res_make, 'Toyota Fortuner')
        self.assertNotContains(res_make, 'Swift')

        # Fuel Filter
        res_fuel = self.client.get(reverse('used_cars:marketplace'), {'fuel': 'Diesel'})
        self.assertContains(res_fuel, 'Fortuner')
        self.assertNotContains(res_fuel, 'Swift')

        # Budget Filter: '5_10'
        res_budget = self.client.get(reverse('used_cars:marketplace'), {'budget': '5_10'})
        self.assertContains(res_budget, 'Swift')
        self.assertNotContains(res_budget, 'Fortuner')

        # Sorting: price_asc
        res_sort = self.client.get(reverse('used_cars:marketplace'), {'sort': 'price_asc'})
        self.assertEqual(res_sort.status_code, 200)

    # 6. Multiple Image Uploads
    def test_multiple_image_uploads(self):
        img1 = get_test_image('interior.jpg')
        img2 = get_test_image('engine.jpg')

        UsedCarImage.objects.create(listing=self.listing, image=img1, photo_type='interior', caption='Cockpit view')
        UsedCarImage.objects.create(listing=self.listing, image=img2, photo_type='engine', caption='Engine bay')

        self.assertEqual(self.listing.images.count(), 2)
        res = self.client.get(reverse('used_cars:listing_detail', args=[self.listing.slug]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['gallery_images']), 2)
        self.assertContains(res, 'gallery-thumb')

    # 7. Wishlist Creation, Removal and Duplicate Prevention
    def test_wishlist_creation_and_removal(self):
        self.client.login(username=self.buyer.username, password=self.password)

        # 1. Add to wishlist
        res_add = self.client.get(reverse('used_cars:toggle_wishlist', args=[self.listing.id]))
        self.assertEqual(res_add.status_code, 302)
        self.assertTrue(UsedCarWishlist.objects.filter(user=self.buyer, listing=self.listing).exists())

        # Check in wishlist page
        res_view = self.client.get(reverse('used_cars:wishlist_view'))
        self.assertEqual(res_view.status_code, 200)
        self.assertContains(res_view, self.listing.title)

        # 2. Toggle again to remove
        res_remove = self.client.get(reverse('used_cars:toggle_wishlist', args=[self.listing.id]))
        self.assertEqual(res_remove.status_code, 302)
        self.assertFalse(UsedCarWishlist.objects.filter(user=self.buyer, listing=self.listing).exists())

    # 8. Comparison Functionality (Up to 3 Cars)
    def test_comparison_functionality(self):
        car2 = UsedCarListing.objects.create(
            seller=self.seller, title='Car Two', make_name='Tata', model_name='Nexon',
            year=2022, mileage=20000, expected_price=Decimal('1100000.00'), status='published', is_approved=True
        )
        car3 = UsedCarListing.objects.create(
            seller=self.seller, title='Car Three', make_name='Honda', model_name='City',
            year=2021, mileage=30000, expected_price=Decimal('1050000.00'), status='published', is_approved=True
        )
        car4 = UsedCarListing.objects.create(
            seller=self.seller, title='Car Four', make_name='Kia', model_name='Seltos',
            year=2023, mileage=12000, expected_price=Decimal('1600000.00'), status='published', is_approved=True
        )

        # Add 3 cars
        self.client.get(reverse('used_cars:toggle_compare', args=[self.listing.id]))
        self.client.get(reverse('used_cars:toggle_compare', args=[car2.id]))
        self.client.get(reverse('used_cars:toggle_compare', args=[car3.id]))

        # View compare matrix
        res_compare = self.client.get(reverse('used_cars:compare_view'))
        self.assertEqual(res_compare.status_code, 200)
        self.assertContains(res_compare, 'Vehicle Comparison Matrix')
        self.assertContains(res_compare, self.listing.title)
        self.assertContains(res_compare, car2.title)
        self.assertContains(res_compare, car3.title)

        # Attempt to add 4th car
        self.client.get(reverse('used_cars:toggle_compare', args=[car4.id]))
        compare_ids = self.client.session.get('car_compare_ids', [])
        self.assertEqual(len(compare_ids), 3)
        self.assertNotIn(car4.id, compare_ids)

        # Clear comparison
        self.client.get(reverse('used_cars:clear_compare'))
        self.assertEqual(len(self.client.session.get('car_compare_ids', [])), 0)

    # 9. Valuation Calculations & Engine
    def test_valuation_calculations(self):
        res = estimate_resale_value(
            make_name='Tata',
            model_name='Nexon',
            year=2022,
            fuel_type='Petrol',
            transmission='Manual',
            mileage=30000,
            owners_count=1,
            condition='good',
            city='Bengaluru'
        )
        self.assertIn('estimated_min', res)
        self.assertIn('estimated_max', res)
        self.assertIn('fair_market_value', res)
        self.assertGreater(res['estimated_min'], 0)
        self.assertGreater(res['estimated_max'], res['estimated_min'])
        self.assertTrue(len(res['factors']) >= 4)
        self.assertTrue(len(res['limitations']) >= 3)
        self.assertTrue(len(res['next_steps']) >= 2)

        # Test POST to /used-cars/valuation/
        self.client.login(username=self.buyer.username, password=self.password)
        post_res = self.client.post(reverse('used_cars:valuation_view'), {
            'make_name': 'Tata',
            'model_name': 'Nexon',
            'year': 2022,
            'fuel_type': 'Petrol',
            'transmission': 'Manual',
            'mileage': 30000,
            'owners_count': 1,
            'condition': 'good',
            'city': 'Bengaluru'
        })
        self.assertEqual(post_res.status_code, 200)
        self.assertContains(post_res, 'Estimated Fair Market Value')

        # Check valuation record saved for buyer
        saved = CarValuationRecord.objects.filter(user=self.buyer, make_name='Tata', model_name='Nexon').first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.year, 2022)

    # 10. Seller Enquiry Privacy and Workflow
    def test_seller_enquiry_privacy(self):
        # Buyer submits enquiry
        self.client.login(username=self.buyer.username, password=self.password)
        res_post = self.client.post(reverse('used_cars:listing_detail', args=[self.listing.slug]), {
            'submit_enquiry': '1',
            'sender_name': 'Rohan Buyer',
            'sender_email': 'rohan@example.com',
            'sender_phone': '+91 98765 43210',
            'enquiry_type': 'offer',
            'offer_amount': 1400000,
            'message': 'Can I inspect the car this weekend?'
        })
        self.assertEqual(res_post.status_code, 302)

        enquiry = UsedCarEnquiry.objects.filter(listing=self.listing).first()
        self.assertIsNotNone(enquiry)
        self.assertTrue(enquiry.reference_code.startswith('AVX-ENQ-'))
        self.assertEqual(enquiry.status, 'new')

        # Seller logs in and views enquiry
        self.client.logout()
        self.client.login(username=self.seller.username, password=self.password)
        res_seller = self.client.get(reverse('used_cars:my_received_enquiries'))
        self.assertEqual(res_seller.status_code, 200)
        self.assertContains(res_seller, enquiry.reference_code)
        self.assertContains(res_seller, 'Rohan Buyer')

        # Seller updates status
        self.client.post(reverse('used_cars:update_enquiry_status', args=[enquiry.id]), {
            'status': 'contacted',
            'seller_notes': 'Called buyer, scheduled viewing for Sunday 11am'
        })
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, 'contacted')

        # Buyer tracks sent enquiry
        self.client.logout()
        self.client.login(username=self.buyer.username, password=self.password)
        res_buyer = self.client.get(reverse('used_cars:my_sent_enquiries'))
        self.assertEqual(res_buyer.status_code, 200)
        self.assertContains(res_buyer, 'Seller Responded')

        # Stranger attempts to update enquiry status -> Forbidden
        self.client.logout()
        self.client.login(username=self.other_user.username, password=self.password)
        res_stranger = self.client.post(reverse('used_cars:update_enquiry_status', args=[enquiry.id]), {
            'status': 'closed'
        })
        self.assertEqual(res_stranger.status_code, 403)

    # 11. Unauthorized Access Restrictions
    def test_unauthorized_access_restrictions(self):
        # Anonymous user cannot access sell car page
        res_sell = self.client.get(reverse('used_cars:create_listing'))
        self.assertEqual(res_sell.status_code, 302)
        self.assertIn('/accounts/login/', res_sell.url)

        # Normal customer cannot access admin moderation center
        self.client.login(username=self.buyer.username, password=self.password)
        res_admin = self.client.get(reverse('custom_admin:admin_used_cars'))
        self.assertEqual(res_admin.status_code, 302)
        self.assertIn('/accounts/login/', res_admin.url)

    # 12. Sold and Inactive Listing Behavior
    def test_sold_and_inactive_listing_behavior(self):
        self.client.login(username=self.seller.username, password=self.password)

        # Seller marks as sold (follow redirect to consume message)
        res_sold = self.client.get(reverse('used_cars:mark_listing_sold', args=[self.listing.id]), follow=True)
        self.assertEqual(res_sold.status_code, 200)

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, 'sold')
        self.assertTrue(self.listing.is_sold)
        self.assertFalse(self.listing.is_publicly_visible)

        # Removed from public catalog
        res_catalog = self.client.get(reverse('used_cars:marketplace'))
        self.assertNotIn(self.listing, res_catalog.context['listings'])
        self.assertNotContains(res_catalog, self.listing.title)

        # Wishlist shows sold badge
        UsedCarWishlist.objects.create(user=self.buyer, listing=self.listing)
        self.client.logout()
        self.client.login(username=self.buyer.username, password=self.password)
        res_wishlist = self.client.get(reverse('used_cars:wishlist_view'))
        self.assertContains(res_wishlist, 'SOLD OUT')
