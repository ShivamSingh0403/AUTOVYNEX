from django.urls import path
from . import views

app_name = 'used_cars'

urlpatterns = [
    # Marketplace Homepage & Filters
    path('', views.marketplace_list, name='marketplace'),

    # Sell Your Car (10-Step Submission Wizard)
    path('sell/', views.create_listing, name='create_listing'),

    # Seller Listing Management
    path('my-listings/', views.my_listings, name='my_listings'),
    path('listing/<int:car_id>/edit/', views.edit_listing, name='edit_listing'),
    path('listing/<int:car_id>/toggle-active/', views.toggle_listing_active, name='toggle_listing_active'),
    path('listing/<int:car_id>/mark-sold/', views.mark_listing_sold, name='mark_listing_sold'),

    # Car Comparison Feature
    path('compare/', views.compare_view, name='compare_view'),
    path('compare/clear/', views.clear_compare, name='clear_compare'),
    path('compare/toggle/<int:car_id>/', views.toggle_compare, name='toggle_compare'),

    # Used-Car Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    path('wishlist/toggle/<int:car_id>/', views.toggle_wishlist, name='toggle_wishlist'),

    # Resale Valuation Calculator
    path('valuation/', views.valuation_view, name='valuation_view'),

    # Seller & Buyer Enquiries
    path('my-enquiries/', views.my_received_enquiries, name='my_received_enquiries'),
    path('my-enquiries/<int:enquiry_id>/update/', views.update_enquiry_status, name='update_enquiry_status'),
    path('my-sent-enquiries/', views.my_sent_enquiries, name='my_sent_enquiries'),

    # Listing Detail Page
    path('<slug:slug>/', views.listing_detail, name='listing_detail'),
]
