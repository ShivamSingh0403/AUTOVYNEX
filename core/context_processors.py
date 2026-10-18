from inventory.models import ProductCategory, WishlistItem
from vehicles.models import VehicleMake, VehicleVariant
from orders.models import CartItem
from garage.models import CustomerVehicle
from accounts.models import Notification


def global_context(request):
    cart_count = 0
    wishlist_count = 0
    notifications_count = 0
    selected_vehicle = None

    # Cart item count
    try:
        if request.user.is_authenticated:
            cart_count = sum(CartItem.objects.filter(user=request.user).values_list('quantity', flat=True))
            wishlist_count = WishlistItem.objects.filter(user=request.user).count()
            notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
        elif request.session.session_key:
            cart_count = sum(CartItem.objects.filter(session_key=request.session.session_key).values_list('quantity', flat=True))
    except Exception:
        cart_count = 0

    # Selected Vehicle logic
    selected_variant_id = request.session.get('selected_variant_id')
    if selected_variant_id:
        try:
            selected_vehicle = VehicleVariant.objects.select_related('model__make').get(pk=selected_variant_id)
        except VehicleVariant.DoesNotExist:
            request.session.pop('selected_variant_id', None)

    if not selected_vehicle and request.user.is_authenticated:
        try:
            if hasattr(request.user, 'profile') and request.user.profile.selected_vehicle:
                selected_vehicle = request.user.profile.selected_vehicle
                request.session['selected_variant_id'] = selected_vehicle.id
            else:
                default_gv = CustomerVehicle.objects.filter(user=request.user, is_default=True).select_related('variant__model__make').first()
                if default_gv:
                    selected_vehicle = default_gv.variant
                    request.session['selected_variant_id'] = selected_vehicle.id
        except Exception:
            pass

    try:
        categories = ProductCategory.objects.all().order_by('sort_order', 'name')[:12]
        popular_makes = VehicleMake.objects.filter(is_popular=True).order_by('name')[:10]
    except Exception:
        categories = []
        popular_makes = []

    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'notifications_count': notifications_count,
        'selected_vehicle': selected_vehicle,
        'global_categories': categories,
        'popular_makes': popular_makes,
        'BRAND_NAME': 'AUTOVYNEX',
        'BRAND_TAGLINE': 'The Future of Every Drive.',
    }
