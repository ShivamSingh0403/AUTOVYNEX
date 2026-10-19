"""
Notification & Communication Dispatcher for AUTOVYNEX Missing Part Sourcing.

IMPORTANT NOTICE:
In-app dashboard notifications are created directly in the customer account.
Email notifications use Django's configured mail backend (console logger in local development).
SMS and WhatsApp notifications are clearly identified as demonstration simulations unless
an authenticated external telecommunications gateway is explicitly connected.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from accounts.models import Notification


def send_enquiry_notification(enquiry, event_type, extra_context=None):
    """
    Dispatches customer notification across active communication channels.
    event_type: 'submitted', 'info_required', 'sourcing_update', 'quote_prepared', 'quote_decision', 'completed', 'cancelled'
    """
    extra_context = extra_context or {}
    tracking_url = reverse('enquiries:enquiry_detail', args=[enquiry.reference_code])

    titles = {
        'submitted': f"Part Sourcing Request Received — {enquiry.reference_code}",
        'info_required': f"Additional Information Needed: {enquiry.part_name}",
        'sourcing_update': f"Logistics Update: {enquiry.reference_code}",
        'quote_prepared': f"Official Sourcing Quote Ready: {enquiry.part_name}",
        'quote_accepted': f"Quote Accepted — Sourcing Dispatched: {enquiry.reference_code}",
        'quote_declined': f"Quote Declined for Enquiry {enquiry.reference_code}",
        'completed': f"Sourcing Completed — {enquiry.part_name}",
        'cancelled': f"Sourcing Request Cancelled: {enquiry.reference_code}",
    }

    quote_formatted = f"₹{enquiry.quote_amount:,.2f}" if enquiry.quote_amount is not None else "₹0.00"

    messages = {
        'submitted': (
            f"Your request for '{enquiry.part_name}' ({enquiry.display_vehicle}) has been queued "
            f"with AUTOVYNEX OEM & OES supplier networks under reference {enquiry.reference_code}."
        ),
        'info_required': (
            f"Our sourcing specialists need additional details or photographs to locate '{enquiry.part_name}'. "
            f"Note: {enquiry.customer_notes or 'Please check your enquiry dashboard to upload required details.'}"
        ),
        'sourcing_update': (
            f"Status updated to '{enquiry.get_status_display()}'. {enquiry.customer_notes}"
        ),
        'quote_prepared': (
            f"A verified quote of {quote_formatted} is ready for '{enquiry.part_name}'. "
            f"Brand: {enquiry.quote_brand or 'OEM Certified'} • Delivery: {enquiry.quote_delivery_days}. Review and accept in your dashboard."
        ),
        'quote_accepted': (
            f"You accepted the quote of {quote_formatted} for '{enquiry.part_name}'. Our fulfillment desk is preparing dispatch."
        ),
        'quote_declined': (
            f"You declined the sourcing quote for '{enquiry.part_name}'. The request has been concluded."
        ),
        'completed': (
            f"Sourcing for '{enquiry.part_name}' has been successfully completed. Thank you for choosing AUTOVYNEX."
        ),
        'cancelled': (
            f"Enquiry {enquiry.reference_code} has been cancelled."
        ),
    }

    title = titles.get(event_type, f"Update on Enquiry {enquiry.reference_code}")
    msg = messages.get(event_type, f"Status updated to {enquiry.get_status_display()}.")

    # 1. In-App Notification (If associated with an authenticated customer)
    if enquiry.user:
        Notification.objects.create(
            user=enquiry.user,
            title=title,
            message=msg,
            link=tracking_url,
            notification_type='enquiry',
            is_read=False
        )

    # 2. Email Notification (Console or configured SMTP backend)
    try:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@autovynex.com')
        send_mail(
            subject=f"[AUTOVYNEX] {title}",
            message=(
                f"Hello {enquiry.contact_name},\n\n"
                f"{msg}\n\n"
                f"Enquiry Reference: {enquiry.reference_code}\n"
                f"Vehicle: {enquiry.display_vehicle}\n"
                f"Part: {enquiry.part_name}\n\n"
                f"Track live sourcing progress at:\n"
                f"{tracking_url}\n\n"
                f"Best regards,\n"
                f"AUTOVYNEX Automotive Logistics Network"
            ),
            from_email=from_email,
            recipient_list=[enquiry.contact_email],
            fail_silently=True
        )
    except Exception:
        pass

    return {
        'title': title,
        'message': msg,
        'in_app': bool(enquiry.user),
        'whatsapp_simulated': enquiry.whatsapp_enabled
    }
