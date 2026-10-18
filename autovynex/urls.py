"""
AUTOVYNEX Master URL Configuration
The Future of Every Drive.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import custom_admin.views
import inventory.views
import orders.views
import accounts.views

# Customer dashboard namespaced patterns
dashboard_patterns = ([
    path('customer/', custom_admin.views.customer_dashboard, name='customer_dashboard'),
], 'dashboard')

urlpatterns = [
    # 1. Native Django Admin & Custom Admin Center
    path('admin/', admin.site.urls),
    path('custom-admin/', include('custom_admin.urls', namespace='custom_admin')),

    # 2. Customer Dashboard Shortcut
    path('dashboard/', include(dashboard_patterns, namespace='dashboard')),

    # 3. Modular Domain Applications
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('vehicles/', include('vehicles.urls', namespace='vehicles')),
    path('shop/', include('inventory.urls', namespace='inventory')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('garage/', include('garage.urls', namespace='garage')),
    path('services/', include('services.urls', namespace='services')),
    path('enquiries/', include('enquiries.urls', namespace='enquiries')),
    path('used-cars/', include('used_cars.urls', namespace='used_cars')),
    path('assistance/', include('assistance.urls', namespace='assistance')),

    # 4. Direct Navigation Shortcuts (Cart, Checkout, Wishlist, Notifications)
    path('cart/', orders.views.cart_detail, name='cart_direct'),
    path('checkout/', orders.views.checkout_view, name='checkout_direct'),
    path('wishlist/', inventory.views.wishlist_view, name='wishlist_direct'),
    path('notifications/', accounts.views.notifications_view, name='notifications_direct'),

    # 5. Core Marketing, Calculators, AI Help, Legal, and Home
    path('', include('core.urls', namespace='core')),
]

# Custom 404 handler
handler404 = 'core.views.custom_404_view'

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
