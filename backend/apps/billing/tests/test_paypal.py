import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from backend.apps.accounts.models import UserRole
from backend.apps.billing.models import Subscription, SubscriptionStatus
from backend.apps.billing.services import (
    BillingWebhookError,
    PayPalPaymentPendingError,
    activate_subscription_from_paypal_order,
    capture_paypal_order,
)

User = get_user_model()

PAYPAL_SETTINGS = {
    "PAYPAL_CLIENT_ID": "client",
    "PAYPAL_CLIENT_SECRET": "secret",
    "PAYPAL_WEBHOOK_ID": "webhook",
}
ORDER_ID = "ORDER123"
CAPTURE_ID = "CAPTURE123"


def paypal_order(user, *, capture_status="COMPLETED", captured_value="12.00", currency="GBP"):
    return {
        "id": ORDER_ID,
        "status": "COMPLETED",
        "payer": {"payer_id": "PAYER1"},
        "purchase_units": [
            {
                "amount": {"currency_code": "GBP", "value": "12.00"},
                "custom_id": json.dumps({"user_id": user.id, "plan_code": "monthly"}),
                "payments": {
                    "captures": [
                        {
                            "id": CAPTURE_ID,
                            "status": capture_status,
                            "status_details": {"reason": "PENDING_REVIEW"} if capture_status == "PENDING" else {},
                            "amount": {"currency_code": currency, "value": captured_value},
                        }
                    ]
                },
            }
        ],
    }


@override_settings(**PAYPAL_SETTINGS)
class PayPalActivationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="paypal@example.com", password="secret")
        Subscription.objects.create(
            user=self.user,
            provider="paypal",
            provider_subscription_id=ORDER_ID,
            plan_code="monthly",
            status=SubscriptionStatus.PENDING,
        )

    def test_completed_capture_activates_access(self):
        activate_subscription_from_paypal_order(paypal_order(self.user))

        self.user.refresh_from_db()
        self.assertEqual(self.user.role, UserRole.PAID)
        self.assertIsNotNone(self.user.subscription_expires_at)

    def test_pending_capture_on_completed_order_does_not_grant_access(self):
        with self.assertRaises(PayPalPaymentPendingError):
            activate_subscription_from_paypal_order(paypal_order(self.user, capture_status="PENDING"))

        self.user.refresh_from_db()
        self.assertNotEqual(self.user.role, UserRole.PAID)
        self.assertEqual(Subscription.objects.get(provider_subscription_id=ORDER_ID).status, SubscriptionStatus.PENDING)

    def test_declined_capture_does_not_grant_access(self):
        with self.assertRaises(BillingWebhookError):
            activate_subscription_from_paypal_order(paypal_order(self.user, capture_status="DECLINED"))

        self.user.refresh_from_db()
        self.assertNotEqual(self.user.role, UserRole.PAID)

    def test_mismatched_capture_amount_does_not_grant_access(self):
        for kwargs in ({"captured_value": "1.00"}, {"currency": "USD"}):
            with self.subTest(**kwargs), self.assertRaises(BillingWebhookError):
                activate_subscription_from_paypal_order(paypal_order(self.user, **kwargs))

    def test_already_captured_order_is_loaded_instead_of_failing(self):
        order = paypal_order(self.user)

        def fake_request(method, path, payload=None, **kwargs):
            if path.endswith("/capture"):
                raise BillingWebhookError('PayPal API request failed: {"name":"UNPROCESSABLE_ENTITY","details":[{"issue":"ORDER_ALREADY_CAPTURED"}]}')
            return order

        with patch("backend.apps.billing.services._paypal_request", side_effect=fake_request):
            self.assertEqual(capture_paypal_order(ORDER_ID), order)

    def test_other_capture_errors_still_raise(self):
        with patch(
            "backend.apps.billing.services._paypal_request",
            side_effect=BillingWebhookError("PayPal API request failed: INSTRUMENT_DECLINED"),
        ):
            with self.assertRaises(BillingWebhookError):
                capture_paypal_order(ORDER_ID)


