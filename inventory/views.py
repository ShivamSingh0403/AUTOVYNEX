from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, ProductCategory, Brand, ProductFitment, ProductImage, WishlistItem
from vehicles.models import VehicleVariant
from services.models import ServiceProvider


def shop_list(request):
    products = Product.objects.filter(is_active=True).select_related('category', 'brand')

    # 1. Search Query
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(sku__icontains=q) |
            Q(short_description__icontains=q) |
            Q(full_description__icontains=q) |
            Q(brand__name__icontains=q) |
            Q(category__name__icontains=q)
        )

    # 2. Category Filter (safe lookup, no 404 on bad user input)
    category_param = request.GET.get('category', '').strip()
    selected_category = None
    if category_param:
        selected_category = ProductCategory.objects.filter(Q(slug=category_param) | Q(name__iexact=category_param)).first()
        if selected_category:
            products = products.filter(category=selected_category)

    # 3. Brand Filter (safe lookup)
    brand_param = request.GET.get('brand', '').strip()
    selected_brand = None
    if brand_param:
        selected_brand = Brand.objects.filter(Q(slug=brand_param) | Q(name__iexact=brand_param)).first()
        if selected_brand:
            products = products.filter(brand=selected_brand)

    # 4. Price Range Filter (robust numeric validation)
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    clean_min = None
    clean_max = None
    if min_price:
        try:
            val = float(min_price)
            if val >= 0:
                clean_min = val
        except (ValueError, TypeError):
            pass
    if max_price:
        try:
            val = float(max_price)
            if val >= 0:
                clean_max = val
        except (ValueError, TypeError):
            pass

    if clean_min is not None and clean_max is not None and clean_min > clean_max:
        clean_min, clean_max = clean_max, clean_min

    if clean_min is not None:
        products = products.filter(price__gte=clean_min)
    if clean_max is not None:
        products = products.filter(price__lte=clean_max)

    # 5. Availability Filter
    in_stock_only = request.GET.get('in_stock') == '1'
    if in_stock_only:
        products = products.filter(stock_quantity__gt=0)

    # 6. Active Session Vehicle & Compatibility Filter
    selected_variant_id = request.session.get('selected_variant_id')
    active_vehicle = None
    compat_product_ids = set()
    all_fitment_product_ids = set()

    if selected_variant_id:
        try:
            active_vehicle = VehicleVariant.objects.select_related('model__make').get(pk=selected_variant_id)
            compat_product_ids = set(ProductFitment.objects.filter(
                variant=active_vehicle,
                fitment_status__in=['compatible', 'universal']
            ).values_list('product_id', flat=True))
            all_fitment_product_ids = set(ProductFitment.objects.values_list('product_id', flat=True).distinct())

            # Filter by compatibility preference
            compatibility_filter = request.GET.get('compatibility', '').strip()
            if request.GET.get('compatible_only') == '1' or compatibility_filter == 'compatible':
                products = products.filter(id__in=compat_product_ids)
            elif compatibility_filter == 'incompatible':
                # Has fitment data but not for this vehicle
                incompat_ids = all_fitment_product_ids - compat_product_ids
                products = products.filter(id__in=incompat_ids)
            elif compatibility_filter == 'unverified':
                # No fitment data exists for product
                products = products.exclude(id__in=all_fitment_product_ids)
        except VehicleVariant.DoesNotExist:
            request.session.pop('selected_variant_id', None)

    # 7. Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'discount':
        products = products.filter(discount_price__isnull=False).order_by('-discount_price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    else:
        products = products.order_by('-is_featured', '-created_at')

    # 8. Pagination (12 products per page for standard 3x4 grid)
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Annotate page products with exact fitment state for template rendering
    for prod in page_obj:
        if active_vehicle:
            if prod.id in compat_product_ids:
                prod.fitment_state = 'compatible'
            elif prod.id in all_fitment_product_ids:
                prod.fitment_state = 'incompatible'
            else:
                prod.fitment_state = 'unverified'
        else:
            prod.fitment_state = 'none'

    # 9. Sidebar Categories and Brands with dynamic counts
    all_categories = ProductCategory.objects.annotate(prod_count=Count('products')).order_by('name')
    all_brands = Brand.objects.annotate(prod_count=Count('products')).order_by('name')

    # 10. Query string preservation for pagination links
    query_dict = request.GET.copy()
    if 'page' in query_dict:
        query_dict.pop('page')
    query_params = query_dict.urlencode()

    # User wishlist IDs
    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True))

    context = {
        'page_obj': page_obj,
        'products': page_obj,
        'categories': all_categories,
        'brands': all_brands,
        'selected_category': selected_category,
        'selected_brand': selected_brand,
        'q': q,
        'sort_by': sort_by,
        'min_price': clean_min if clean_min is not None else '',
        'max_price': clean_max if clean_max is not None else '',
        'in_stock_only': in_stock_only,
        'active_vehicle': active_vehicle,
        'compat_product_ids': compat_product_ids,
        'wishlist_ids': wishlist_ids,
        'total_results': paginator.count,
        'query_params': query_params,
        'compatibility_filter': request.GET.get('compatibility', ''),
    }
    return render(request, 'inventory/shop.html', context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related('gallery_images'),
        slug=slug
    )
    
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

    # All known compatible vehicle models for display list
    compatible_fits = ProductFitment.objects.filter(
        product=product,
        fitment_status__in=['compatible', 'universal']
    ).select_related('variant__model__make')[:16]

    # Image gallery
    gallery_images = product.gallery_images.all()

    # Service providers if installable
    install_providers = []
    if product.is_installable:
        install_providers = ServiceProvider.objects.filter(is_active=True)[:6]

    # User wishlist status
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
        'gallery_images': gallery_images,
        'install_providers': install_providers,
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
    ).select_related('category', 'brand')[:6]

    results = []
    for item in matches:
        results.append({
            'id': item.id,
            'name': item.name,
            'sku': item.sku,
            'brand': item.brand.name,
            'category': item.category.name,
            'price': str(item.final_price),
            'in_stock': item.in_stock,
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
