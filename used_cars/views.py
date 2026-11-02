from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse

from .models import (
    UsedCarListing,
    UsedCarImage,
    UsedCarWishlist,
    CarComparison,
    UsedCarEnquiry,
    UsedCarReport,
    UsedCarAdminLog,
    CarValuationRecord
)
from .forms import UsedCarListingForm, UsedCarEnquiryForm, UsedCarReportForm
from .valuation import estimate_resale_value


# ---------------------------------------------------------
# 1. MARKETPLACE HOMEPAGE & ADVANCED SEARCH / FILTERS
# ---------------------------------------------------------
def marketplace_list(request):
    """
    Marketplace homepage and vehicle catalog with server-side multi-filtering,
    sorting, budget presets, and pagination.
    """
    listings = UsedCarListing.objects.filter(is_approved=True, is_sold=False)

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        listings = listings.filter(
            Q(title__icontains=q) |
            Q(make_name__icontains=q) |
            Q(model_name__icontains=q) |
            Q(variant_name__icontains=q) |
            Q(location_city__icontains=q) |
            Q(location_area__icontains=q) |
            Q(description__icontains=q)
        )

    # 2. Filters
    make = request.GET.get('make', '').strip()
    if make:
        listings = listings.filter(make_name__iexact=make)

    model = request.GET.get('model', '').strip()
    if model:
        listings = listings.filter(model_name__icontains=model)

    fuel = request.GET.get('fuel', '').strip()
    if fuel:
        listings = listings.filter(fuel_type__iexact=fuel)

    trans = request.GET.get('trans', '').strip()
    if trans:
        listings = listings.filter(transmission__iexact=trans)

    city = request.GET.get('city', '').strip()
    if city:
        listings = listings.filter(location_city__iexact=city)

    condition = request.GET.get('condition', '').strip()
    if condition:
        listings = listings.filter(condition__iexact=condition)

    # Budget preset filter
    budget = request.GET.get('budget', '').strip()
    if budget == 'under_5':
        listings = listings.filter(expected_price__lte=500000)
    elif budget == '5_10':
        listings = listings.filter(expected_price__gte=500000, expected_price__lte=1000000)
    elif budget == '10_20':
        listings = listings.filter(expected_price__gte=1000000, expected_price__lte=2000000)
    elif budget == 'above_20':
        listings = listings.filter(expected_price__gte=2000000)

    # Explicit Min & Max Price
    min_price = request.GET.get('min_price', '').strip()
    if min_price and min_price.isdigit():
        listings = listings.filter(expected_price__gte=int(min_price))

    max_price = request.GET.get('max_price', '').strip()
    if max_price and max_price.isdigit():
        listings = listings.filter(expected_price__lte=int(max_price))

    # Manufacturing Year
    year = request.GET.get('year', '').strip()
    if year and year.isdigit():
        listings = listings.filter(year__gte=int(year))

    # Max Mileage
    max_mileage = request.GET.get('max_mileage', '').strip()
    if max_mileage and max_mileage.isdigit():
        listings = listings.filter(mileage__lte=int(max_mileage))

    # Owners Count
    owners = request.GET.get('owners', '').strip()
    if owners and owners.isdigit():
        listings = listings.filter(owners_count__lte=int(owners))

    # Listing type: Genuine vs Sample
    listing_type = request.GET.get('listing_type', '').strip()
    if listing_type == 'genuine':
        listings = listings.filter(is_sample_listing=False)
    elif listing_type == 'sample':
        listings = listings.filter(is_sample_listing=True)

    # 3. Sorting Options
    sort = request.GET.get('sort', 'newest').strip()
    if sort == 'price_asc':
        listings = listings.order_by('expected_price')
    elif sort == 'price_desc':
        listings = listings.order_by('-expected_price')
    elif sort == 'year_desc':
        listings = listings.order_by('-year', '-created_at')
    elif sort == 'year_asc':
        listings = listings.order_by('year', '-created_at')
    elif sort == 'mileage_asc':
        listings = listings.order_by('mileage')
    else:
        # Default newest
        listings = listings.order_by('-created_at')

    # Popular Brands for quick clickable chips with counts
    popular_brands = (
        UsedCarListing.objects.filter(is_approved=True, is_sold=False)
        .values('make_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:8]
    )

    # Unique filter options
    makes_list = sorted(list(set(
        UsedCarListing.objects.filter(is_approved=True)
        .values_list('make_name', flat=True)
    )))
    cities_list = sorted(list(set(
        UsedCarListing.objects.filter(is_approved=True)
        .values_list('location_city', flat=True)
    )))

    # Featured cars (e.g. verified or top 3)
    featured_cars = UsedCarListing.objects.filter(is_approved=True, is_sold=False).order_by('-is_verified', '-created_at')[:3]

    # Recently added cars
    recently_added = UsedCarListing.objects.filter(is_approved=True, is_sold=False).order_by('-created_at')[:4]

    # Session comparison listings
    comparison_ids = request.session.get('car_compare_ids', [])

    # User wishlisted car IDs
    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(
            UsedCarWishlist.objects.filter(user=request.user)
            .values_list('listing_id', flat=True)
        )

    # Server-side Pagination
    paginator = Paginator(listings, 9)  # 9 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Build clean querystring without 'page' for pagination links
    params = request.GET.copy()
    if 'page' in params:
        del params['page']
    query_string = params.urlencode()

    has_active_filters = any([
        q, make, model, fuel, trans, city, condition, budget,
        min_price, max_price, year, max_mileage, owners, listing_type
    ])

    context = {
        'page_obj': page_obj,
        'listings': page_obj.object_list,
        'total_count': paginator.count,
        'makes_list': makes_list,
        'cities_list': cities_list,
        'popular_brands': popular_brands,
        'featured_cars': featured_cars,
        'recently_added': recently_added,
        'comparison_ids': comparison_ids,
        'wishlist_ids': wishlist_ids,
        'selected_make': make,
        'selected_model': model,
        'selected_fuel': fuel,
        'selected_trans': trans,
        'selected_city': city,
        'selected_condition': condition,
        'selected_budget': budget,
        'selected_sort': sort,
        'min_price': min_price,
        'max_price': max_price,
        'selected_year': year,
        'max_mileage': max_mileage,
        'selected_owners': owners,
        'listing_type': listing_type,
        'q': q,
        'has_active_filters': has_active_filters,
        'query_string': query_string,
    }
    return render(request, 'used_cars/marketplace.html', context)


# ---------------------------------------------------------
# 2. USED CAR DETAILS PAGE & ENQUIRY WORKFLOW
# ---------------------------------------------------------
def listing_detail(request, slug):
    """
    Detailed vehicle listing view with gallery, specs, seller disclaimer,
    similar cars, enquiry submission, and reporting modal.
    """
    # Allow seller or staff to view even if not published
    listing = get_object_or_404(UsedCarListing, slug=slug)
    
    if not listing.is_publicly_visible:
        if not (request.user.is_authenticated and (request.user == listing.seller or request.user.is_staff)):
            messages.warning(request, "This vehicle listing is currently not available or pending moderation.")
            return redirect('used_cars:marketplace')

    # Increment view count safely
    UsedCarListing.objects.filter(pk=listing.pk).update(views_count=listing.views_count + 1)
    listing.refresh_from_db(fields=['views_count'])

    # Comparison and Wishlist state
    comparison_ids = request.session.get('car_compare_ids', [])
    is_in_compare = listing.id in comparison_ids
    
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = UsedCarWishlist.objects.filter(user=request.user, listing=listing).exists()

    # Gallery images
    gallery_images = listing.images.all()

    # Similar vehicles
    similar_cars = UsedCarListing.objects.filter(
        make_name=listing.make_name,
        is_approved=True,
        is_sold=False
    ).exclude(pk=listing.pk)[:3]

    # If few by make, supplement with similar price segment
    if similar_cars.count() < 3:
        price_min = listing.expected_price * Decimal('0.7')
        price_max = listing.expected_price * Decimal('1.3')
        additional = UsedCarListing.objects.filter(
            expected_price__gte=price_min,
            expected_price__lte=price_max,
            is_approved=True,
            is_sold=False
        ).exclude(pk=listing.pk).exclude(pk__in=[c.pk for c in similar_cars])[:3 - similar_cars.count()]
        similar_cars = list(similar_cars) + list(additional)

    # Forms
    enquiry_form = UsedCarEnquiryForm(initial={
        'sender_name': request.user.get_full_name() if request.user.is_authenticated else '',
        'sender_email': request.user.email if request.user.is_authenticated else '',
    })
    report_form = UsedCarReportForm()

    # Handle Enquiry Submission (POST)
    if request.method == 'POST' and 'submit_enquiry' in request.POST:
        enquiry_form = UsedCarEnquiryForm(request.POST)
        if enquiry_form.is_valid():
            enquiry = enquiry_form.save(commit=False)
            enquiry.listing = listing
            if request.user.is_authenticated:
                enquiry.sender = request.user
            enquiry.save()
            messages.success(
                request,
                f"Your enquiry has been successfully transmitted to the seller! "
                f"Reference Code: {enquiry.reference_code}. Track status in your dashboard."
            )
            return redirect('used_cars:listing_detail', slug=slug)
        else:
            messages.error(request, "Please correct the errors in the enquiry form.")

    # Handle Report Submission (POST)
    if request.method == 'POST' and 'submit_report' in request.POST:
        report_form = UsedCarReportForm(request.POST)
        if report_form.is_valid():
            report = report_form.save(commit=False)
            report.listing = listing
            if request.user.is_authenticated:
                report.reporter = request.user
            report.save()
            messages.info(request, "Thank you. Your report has been submitted to AUTOVYNEX administrators for review.")
            return redirect('used_cars:listing_detail', slug=slug)

    context = {
        'listing': listing,
        'gallery_images': gallery_images,
        'is_in_compare': is_in_compare,
        'is_wishlisted': is_wishlisted,
        'similar_cars': similar_cars,
        'enquiry_form': enquiry_form,
        'report_form': report_form,
    }
    return render(request, 'used_cars/listing_detail.html', context)


# ---------------------------------------------------------
# 3. SELL YOUR CAR — 10-STEP MULTI-STEP SUBMISSION
# ---------------------------------------------------------
@login_required
def create_listing(request):
    """
    10-step multi-step vehicle listing wizard for authenticated sellers.
    Enforces server-side validation and assigns 'pending_review' status.
    """
    if request.method == 'POST':
        form = UsedCarListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            # Default to pending review for staff moderation
            # If seller clicks "Save as Draft", mark draft
            if 'save_as_draft' in request.POST:
                listing.status = 'draft'
                listing.is_approved = False
                action_msg = "saved as Draft. You can review and publish it whenever you are ready."
            else:
                listing.status = 'pending_review'
                listing.is_approved = False
                action_msg = "submitted for moderation! It will be reviewed by our team before going live on the marketplace."

            listing.is_sample_listing = False
            listing.save()

            # Handle gallery photographs upload (multiple images)
            gallery_files = request.FILES.getlist('gallery_images')
            for f in gallery_files:
                if f.size <= 8 * 1024 * 1024:
                    ext = f.name.split('.')[-1].lower()
                    if ext in ['jpg', 'jpeg', 'png', 'webp']:
                        UsedCarImage.objects.create(
                            listing=listing,
                            image=f,
                            photo_type='exterior',
                            caption=listing.title[:50]
                        )

            messages.success(request, f"Your vehicle listing for '{listing.title}' has been {action_msg}")
            return redirect('used_cars:my_listings')
        else:
            messages.error(request, "Please correct the highlighted fields in the listing form.")
    else:
        form = UsedCarListingForm(initial={
            'year': 2022,
            'mileage': 30000,
            'fuel_type': 'Petrol',
            'transmission': 'Manual',
            'condition': 'good',
            'location_city': 'Bengaluru',
            'location_state': 'Karnataka',
            'registration_state': 'Karnataka (KA)',
            'owners_count': 1,
        })

    return render(request, 'used_cars/create_listing.html', {'form': form})


# ---------------------------------------------------------
# 4. SELLER LISTINGS MANAGEMENT & ACTIONS
# ---------------------------------------------------------
@login_required
def my_listings(request):
    """
    Shows all listings submitted by the authenticated user with live statuses.
    """
    user_listings = UsedCarListing.objects.filter(seller=request.user).order_by('-created_at')
    
    # Counts by status
    total = user_listings.count()
    published = user_listings.filter(status='published').count()
    pending = user_listings.filter(status='pending_review').count()
    sold = user_listings.filter(status='sold').count()

    context = {
        'listings': user_listings,
        'total': total,
        'published': published,
        'pending': pending,
        'sold': sold,
    }
    return render(request, 'used_cars/my_listings.html', context)


@login_required
def edit_listing(request, car_id):
    """
    Allow sellers to edit their own listings. Enforces ownership check.
    """
    listing = get_object_or_404(UsedCarListing, pk=car_id)
    if listing.seller != request.user and not request.user.is_staff:
        messages.error(request, "You do not have permission to edit this listing.")
        return redirect('used_cars:marketplace')

    if request.method == 'POST':
        form = UsedCarListingForm(request.POST, request.FILES, instance=listing)
        if form.is_valid():
            updated_listing = form.save(commit=False)
            # If listing was rejected, editing resets it to pending review
            if updated_listing.status == 'rejected':
                updated_listing.status = 'pending_review'
                updated_listing.rejection_reason = ''
            updated_listing.save()

            # Additional gallery images
            gallery_files = request.FILES.getlist('gallery_images')
            for f in gallery_files:
                if f.size <= 8 * 1024 * 1024:
                    UsedCarImage.objects.create(
                        listing=updated_listing,
                        image=f,
                        photo_type='exterior'
                    )

            messages.success(request, f"Listing for '{updated_listing.title}' has been successfully updated!")
            return redirect('used_cars:my_listings')
        else:
            messages.error(request, "Please review the form errors below.")
    else:
        form = UsedCarListingForm(instance=listing)

    context = {
        'form': form,
        'listing': listing,
        'gallery_images': listing.images.all(),
    }
    return render(request, 'used_cars/edit_listing.html', context)


@login_required
def toggle_listing_active(request, car_id):
    """
    Deactivate or reactivate seller listing. Enforces ownership check.
    """
    listing = get_object_or_404(UsedCarListing, pk=car_id)
    if listing.seller != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Unauthorized")

    if listing.status == 'published':
        listing.status = 'inactive'
        listing.is_approved = False
        listing.save()
        messages.info(request, f"Listing '{listing.title}' has been deactivated and is hidden from buyers.")
    elif listing.status == 'inactive':
        listing.status = 'published'
        listing.is_approved = True
        listing.save()
        messages.success(request, f"Listing '{listing.title}' is now reactivated and live!")
    else:
        messages.warning(request, f"Listing is currently '{listing.get_status_display()}' and cannot be toggled.")

    return redirect('used_cars:my_listings')


@login_required
def mark_listing_sold(request, car_id):
    """
    Mark a vehicle listing as Sold. Enforces ownership check.
    """
    listing = get_object_or_404(UsedCarListing, pk=car_id)
    if listing.seller != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Unauthorized")

    listing.status = 'sold'
    listing.is_sold = True
    listing.save()
    messages.success(request, f"Congratulations! Listing '{listing.title}' has been marked as SOLD.")
    return redirect('used_cars:my_listings')


# ---------------------------------------------------------
# 5. CAR COMPARISON MATRIX (UP TO 3 CARS)
# ---------------------------------------------------------
def toggle_compare(request, car_id):
    """
    Add or remove car from comparison matrix (max 3). Supports AJAX or redirect.
    """
    car = get_object_or_404(UsedCarListing, pk=car_id)
    compare_ids = request.session.get('car_compare_ids', [])

    action = 'added'
    if car.id in compare_ids:
        compare_ids.remove(car.id)
        action = 'removed'
        messages.info(request, f"Removed {car.make_name} {car.model_name} from comparison matrix.")
    else:
        if len(compare_ids) >= 3:
            messages.warning(request, "You can compare up to 3 cars side-by-side. Please remove one first.")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Maximum 3 cars in comparison.'}, status=400)
            return redirect(request.META.get('HTTP_REFERER', 'used_cars:marketplace'))
        else:
            compare_ids.append(car.id)
            messages.success(request, f"Added {car.make_name} {car.model_name} to comparison matrix!")

    request.session['car_compare_ids'] = compare_ids

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'action': action,
            'car_id': car.id,
            'compare_count': len(compare_ids),
        })

    return redirect(request.META.get('HTTP_REFERER', 'used_cars:marketplace'))


