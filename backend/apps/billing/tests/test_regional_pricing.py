from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from backend.apps.billing.models import BillingPlan, BillingPlanCountryPrice, format_money
from backend.apps.billing.regions import display_currency_for_country, pricing_region_for_country
from backend.apps.billing.services import PAYPAL_SUPPORTED_CURRENCIES, create_paypal_order, get_plan_definition

User = get_user_model()
PAYPAL_SETTINGS = {"PAYPAL_CLIENT_ID": "client", "PAYPAL_CLIENT_SECRET": "secret", "PAYPAL_WEBHOOK_ID": "webhook"}


class RegionMappingTests(TestCase):
    def test_countries_map_to_regions(self):
        cases = {
            "US": "US", "CA": "US", "AU": "US", "GB": "GB", "IN": "IN",
            "DE": "EU", "FR": "EU", "CH": "EU", "SE": "EU",
            "PL": "EE", "RO": "EE", "GR": "EE",
            "MX": "LA", "BR": "LA", "AR": "LA",
        }
        for country, region in cases.items():
            with self.subTest(country=country):
                self.assertEqual(pricing_region_for_country(country), region)

    def test_display_currency(self):
        self.assertEqual(display_currency_for_country("CA"), "CAD")
        self.assertEqual(display_currency_for_country("RO"), "EUR")
        self.assertEqual(display_currency_for_country("BR"), "USD")
        self.assertEqual(display_currency_for_country("IN"), "USD")


class SeededRegionalPriceTests(TestCase):
    """The migration seeds a starting price row for every new region."""

    def monthly(self, country):
        return get_plan_definition("monthly", country_code=country, currencies=PAYPAL_SUPPORTED_CURRENCIES)

    def test_india_and_latin_america_pay_about_half_in_usd(self):
        base = BillingPlan.objects.get(code="monthly").price
        for country in ("IN", "BR", "AR"):
            with self.subTest(country=country):
                plan = self.monthly(country)
                self.assertEqual(plan.currency, "USD")
                self.assertLess(Decimal(plan.price_value), base * Decimal("0.55"))

    def test_local_currencies(self):
        expected = {"CA": "CAD", "MX": "MXN", "PL": "PLN", "CZ": "CZK", "HU": "HUF", "SE": "SEK", "RO": "EUR", "DE": "EUR"}
        for country, currency in expected.items():
            with self.subTest(country=country):
                self.assertEqual(self.monthly(country).currency, currency)

    def test_rest_of_europe_is_cheaper_than_western_europe(self):
        self.assertLess(Decimal(self.monthly("RO").price_value), Decimal(self.monthly("DE").price_value))

    def test_forint_amounts_are_whole_numbers(self):
        self.assertNotIn(".", self.monthly("HU").price_value)

    def test_inr_row_is_skipped_for_paypal_but_used_otherwise(self):
        row = BillingPlanCountryPrice.objects.get(plan__code="monthly", country_code="IN")
        row.currency, row.price = "INR", Decimal("999.00")
        row.save()
        self.assertEqual(get_plan_definition("monthly", country_code="IN").currency, "INR")
        # PayPal can't take INR here, so India falls back to the base USD plan.
        self.assertEqual(self.monthly("IN").currency, "USD")


class MoneyFormattingTests(TestCase):
    def test_formats(self):
        self.assertEqual(format_money("PLN", Decimal("49.00")), "49 zł")
        self.assertEqual(format_money("HUF", Decimal("4990")), "4,990 Ft")
        self.assertEqual(format_money("CAD", Decimal("27.99")), "CA$27.99")
        self.assertEqual(format_money("MXN", Decimal("179.00")), "MX$179")

    def test_forint_prices_must_be_whole(self):
        row = BillingPlanCountryPrice(plan=BillingPlan.objects.get(code="monthly"), country_code="HU", currency="HUF", price=Decimal("4990.50"))
        with self.assertRaises(ValidationError):
            row.full_clean(validate_unique=False)


@override_settings(**PAYPAL_SETTINGS)
class PayPalRegionalCheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="buyer@example.com", password="secret")

    def order_amount(self, country):
        sent = {}

        def fake_request(method, path, payload=None):
            sent.update(payload or {})
            return {"id": "ORDER1", "links": [{"rel": "approve", "href": "https://paypal.test/approve"}]}

        with patch("backend.apps.billing.services._paypal_request", side_effect=fake_request):
            create_paypal_order(self.user, "monthly", base_url="https://mindmetric.store", country_code=country)
        return sent["purchase_units"][0]["amount"]

    def test_india_is_charged_its_discounted_usd_price(self):
        amount = self.order_amount("IN")
        india = BillingPlanCountryPrice.objects.get(plan__code="monthly", country_code="IN")
        self.assertEqual(amount, {"currency_code": "USD", "value": f"{india.effective_price:.2f}"})

    def test_hungary_is_charged_whole_forints(self):
        amount = self.order_amount("HU")
        self.assertEqual(amount["currency_code"], "HUF")
        self.assertNotIn(".", amount["value"])
