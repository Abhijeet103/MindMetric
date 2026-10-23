from django.conf import settings
from urllib.parse import urljoin

from django.core.mail import EmailMultiAlternatives, send_mail
from django.templatetags.static import static
from django.template.loader import render_to_string


def build_branded_email(*, subject, body, recipient, connection=None):
    """Keep admin-authored content plain text and escape it in the HTML layout."""
    site_url = settings.SITE_URL.rstrip("/") + "/"
    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        connection=connection,
    )
    message.attach_alternative(render_to_string("emails/branded_message.html", {
        "subject": subject,
        "body": body,
        "site_url": site_url,
        "logo_url": urljoin(site_url, static("favicons/android-chrome-192x192.png")),
    }), "text/html")
    return message


def send_sale_inquiry_notification(inquiry) -> None:
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return

    contact_label = inquiry.full_name or inquiry.email
    subject = f"New sales inquiry from {contact_label}"
    message = (
        "A new sales inquiry was submitted on MindMetric.\n\n"
        f"Contact name: {inquiry.full_name or 'N/A'}\n"
        f"Email: {inquiry.email}\n"
        f"Phone: {inquiry.phone or 'N/A'}\n"
        f"Organization: {inquiry.organization or 'N/A'}\n"
        f"Team size: {inquiry.team_size or 'N/A'}\n"
        f"Source page: {inquiry.source_page or 'N/A'}\n\n"
        "Message:\n"
        f"{inquiry.message}\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.SALES_INQUIRY_NOTIFICATION_EMAIL],
        fail_silently=False,
    )