def compare_view(request):
    """
    Side-by-side comparison matrix for up to three vehicles, highlighting
    spec differences and displaying 'Not provided' where data is unavailable.
    """
    compare_ids = request.session.get('car_compare_ids', [])
    cars = list(UsedCarListing.objects.filter(id__in=compare_ids))

    # Helper function to check if row values differ across cars
    def check_diff(accessor):
        if len(cars) <= 1:
            return False
        vals = [accessor(c) for c in cars]
        return len(set(vals)) > 1

    diff_matrix = {
        'make_model': check_diff(lambda c: f"{c.make_name} {c.model_name}"),
        'year': check_diff(lambda c: c.year),
        'price': check_diff(lambda c: float(c.expected_price)),
        'fuel': check_diff(lambda c: c.fuel_type),
        'trans': check_diff(lambda c: c.transmission),
        'mileage': check_diff(lambda c: c.mileage),
        'owners': check_diff(lambda c: c.owners_count if c.owners_count else 'Not provided'),
        'condition': check_diff(lambda c: c.condition),
        'city': check_diff(lambda c: c.location_city),
    }

    context = {
        'cars': cars,
        'diff_matrix': diff_matrix,
        'empty_slots': range(max(0, 3 - len(cars))),
    }
    return render(request, 'used_cars/compare.html', context)


