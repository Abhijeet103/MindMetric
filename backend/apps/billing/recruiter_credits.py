"""Per-candidate credits for the recruiter workspace.

Each candidate who starts a recruiter assessment uses one credit. Credits come
in lots (welcome grant, purchase, manual grant) that each expire after a year;
usage always draws from the lot that expires soonest. Purchases are one-time
PayPal orders charged in USD, with the same regional discounts as student passes.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from backend.apps.accounts.models import User

from .models import (
    RECRUITER_CREDIT_VALIDITY_DAYS,
    RECRUITER_WELCOME_CREDITS,
    RecruiterCreditLot,
    RecruiterCreditPurchase,
    RecruiterCreditPurchaseStatus,
    RecruiterCreditSource,
    RecruiterPriceTier,
    format_money,
)
from .regions import pricing_region_for_country
from .services import (
    BillingConfigurationError,
    BillingWebhookError,
    _build_absolute_url,
    _completed_paypal_capture,
    _paypal_request,
    get_paypal_order,
    paypal_is_configured,
)

logger = logging.getLogger(__name__)

MIN_PURCHASE = 10
MAX_PURCHASE = 5000
CURRENCY = "USD"
ORDER_KIND = "recruiter_credits"
# Same regional ladder as student passes: India and Latin America about half
# price, the rest of Europe about 30% lower.
REGIONAL_MULTIPLIERS = {"IN": Decimal("0.5"), "LA": Decimal("0.5"), "EE": Decimal("0.7")}


class RecruiterCreditError(Exception):
    """A purchase or usage request that cannot be completed as asked."""


# ------------------------------------------------------------------ pricing
@dataclass(frozen=True)
class TierPrice:
    name: str
    min_candidates: int
    max_candidates: int | None
    unit_price: Decimal

    @property
    def unit_display(self) -> str:
        return format_money(CURRENCY, self.unit_price)

    @property
    def range_display(self) -> str:
        if self.max_candidates is None:
            return f"{self.min_candidates:,}+ candidates"
        return f"{self.min_candidates:,}–{self.max_candidates:,} candidates"


@dataclass(frozen=True)
class Quote:
    candidates: int
    tier: TierPrice
    total: Decimal
    pricing_region: str

    @property
    def total_display(self) -> str:
        return format_money(CURRENCY, self.total)


def _regional_price(price: Decimal, region: str) -> Decimal:
    return (price * REGIONAL_MULTIPLIERS.get(region, Decimal("1"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def tier_prices(country_code: str | None = None) -> list[TierPrice]:
    region = pricing_region_for_country(country_code)
    return [
        TierPrice(tier.name, tier.min_candidates, tier.max_candidates, _regional_price(tier.price_per_candidate, region))
        for tier in RecruiterPriceTier.objects.filter(is_active=True).order_by("min_candidates")
    ]


def quote(candidates: int, country_code: str | None = None) -> Quote:
    if not isinstance(candidates, int) or isinstance(candidates, bool):
        raise RecruiterCreditError("Enter a whole number of candidates.")
    if candidates < MIN_PURCHASE:
        raise RecruiterCreditError(f"The minimum purchase is {MIN_PURCHASE} candidates.")
    if candidates > MAX_PURCHASE:
        raise RecruiterCreditError(f"For more than {MAX_PURCHASE:,} candidates, email support@mindmetric.store for a custom quote.")
    for tier in tier_prices(country_code):
        if candidates >= tier.min_candidates and (tier.max_candidates is None or candidates <= tier.max_candidates):
            total = (tier.unit_price * candidates).quantize(Decimal("0.01"))
            return Quote(candidates, tier, total, pricing_region_for_country(country_code))
    raise RecruiterCreditError("Recruiter pricing is not available right now. Email support@mindmetric.store.")


# ------------------------------------------------------------------ balance
def active_lots(user: User):
    return RecruiterCreditLot.objects.filter(recruiter=user, remaining__gt=0, expires_at__gt=timezone.now())


def credit_balance(user: User) -> int:
    return active_lots(user).aggregate(total=Sum("remaining"))["total"] or 0


def grant_welcome_credits(user: User) -> bool:
    """Give a recruiter their one-time free credits. Safe to call repeatedly."""
    if not user.is_recruiter or RecruiterCreditLot.objects.filter(recruiter=user, source=RecruiterCreditSource.WELCOME).exists():
        return False
    try:
        with transaction.atomic():
            RecruiterCreditLot.objects.create(
                recruiter=user, source=RecruiterCreditSource.WELCOME, quantity=RECRUITER_WELCOME_CREDITS,
                remaining=RECRUITER_WELCOME_CREDITS, expires_at=timezone.now() + timedelta(days=RECRUITER_CREDIT_VALIDITY_DAYS),
                note="Free credits for new recruiter accounts",
            )
    except IntegrityError:
        return False  # A concurrent request granted them first.
    return True


def consume_credit(recruiter: User) -> RecruiterCreditLot:
    """Take one credit from the soonest-expiring lot. Call inside a transaction."""
    lot = active_lots(recruiter).select_for_update().order_by("expires_at", "pk").first()
    if lot is None:
        raise RecruiterCreditError("This assessment is temporarily unavailable. Please contact the recruiter who shared it.")
    lot.remaining -= 1
    lot.save(update_fields=["remaining"])
    return lot


# ------------------------------------------------------------------ PayPal
def _custom_id(purchase: RecruiterCreditPurchase) -> str:
    return json.dumps({"kind": ORDER_KIND, "purchase_id": purchase.pk}, separators=(",", ":"))


def create_credit_order(user: User, candidates: int, *, base_url: str, country_code: str | None, tenant=None) -> str:
    """Create a PayPal order for a credit pack and return the approval URL."""
    if not user.is_recruiter:
        raise RecruiterCreditError("Only recruiter accounts can buy candidate credits.")
    if not paypal_is_configured():
        raise BillingConfigurationError("Online payment is not available right now. Email support@mindmetric.store to buy credits.")
    priced = quote(candidates, country_code)
    with transaction.atomic():
        purchase = RecruiterCreditPurchase.objects.create(
            recruiter=user, tenant=tenant, candidates=candidates, tier_name=priced.tier.name, unit_price=priced.tier.unit_price,
            amount=priced.total, currency=CURRENCY, pricing_region=priced.pricing_region,
            provider_order_id=f"pending-{timezone.now().timestamp()}-{user.pk}",
        )
        order = _paypal_request("POST", "/v2/checkout/orders", {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {"currency_code": CURRENCY, "value": f"{priced.total:.2f}"},
                "description": f"MindMetric recruiter credits: {candidates} candidates",
                "custom_id": _custom_id(purchase),
            }],
            "payment_source": {"paypal": {"experience_context": {
                "landing_page": "GUEST_CHECKOUT",
                "return_url": _build_absolute_url(reverse("billing-recruiter-paypal-return"), base_url=base_url),
                "cancel_url": _build_absolute_url(f"{reverse('pages:recruiter-credits')}?checkout=cancelled", base_url=base_url),
                "brand_name": settings.PAYPAL_BRAND_NAME,
                "shipping_preference": "NO_SHIPPING",
                "user_action": "PAY_NOW",
            }}},
        })
        order_id = order.get("id", "")
        if not order_id:
            raise BillingWebhookError("PayPal did not create the order.")
        purchase.provider_order_id = order_id
        purchase.save(update_fields=["provider_order_id"])
    for link in order.get("links", []):
        if link.get("rel") in {"payer-action", "approve"} and link.get("href"):
            logger.info("Created recruiter credit order user=%s candidates=%s order=%s", user.pk, candidates, order_id)
            return link["href"]
    raise BillingWebhookError("PayPal did not return an approval URL for the order.")


def is_credit_order(order_id: str) -> bool:
    return bool(order_id) and RecruiterCreditPurchase.objects.filter(provider_order_id=order_id).exists()


def fulfil_credit_order(order: dict) -> RecruiterCreditPurchase:
    """Add the credits for a completed PayPal order. Idempotent."""
    if order.get("status") != "COMPLETED":
        raise BillingWebhookError("PayPal order is not completed.")
    units = order.get("purchase_units") or []
    if not units:
        raise BillingWebhookError("PayPal order payload is missing purchase units.")
    capture = _completed_paypal_capture(units[0])
    with transaction.atomic():
        purchase = RecruiterCreditPurchase.objects.select_for_update().get(provider_order_id=order.get("id", ""))
        if purchase.status == RecruiterCreditPurchaseStatus.PAID:
            return purchase
        if purchase.status == RecruiterCreditPurchaseStatus.REFUNDED:
            raise BillingWebhookError("This credit purchase was refunded.")
        paid = capture.get("amount") or {}
        if paid.get("currency_code") != purchase.currency or Decimal(paid.get("value") or "0") != purchase.amount:
            raise BillingWebhookError("PayPal captured amount does not match the credit purchase.")
        now = timezone.now()
        purchase.status = RecruiterCreditPurchaseStatus.PAID
        purchase.paid_at = now
        purchase.save(update_fields=["status", "paid_at"])
        RecruiterCreditLot.objects.create(
            recruiter=purchase.recruiter, source=RecruiterCreditSource.PURCHASE, quantity=purchase.candidates,
            remaining=purchase.candidates, expires_at=now + timedelta(days=RECRUITER_CREDIT_VALIDITY_DAYS), purchase=purchase,
        )
    logger.info("Recruiter credit order %s paid: %s credits for user=%s", purchase.provider_order_id, purchase.candidates, purchase.recruiter_id)
    return purchase


def complete_credit_order(order_id: str) -> RecruiterCreditPurchase:
    """Capture (if needed) and fulfil a credit order. Safe to call repeatedly."""
    order = get_paypal_order(order_id)
    if order.get("status") == "APPROVED":
        try:
            _paypal_request("POST", f"/v2/checkout/orders/{order_id}/capture", {})
        except BillingWebhookError as exc:
            if "ORDER_ALREADY_CAPTURED" not in str(exc):
                raise
        order = get_paypal_order(order_id)
    return fulfil_credit_order(order)


def refund_credit_order(order_id: str) -> RecruiterCreditPurchase | None:
    """A full refund or reversal removes the pack's unused credits."""
    with transaction.atomic():
        purchase = RecruiterCreditPurchase.objects.select_for_update().filter(provider_order_id=order_id).first()
        if purchase is None or purchase.status == RecruiterCreditPurchaseStatus.REFUNDED:
            return purchase
        purchase.status = RecruiterCreditPurchaseStatus.REFUNDED
        purchase.save(update_fields=["status"])
        RecruiterCreditLot.objects.filter(purchase=purchase).update(remaining=0)
    logger.info("Recruiter credit order %s refunded; unused credits removed.", order_id)
    return purchase


def reconcile_pending_credit_orders(*, since) -> list[dict]:
    """Safety net behind the return URL and webhooks."""
    outcomes = []
    for purchase in RecruiterCreditPurchase.objects.filter(status=RecruiterCreditPurchaseStatus.PENDING, created_at__gte=since):
        order_id = purchase.provider_order_id
        try:
            order = get_paypal_order(order_id)
            if order.get("status") not in {"COMPLETED", "APPROVED"}:
                outcomes.append({"order_id": order_id, "paypal_status": order.get("status", ""), "action": "skipped"})
                continue
            complete_credit_order(order_id)
            outcomes.append({"order_id": order_id, "paypal_status": order.get("status", ""), "action": "activated"})
        except BillingWebhookError as exc:
            outcomes.append({"order_id": order_id, "paypal_status": "unavailable", "action": "skipped", "detail": str(exc)[:160]})
    return outcomes
