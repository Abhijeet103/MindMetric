import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from backend.apps.accounts.forms import CustomSignupForm
from backend.apps.assessments.config import ASSESSMENT_CONFIG
from backend.apps.billing import recruiter_credits as rc
from backend.apps.billing.models import RecruiterCreditLot, RecruiterCreditPurchase
from backend.apps.billing.views import _handle_recruiter_credit_event
from backend.apps.pages.models import RecruiterAssessment, RecruiterSubmission
from backend.apps.tenants.models import Tenant

User = get_user_model()


def paypal_order(purchase, status="COMPLETED", value=None, capture_status="COMPLETED"):
    amount = {"currency_code": "USD", "value": value or f"{purchase.amount:.2f}"}
    return {"id": purchase.provider_order_id, "status": status, "purchase_units": [{
        "amount": {"currency_code": "USD", "value": f"{purchase.amount:.2f}"},
        "custom_id": json.dumps({"kind": "recruiter_credits", "purchase_id": purchase.pk}),
        "payments": {"captures": [{"status": capture_status, "amount": amount}]},
    }]}


class RecruiterCreditTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Credit tests", slug="credit-tests", primary_domain="credits.example.com", tenant_type="platform", allowed_assessments=list(ASSESSMENT_CONFIG))
        self.host = {"HTTP_HOST": self.tenant.primary_domain}
        self.owner = User.objects.create_user(email="hr@example.com", password="pw", account_type="recruiter", organization="Acme", tenant=self.tenant)
        self.student = User.objects.create_user(email="cand@example.com", password="pw", tenant=self.tenant)
        self.client.force_login(self.owner)
        self.data = {"title": "Screen", "organization": "Acme", "modules": ["sjt_workplace"], "difficulty": "medium", "questions_per_module": 4,
                     "duration_minutes": 10, "open_days": 7, "max_candidates": 10, "allowed_emails": "", "instructions": ""}

    # ------------------------------------------------------------ pricing
    def test_volume_tiers_and_boundaries(self):
        expected = {10: ("Starter", "40.00"), 50: ("Starter", "200.00"), 51: ("Growth", "153.00"), 300: ("Growth", "900.00"),
                    301: ("Scale", "602.00"), 1000: ("Scale", "2000.00"), 1001: ("Enterprise", "1501.50"), 5000: ("Enterprise", "7500.00")}
        for candidates, (tier, total) in expected.items():
            with self.subTest(candidates=candidates):
                priced = rc.quote(candidates, "US")
                self.assertEqual((priced.tier.name, priced.total), (tier, Decimal(total)))
        for bad in (0, 9, 5001, True):
            with self.subTest(bad=bad), self.assertRaises(rc.RecruiterCreditError):
                rc.quote(bad, "US")

    def test_regional_discounts_match_student_passes(self):
        self.assertEqual(rc.quote(50, "IN").tier.unit_price, Decimal("2.00"))
        self.assertEqual(rc.quote(50, "MX").tier.unit_price, Decimal("2.00"))
        self.assertEqual(rc.quote(50, "PL").tier.unit_price, Decimal("2.80"))
        self.assertEqual(rc.quote(50, "GB").tier.unit_price, Decimal("4.00"))

    # ------------------------------------------------------------ grants
    def test_welcome_credits_are_granted_once_and_only_to_recruiters(self):
        self.assertTrue(rc.grant_welcome_credits(self.owner))
        self.assertFalse(rc.grant_welcome_credits(self.owner))
        self.assertEqual(rc.credit_balance(self.owner), 100)
        self.assertFalse(rc.grant_welcome_credits(self.student))
        self.assertEqual(rc.credit_balance(self.student), 0)

    def test_recruiter_signup_grants_welcome_credits(self):
        user = User.objects.create_user(email="new-hr@example.com", password="pw")
        form = CustomSignupForm({"first_name": "New", "account_type": "recruiter"})
        self.assertTrue(form.is_valid())
        request = RequestFactory().post("/accounts/signup/")
        request.tenant = self.tenant
        form.signup(request, user)
        self.assertEqual(rc.credit_balance(user), 100)

    def test_dashboard_grants_missing_welcome_credits_and_advertises_them(self):
        page = self.client.get(reverse("pages:recruiter-dashboard"), **self.host)
        self.assertContains(page, "100 free credits")
        self.assertEqual(page.context["credit_balance"], 100)

    # ------------------------------------------------------------ usage
    def start(self, assessment, user):
        self.client.force_login(user)
        return self.client.post(reverse("pages:recruiter-candidate-start", args=[assessment.share_token]), '{"consent":true}', content_type="application/json", **self.host)

    def make_assessment(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(reverse("pages:recruiter-create"), self.data, **self.host).status_code, 302)
        return RecruiterAssessment.objects.latest("created_at")

    def test_each_new_candidate_uses_one_credit_and_resume_is_free(self):
        rc.grant_welcome_credits(self.owner)
        assessment = self.make_assessment()
        self.assertEqual(self.start(assessment, self.student).status_code, 201)
        self.assertEqual(rc.credit_balance(self.owner), 99)
        self.assertEqual(self.start(assessment, self.student).status_code, 200)
        self.assertEqual(rc.credit_balance(self.owner), 99)
        self.assertIsNotNone(RecruiterSubmission.objects.get().credit_lot_id)

    def test_out_of_credits_blocks_new_starts_but_not_resumes(self):
        rc.grant_welcome_credits(self.owner)
        assessment = self.make_assessment()
        self.assertEqual(self.start(assessment, self.student).status_code, 201)
        RecruiterCreditLot.objects.update(remaining=0)
        self.assertEqual(self.start(assessment, self.student).status_code, 200)
        newcomer = User.objects.create_user(email="late@example.com", password="pw", tenant=self.tenant)
        response = self.start(assessment, newcomer)
        self.assertEqual(response.status_code, 400)
        self.assertIn("temporarily unavailable", response.json()["detail"])
        self.assertEqual(RecruiterSubmission.objects.count(), 1)
        self.client.force_login(self.owner)
        self.assertRedirects(self.client.get(reverse("pages:recruiter-create"), **self.host), reverse("pages:recruiter-credits"), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("pages:recruiter-assessment", args=[assessment.pk]), **self.host), "no candidate credits left")

    def test_soonest_expiring_lot_is_used_and_expired_lots_are_ignored(self):
        now = timezone.now()
        RecruiterCreditLot.objects.create(recruiter=self.owner, source="grant", quantity=5, remaining=5, expires_at=now - timedelta(days=1))
        later = RecruiterCreditLot.objects.create(recruiter=self.owner, source="grant", quantity=5, remaining=5, expires_at=now + timedelta(days=200))
        sooner = RecruiterCreditLot.objects.create(recruiter=self.owner, source="grant", quantity=5, remaining=5, expires_at=now + timedelta(days=20))
        self.assertEqual(rc.credit_balance(self.owner), 10)
        self.assertEqual(rc.consume_credit(self.owner).pk, sooner.pk)
        later.refresh_from_db()
        self.assertEqual(later.remaining, 5)

    def test_new_recruiter_without_credits_cannot_create(self):
        self.assertEqual(rc.credit_balance(self.owner), 0)
        self.assertEqual(self.client.post(reverse("pages:recruiter-create"), self.data, **self.host).status_code, 302)
        self.assertFalse(RecruiterAssessment.objects.exists())

    # ------------------------------------------------------------ PayPal
    @patch.object(rc, "paypal_is_configured", return_value=True)
    @patch.object(rc, "_paypal_request")
    def test_checkout_creates_pending_purchase_at_tier_price(self, paypal_request, _configured):
        paypal_request.return_value = {"id": "ORDER-1", "links": [{"rel": "payer-action", "href": "https://paypal.test/approve"}]}
        response = self.client.post(reverse("pages:recruiter-credits"), {"candidates": "120"}, **self.host)
        self.assertRedirects(response, "https://paypal.test/approve", fetch_redirect_response=False)
        purchase = RecruiterCreditPurchase.objects.get()
        self.assertEqual((purchase.candidates, purchase.tier_name, purchase.amount, purchase.status), (120, "Growth", Decimal("360.00"), "pending"))
        body = paypal_request.call_args.args[2]
        self.assertEqual(body["purchase_units"][0]["amount"], {"currency_code": "USD", "value": "360.00"})
        self.assertEqual(json.loads(body["purchase_units"][0]["custom_id"])["purchase_id"], purchase.pk)

    def test_checkout_rejects_too_few_candidates(self):
        response = self.client.post(reverse("pages:recruiter-credits"), {"candidates": "3"}, **self.host)
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "minimum purchase", status_code=400)

    def make_purchase(self, candidates=60, order_id="ORDER-2"):
        priced = rc.quote(candidates, "US")
        return RecruiterCreditPurchase.objects.create(recruiter=self.owner, candidates=candidates, tier_name=priced.tier.name, unit_price=priced.tier.unit_price,
                                                      amount=priced.total, provider_order_id=order_id)

    def test_return_adds_credits_once(self):
        purchase = self.make_purchase()
        with patch.object(rc, "get_paypal_order", return_value=paypal_order(purchase)):
            for _ in range(2):
                response = self.client.get(reverse("billing-recruiter-paypal-return"), {"token": purchase.provider_order_id}, **self.host)
                self.assertRedirects(response, reverse("pages:recruiter-credits"), fetch_redirect_response=False)
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "paid")
        self.assertEqual(rc.credit_balance(self.owner), 60)
        self.assertEqual(RecruiterCreditLot.objects.filter(purchase=purchase).count(), 1)

    def test_amount_mismatch_and_foreign_orders_add_nothing(self):
        purchase = self.make_purchase()
        with patch.object(rc, "get_paypal_order", return_value=paypal_order(purchase, value="1.00")):
            self.client.get(reverse("billing-recruiter-paypal-return"), {"token": purchase.provider_order_id}, **self.host)
        self.assertEqual(rc.credit_balance(self.owner), 0)
        other = User.objects.create_user(email="other-hr@example.com", password="pw", account_type="recruiter", tenant=self.tenant)
        self.client.force_login(other)
        with patch.object(rc, "get_paypal_order", return_value=paypal_order(purchase)) as fetch:
            self.client.get(reverse("billing-recruiter-paypal-return"), {"token": purchase.provider_order_id}, **self.host)
            fetch.assert_not_called()
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "pending")

    def test_webhook_fulfils_and_full_refund_removes_unused_credits(self):
        purchase = self.make_purchase()
        with patch("backend.apps.billing.views.paypal_order_id_from_event", return_value=purchase.provider_order_id), \
                patch.object(rc, "get_paypal_order", return_value=paypal_order(purchase)):
            self.assertTrue(_handle_recruiter_credit_event("PAYMENT.CAPTURE.COMPLETED", {}))
        self.assertEqual(rc.credit_balance(self.owner), 60)
        with patch("backend.apps.billing.views.paypal_order_id_from_event", return_value=purchase.provider_order_id), \
                patch("backend.apps.billing.views.paypal_capture_is_fully_reversed", return_value=True):
            self.assertTrue(_handle_recruiter_credit_event("PAYMENT.CAPTURE.REFUNDED", {}))
        self.assertEqual(rc.credit_balance(self.owner), 0)
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "refunded")
        with patch("backend.apps.billing.views.paypal_order_id_from_event", return_value="STUDENT-PASS-ORDER"):
            self.assertFalse(_handle_recruiter_credit_event("PAYMENT.CAPTURE.COMPLETED", {}))

    # ------------------------------------------------------------ builder UI
    def test_builder_groups_sections_under_their_test(self):
        rc.grant_welcome_credits(self.owner)
        page = self.client.get(reverse("pages:recruiter-create"), **self.host)
        self.assertContains(page, 'data-test-toggle="prepgia"', html=False)
        self.assertContains(page, 'data-test-sections="prepgia"', html=False)
        self.assertContains(page, "Choose sections")
        groups = {group["key"]: [m["key"] for m in group["modules"]] for group in page.context["test_groups"]}
        self.assertIn("reasoning", groups["prepgia"])
        # Every section appears exactly once, under its own test.
        all_keys = [key for keys in groups.values() for key in keys]
        self.assertEqual(len(all_keys), len(set(all_keys)))
        invalid = self.client.post(reverse("pages:recruiter-create"), {**self.data, "modules": ["reasoning"], "questions_per_module": 4, "title": ""}, **self.host)
        self.assertEqual(invalid.status_code, 400)
        self.assertTrue(next(g for g in invalid.context["test_groups"] if g["key"] == "prepgia")["selected"])

    def test_credits_page_shows_tiers_and_balance(self):
        rc.grant_welcome_credits(self.owner)
        page = self.client.get(reverse("pages:recruiter-credits"), **self.host)
        for text in ("Starter", "Growth", "Scale", "Enterprise", "$4.00", "$1.50", "Free welcome credits"):
            self.assertContains(page, text)
        self.assertContains(page, 'id="credit-tiers"', html=False)