def clear_compare(request):
    request.session['car_compare_ids'] = []
    messages.info(request, "Comparison matrix cleared.")
    return redirect('used_cars:marketplace')


# ---------------------------------------------------------
# 6. USED CAR WISHLIST
# ---------------------------------------------------------
@login_required
def wishlist_view(request):
    """
    Customer saved vehicles wishlist. Shows live statuses (published, sold, inactive).
    """
    wishlist_items = (
        UsedCarWishlist.objects.filter(user=request.user)
        .select_related('listing')
        .order_by('-added_at')
    )

    context = {
        'wishlist_items': wishlist_items,
        'total_count': wishlist_items.count(),
    }
    return render(request, 'used_cars/wishlist.html', context)


@login_required
def toggle_wishlist(request, car_id):
    """
    Add or remove a vehicle listing from authenticated user's wishlist.
    """
    listing = get_object_or_404(UsedCarListing, pk=car_id)
    item, created = UsedCarWishlist.objects.get_or_create(user=request.user, listing=listing)

    if not created:
        item.delete()
        saved = False
        msg = f"Removed '{listing.title}' from your saved wishlist."
    else:
        saved = True
        msg = f"Saved '{listing.title}' to your wishlist!"

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'saved': saved,
            'car_id': listing.id,
            'message': msg,
        })

    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'used_cars:marketplace'))


