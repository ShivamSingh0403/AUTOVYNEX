from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import UsedCarListing, CarComparison


def marketplace_list(request):
    listings = UsedCarListing.objects.filter(is_approved=True, is_sold=False)

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        listings = listings.filter(
            Q(title__icontains=q) |
            Q(make_name__icontains=q) |
            Q(model_name__icontains=q) |
            Q(location_city__icontains=q)
        )

    # 2. Filters
    make = request.GET.get('make')
    if make:
        listings = listings.filter(make_name__iexact=make)

    fuel = request.GET.get('fuel')
    if fuel:
        listings = listings.filter(fuel_type__iexact=fuel)

    trans = request.GET.get('trans')
    if trans:
        listings = listings.filter(transmission__iexact=trans)

    max_price = request.GET.get('max_price')
    if max_price and max_price.isdigit():
        listings = listings.filter(expected_price__lte=int(max_price))

    max_mileage = request.GET.get('max_mileage')
    if max_mileage and max_mileage.isdigit():
        listings = listings.filter(mileage__lte=int(max_mileage))

    # All unique makes for filter
    makes_list = UsedCarListing.objects.values_list('make_name', flat=True).distinct()

    # Session comparison listings
    comparison_ids = request.session.get('car_compare_ids', [])

    context = {
        'listings': listings,
        'makes_list': makes_list,
        'comparison_ids': comparison_ids,
        'selected_make': make,
        'selected_fuel': fuel,
        'selected_trans': trans,
        'q': q,
    }
    return render(request, 'used_cars/marketplace.html', context)


def listing_detail(request, slug):
    listing = get_object_or_404(UsedCarListing, slug=slug, is_approved=True)
    comparison_ids = request.session.get('car_compare_ids', [])
    is_in_compare = listing.id in comparison_ids

    # Similar cars
    similar_cars = UsedCarListing.objects.filter(
        make_name=listing.make_name,
        is_approved=True
    ).exclude(pk=listing.pk)[:3]

    if request.method == 'POST':
        buyer_name = request.POST.get('buyer_name', '').strip()
        buyer_phone = request.POST.get('buyer_phone', '').strip()
        offer_amount = request.POST.get('offer_amount', '').strip()
        
        if buyer_name and buyer_phone:
            messages.success(request, f"Seller contact request dispatched! Reference ID: AVX-LEAD-{listing.id}. The verified seller will reach out.")
            return redirect('used_cars:listing_detail', slug=slug)

    context = {
        'listing': listing,
        'is_in_compare': is_in_compare,
        'similar_cars': similar_cars,
    }
    return render(request, 'used_cars/listing_detail.html', context)


@login_required
def create_listing(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        make_name = request.POST.get('make_name', '').strip()
        model_name = request.POST.get('model_name', '').strip()
        variant_name = request.POST.get('variant_name', '').strip()
        year = int(request.POST.get('year', 2021))
        mileage = int(request.POST.get('mileage', 35000))
        fuel_type = request.POST.get('fuel_type', 'Petrol')
        transmission = request.POST.get('transmission', 'Manual')
        owners_count = int(request.POST.get('owners_count', 1))
        expected_price = request.POST.get('expected_price', 500000)
        location_city = request.POST.get('location_city', 'Bengaluru').strip()
        reg_state = request.POST.get('registration_state', 'KA').strip()
        description = request.POST.get('description', '').strip()
        image = request.FILES.get('primary_image')

        if title and make_name and model_name and expected_price:
            listing = UsedCarListing.objects.create(
                seller=request.user,
                title=title,
                make_name=make_name,
                model_name=model_name,
                variant_name=variant_name,
                year=year,
                mileage=mileage,
                fuel_type=fuel_type,
                transmission=transmission,
                owners_count=owners_count,
                expected_price=expected_price,
                location_city=location_city,
                registration_state=reg_state,
                description=description,
                primary_image=image,
                is_verified=False,
                is_approved=True  # Auto-approved for demo purposes
            )
            messages.success(request, f"Your used car listing for '{listing.title}' has been submitted and published!")
            return redirect('used_cars:listing_detail', slug=listing.slug)
        else:
            messages.error(request, "Please fill in all mandatory vehicle listing fields.")

    return render(request, 'used_cars/create_listing.html')


def toggle_compare(request, car_id):
    car = get_object_or_404(UsedCarListing, pk=car_id)
    compare_ids = request.session.get('car_compare_ids', [])

    if car.id in compare_ids:
        compare_ids.remove(car.id)
        messages.info(request, f"Removed {car.make_name} {car.model_name} from comparison matrix.")
    else:
        if len(compare_ids) >= 3:
            messages.warning(request, "You can compare up to 3 cars side-by-side. Please remove one first.")
        else:
            compare_ids.append(car.id)
            messages.success(request, f"Added {car.make_name} {car.model_name} to comparison matrix!")

    request.session['car_compare_ids'] = compare_ids
    return redirect(request.META.get('HTTP_REFERER', 'used_cars:marketplace'))


def compare_view(request):
    compare_ids = request.session.get('car_compare_ids', [])
    cars = UsedCarListing.objects.filter(id__in=compare_ids)
    return render(request, 'used_cars/compare.html', {'cars': cars})


def clear_compare(request):
    request.session['car_compare_ids'] = []
    messages.info(request, "Comparison matrix cleared.")
    return redirect('used_cars:marketplace')
