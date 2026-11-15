from django.conf import settings
from urllib.parse import urljoin

from django.core.mail import EmailMultiAlternatives, send_mail
from django.templatetags.static import static
from django.template.loader import render_to_string


def campaign_email_initial(kind):
    site_url = settings.SITE_URL.rstrip("/") + "/"
    if kind == "product_update":
        return {
            "subject": "Discover what's new on MindMetric",
            "body": (
                "Hi there,\n\n"
                "Explore MindMetric for practice tests and tools to help you prepare.\n\n"
                "What's new:\n[Add the new tests, features, or improvements here before sending.]\n\n"
                f"Visit MindMetric: {site_url}\n"
                f"Start practising: {urljoin(site_url, 'practice/')}\n\n"
                "We'd love to hear what you think. Just reply to this email."
            ),
        }
    if kind == "feedback_request":
        return {
            "subject": "How can we make MindMetric better for you?",
            "body": (
                "Hi there,\n\n"
                "Have you tried MindMetric? We'd love to hear about your experience. "
                "Tell us what works well, what we could improve, and which tests "
                "or features you'd like us to add next.\n\n"
                f"Share your feedback: {site_url}?feedback=open#feedback-modal\n\n"
                "You can also reply directly to this email. Thank you for helping us improve MindMetric."
            ),
        }
    return {}


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


def send_problem_report_notification(feedback) -> None:
    """Email the team when a student reports a problem, so it is seen quickly."""
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return
    details = "\n".join(f"{key}: {value}" for key, value in (feedback.context or {}).items()) or "N/A"
    send_mail(
        subject=f"Problem reported on MindMetric by {feedback.email}",
        message=(
            "A student reported a problem.\n\n"
            f"Email: {feedback.email}\n"
            f"Page: {feedback.source_page or 'N/A'}\n\n"
            f"Message:\n{feedback.message}\n\n"
            f"Technical details:\n{details}\n"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.SALES_INQUIRY_NOTIFICATION_EMAIL],
        fail_silently=True,
    )


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