# ---------------------------------------------------------
# 7. CAR RESALE VALUATION CALCULATOR
# ---------------------------------------------------------
def valuation_view(request):
    """
    Interactive car resale valuation calculator powered by transparent,
    rule-based industry algorithms and actual marketplace context.
    """
    result = None
    saved_record = None

    if request.method == 'POST':
        make_name = request.POST.get('make_name', '').strip()
        model_name = request.POST.get('model_name', '').strip()
        variant_name = request.POST.get('variant_name', '').strip()
        year = int(request.POST.get('year', 2022))
        fuel_type = request.POST.get('fuel_type', 'Petrol').strip()
        transmission = request.POST.get('transmission', 'Manual').strip()
        mileage = int(request.POST.get('mileage', 35000))
        owners_count = int(request.POST.get('owners_count', 1))
        condition = request.POST.get('condition', 'good').strip()
        city = request.POST.get('city', 'Bengaluru').strip()
        orig_price = request.POST.get('original_price', '').strip()
        user_orig = float(orig_price) if orig_price and orig_price.replace('.', '', 1).isdigit() else None

        if make_name and model_name and year:
            result = estimate_resale_value(
                make_name=make_name,
                model_name=model_name,
                year=year,
                variant_name=variant_name,
                fuel_type=fuel_type,
                transmission=transmission,
                mileage=mileage,
                owners_count=owners_count,
                condition=condition,
                city=city,
                user_orig_price=user_orig
            )

            # Persist valuation record
            saved_record = CarValuationRecord.objects.create(
                user=request.user if request.user.is_authenticated else None,
                make_name=make_name,
                model_name=model_name,
                variant_name=variant_name,
                year=year,
                mileage=mileage,
                fuel_type=fuel_type,
                transmission=transmission,
                owners_count=owners_count,
                condition=condition,
                city=city,
                original_price=user_orig,
                estimated_price_min=result['estimated_min'],
                estimated_price_max=result['estimated_max'],
                fair_market_value=result['fair_market_value'],
                factors_summary=result['factors_json'],
                comparable_count=result['comparables_count'],
                comparable_avg_price=result['comparables_avg'],
                is_estimate_only=True
            )

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'estimated_min': result['estimated_min'],
                    'estimated_max': result['estimated_max'],
                    'fair_market_value': result['fair_market_value'],
                    'factors': result['factors'],
                    'limitations': result['limitations'],
                    'next_steps': result['next_steps'],
                    'market_note': result['market_context_note'],
                })

    # Valuation history for authenticated user
    history = []
    if request.user.is_authenticated:
        history = CarValuationRecord.objects.filter(user=request.user).order_by('-created_at')[:5]

    context = {
        'result': result,
        'saved_record': saved_record,
        'history': history,
    }
    return render(request, 'used_cars/valuation.html', context)


