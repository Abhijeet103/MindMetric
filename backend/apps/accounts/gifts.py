from __future__ import annotations

from urllib.parse import urljoin

from django.conf import settings
from django.utils import timezone

from backend.apps.billing.models import Subscription, SubscriptionStatus
from backend.apps.billing.services import calculate_expiry
from backend.apps.pages.emails import build_branded_email
from backend.apps.tenants.services import get_or_create_tenant_user


def grant_one_month_gift(user):
    """Grant or extend a non-renewing monthly admin subscription for a user."""
    now = timezone.now()
    base = user.subscription_expires_at if user.subscription_expires_at and user.subscription_expires_at > now else now
    expiry = calculate_expiry(base, "monthly")
    tenant_user = get_or_create_tenant_user(tenant=user.tenant, user=user)
    subscription = Subscription.objects.filter(user=user, provider="admin").order_by("-updated_at").first()
    if subscription is None:
        subscription = Subscription(user=user, provider="admin")
    subscription.tenant = user.tenant
    subscription.tenant_user = tenant_user
    subscription.plan_code = "monthly"
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.provider_customer_id = ""
    subscription.provider_subscription_id = f"admin-{user.id}-monthly-gift"
    subscription.current_period_start = base
    subscription.current_period_end = expiry
    subscription.save()
    user.role = "paid"
    user.subscription_expires_at = expiry
    user.save(update_fields=["role", "subscription_expires_at"])
    return expiry


def send_one_month_gift_email(*, email: str, first_name: str, expires_at) -> bool:
    site_root = settings.SITE_URL.rstrip("/") + "/"
    practice_url = urljoin(site_root, "practice/")
    dashboard_feedback_url = urljoin(site_root, "dashboard/?feedback=open#feedback-modal")
    expiry_text = timezone.localtime(expires_at).strftime("%B %-d, %Y")
    message = build_branded_email(
        subject="A month of MindMetric access, on us",
        body=(
            f"Hi {first_name or 'there'},\n\n"
            "We’ve gifted you one month of MindMetric paid access in trial mode. "
            "It’s a gift from us: there’s nothing to pay and it will not renew automatically.\n\n"
            f"Your access is available until {expiry_text}. Open your practice portal here:\n"
            f"{practice_url}\n\n"
            "We’d love to hear what you think. Share feedback with our team here:\n"
            f"{dashboard_feedback_url}\n\n"
            "If you have any questions, just reply to this email.\n\n"
            "The MindMetric team"
        ),
        recipient=email,
    )
    return message.send(fail_silently=False) == 1
