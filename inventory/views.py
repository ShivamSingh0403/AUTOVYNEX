from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, ProductCategory, Brand, ProductFitment, WishlistItem
from vehicles.models import VehicleVariant


def shop_list(request):
    products = Product.objects.filter(is_active=True).select_related('category', 'brand')

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(sku__icontains=q) |
            Q(short_description__icontains=q) |
            Q(brand__name__icontains=q) |
            Q(category__name__icontains=q)
        )

    # 2. Category Filter
    category_slug = request.GET.get('category', '').strip()
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(ProductCategory, slug=category_slug)
        products = products.filter(category=selected_category)

    # 3. Brand Filter
    brand_slug = request.GET.get('brand', '').strip()
    selected_brand = None
    if brand_slug:
        selected_brand = get_object_or_404(Brand, slug=brand_slug)
        products = products.filter(brand=selected_brand)

    # 4. Price Range Filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and min_price.isdigit():
        products = products.filter(price__gte=int(min_price))
    if max_price and max_price.isdigit():
        products = products.filter(price__lte=int(max_price))

    # 5. Vehicle Compatibility Filter (Active Session Vehicle)
    selected_variant_id = request.session.get('selected_variant_id')
    active_vehicle = None
    compat_product_ids = set()
    if selected_variant_id:
        try:
            active_vehicle = VehicleVariant.objects.select_related('model__make').get(pk=selected_variant_id)
            compat_product_ids = set(ProductFitment.objects.filter(
                variant=active_vehicle,
                fitment_status__in=['compatible', 'universal']
            ).values_list('product_id', flat=True))
            
            # If user explicitly filtered by "compatible only"
            if request.GET.get('compatible_only') == '1':
                products = products.filter(id__in=compat_product_ids)
        except VehicleVariant.DoesNotExist:
            pass

    # 6. Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'discount':
        products = products.filter(discount_price__isnull=False).order_by('-discount_price')
    else:
        products = products.order_by('-is_featured', '-created_at')

    # 7. Pagination (16 products per page)
    paginator = Paginator(products, 16)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Categories and Brands for sidebar filters
    all_categories = ProductCategory.objects.all().order_by('name')
    all_brands = Brand.objects.all().order_by('name')

    # User wishlist IDs if logged in
    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True))

    context = {
        'page_obj': page_obj,
        'categories': all_categories,
        'brands': all_brands,
        'selected_category': selected_category,
        'selected_brand': selected_brand,
        'q': q,
        'sort_by': sort_by,
        'min_price': min_price,
        'max_price': max_price,
        'active_vehicle': active_vehicle,
        'compat_product_ids': compat_product_ids,
        'wishlist_ids': wishlist_ids,
        'total_results': paginator.count,
    }
    return render(request, 'inventory/shop.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related('category', 'brand'), slug=slug)
    
    # Related products from same category
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(pk=product.pk)[:4]

    # Active vehicle fitment check
    selected_variant_id = request.session.get('selected_variant_id')
    active_vehicle = None
    fitment_status = 'not_selected'
    fitment_record = None

    if selected_variant_id:
        try:
            active_vehicle = VehicleVariant.objects.select_related('model__make').get(pk=selected_variant_id)
            fitment_record = ProductFitment.objects.filter(product=product, variant=active_vehicle).first()
            if fitment_record:
                fitment_status = fitment_record.fitment_status
            elif not ProductFitment.objects.filter(product=product).exists():
                fitment_status = 'unverified'
            else:
                fitment_status = 'incompatible'
        except VehicleVariant.DoesNotExist:
            pass

    # All known compatible models for display list
    compatible_fits = ProductFitment.objects.filter(product=product).select_related('variant__model__make')[:12]

    # Check if in user's wishlist
    is_in_wishlist = False
    if request.user.is_authenticated:
        is_in_wishlist = WishlistItem.objects.filter(user=request.user, product=product).exists()

    context = {
        'product': product,
        'related_products': related_products,
        'active_vehicle': active_vehicle,
        'fitment_status': fitment_status,
        'fitment_record': fitment_record,
        'compatible_fits': compatible_fits,
        'is_in_wishlist': is_in_wishlist,
    }
    return render(request, 'inventory/product_detail.html', context)


def search_api(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    matches = Product.objects.filter(
        Q(name__icontains=q) |
        Q(sku__icontains=q) |
        Q(brand__name__icontains=q) |
        Q(category__name__icontains=q),
        is_active=True
    ).select_related('category')[:6]

    results = []
    for item in matches:
        results.append({
            'id': item.id,
            'name': item.name,
            'sku': item.sku,
            'category': item.category.name,
            'price': str(item.final_price),
            'url': f"/shop/product/{item.slug}/",
            'image': item.image.url if item.image else None
        })

    return JsonResponse({'results': results})


@login_required
def wishlist_view(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product__category', 'product__brand')
    return render(request, 'inventory/wishlist.html', {'wishlist_items': items})


@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.delete()
        messages.info(request, f"Removed {product.name} from your wishlist.")
    else:
        messages.success(request, f"Added {product.name} to your wishlist!")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept') == 'application/json':
        wishlist_count = WishlistItem.objects.filter(user=request.user).count()
        return JsonResponse({
            'status': 'success',
            'action': 'added' if created else 'removed',
            'wishlist_count': wishlist_count,
            'message': f"{'Added' if created else 'Removed'} {product.name} {'to' if created else 'from'} your wishlist."
        })

    return redirect(request.META.get('HTTP_REFERER', 'inventory:wishlist'))