# ---------------------------------------------------------
# 8. SELLER & BUYER ENQUIRY TRACKING
# ---------------------------------------------------------
@login_required
def my_received_enquiries(request):
    """
    Sellers can review enquiries received across all of their car listings,
    update follow-up statuses, and record notes.
    """
    enquiries = (
        UsedCarEnquiry.objects.filter(listing__seller=request.user)
        .select_related('listing', 'sender')
        .order_by('-created_at')
    )

    context = {
        'enquiries': enquiries,
    }
    return render(request, 'used_cars/my_enquiries.html', context)


@login_required
def update_enquiry_status(request, enquiry_id):
    """
    Update status of an enquiry received by the seller.
    """
    enquiry = get_object_or_404(UsedCarEnquiry, pk=enquiry_id)
    if enquiry.listing.seller != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Unauthorized")

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        seller_reply = request.POST.get('seller_reply', '').strip()
        seller_notes = request.POST.get('seller_notes', '').strip()

        if new_status in dict(UsedCarEnquiry.STATUS_CHOICES):
            enquiry.status = new_status
        if seller_reply:
            enquiry.seller_reply = seller_reply
        if seller_notes:
            enquiry.seller_notes = seller_notes
        enquiry.save()
        messages.success(request, f"Enquiry {enquiry.reference_code} updated successfully.")

    return redirect('used_cars:my_received_enquiries')


@login_required
def my_sent_enquiries(request):
    """
    Buyers can track the status of all enquiries they have submitted on used cars.
    """
    enquiries = (
        UsedCarEnquiry.objects.filter(sender=request.user)
        .select_related('listing')
        .order_by('-created_at')
    )

    context = {
        'enquiries': enquiries,
    }
    return render(request, 'used_cars/my_sent_enquiries.html', context)