@override_settings(**PAYPAL_SETTINGS)
class PayPalReturnViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="return@example.com", password="secret")
        Subscription.objects.create(
            user=self.user,
            provider="paypal",
            provider_subscription_id=ORDER_ID,
            plan_code="monthly",
            status=SubscriptionStatus.PENDING,
        )
        self.client.force_login(self.user)

    def test_revisiting_return_url_after_capture_keeps_user_paid(self):
        order = paypal_order(self.user)

        def fake_request(method, path, payload=None, **kwargs):
            if path.endswith("/capture"):
                raise BillingWebhookError("PayPal API request failed: ORDER_ALREADY_CAPTURED")
            return order

        with patch("backend.apps.billing.services._paypal_request", side_effect=fake_request):
            response = self.client.get(reverse("billing-paypal-return"), {"token": ORDER_ID})

        self.assertNotIn("cancelled", response["Location"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, UserRole.PAID)

    def test_pending_capture_redirects_to_processing(self):
        with patch(
            "backend.apps.billing.services._paypal_request",
            return_value=paypal_order(self.user, capture_status="PENDING"),
        ):
            response = self.client.get(reverse("billing-paypal-return"), {"token": ORDER_ID})

        self.assertIn("checkout=processing", response["Location"])
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.role, UserRole.PAID)


@override_settings(**PAYPAL_SETTINGS)
class PayPalWebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="webhook@example.com", password="secret")
        now = timezone.now()
        self.subscription = Subscription.objects.create(
            user=self.user,
            provider="paypal",
            provider_subscription_id=ORDER_ID,
            plan_code="monthly",
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        self.user.role = UserRole.PAID
        self.user.subscription_expires_at = self.subscription.current_period_end
        self.user.save(update_fields=["role", "subscription_expires_at"])

    def post_event(self, event, capture_status="REFUNDED"):
        def fake_request(method, path, payload=None, **kwargs):
            if path == "/v1/notifications/verify-webhook-signature":
                return {"verification_status": "SUCCESS"}
            if path == f"/v2/payments/captures/{CAPTURE_ID}":
                return {
                    "id": CAPTURE_ID,
                    "status": capture_status,
                    "supplementary_data": {"related_ids": {"order_id": ORDER_ID}},
                }
            raise AssertionError(f"Unexpected PayPal call {method} {path}")

        with patch("backend.apps.billing.services._paypal_request", side_effect=fake_request):
            return self.client.post(
                reverse("billing-paypal-webhook"),
                data=json.dumps(event),
                content_type="application/json",
            )

    def refund_event(self, event_type="PAYMENT.CAPTURE.REFUNDED"):
        # Refund resources link "up" to their capture instead of naming the order.
        return {
            "event_type": event_type,
            "resource": {
                "id": "REFUND1",
                "links": [{"rel": "up", "href": f"https://api-m.paypal.com/v2/payments/captures/{CAPTURE_ID}"}],
            },
        }

    def assert_revoked(self):
        self.subscription.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.subscription.status, SubscriptionStatus.CANCELED)
        self.assertEqual(self.user.role, UserRole.FREE)
        self.assertIsNone(self.user.subscription_expires_at)

    def test_full_refund_revokes_access(self):
        response = self.post_event(self.refund_event())

        self.assertEqual(response.status_code, 200)
        self.assert_revoked()

    def test_partial_refund_keeps_access(self):
        response = self.post_event(self.refund_event(), capture_status="PARTIALLY_REFUNDED")

        self.assertEqual(response.status_code, 200)
        self.subscription.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.subscription.status, SubscriptionStatus.ACTIVE)
        self.assertEqual(self.user.role, UserRole.PAID)

    def test_reversal_revokes_access(self):
        response = self.post_event(self.refund_event("PAYMENT.CAPTURE.REVERSED"))

        self.assertEqual(response.status_code, 200)
        self.assert_revoked()

    def test_denied_capture_revokes_access(self):
        response = self.post_event(
            {
                "event_type": "PAYMENT.CAPTURE.DENIED",
                "resource": {
                    "id": CAPTURE_ID,
                    "status": "DECLINED",
                    "supplementary_data": {"related_ids": {"order_id": ORDER_ID}},
                },
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assert_revoked()

    def test_revoking_keeps_other_active_access(self):
        other_end = timezone.now() + timedelta(days=10)
        Subscription.objects.create(
            user=self.user,
            provider="stripe",
            provider_subscription_id="cs_other",
            plan_code="monthly",
            status=SubscriptionStatus.ACTIVE,
            current_period_start=timezone.now(),
            current_period_end=other_end,
        )

        self.post_event(self.refund_event())

        self.user.refresh_from_db()
        self.assertEqual(self.user.role, UserRole.PAID)
        self.assertEqual(self.user.subscription_expires_at, other_end)
