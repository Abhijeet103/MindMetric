from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations, models

# Starting regional prices, derived from each plan's base USD price. Factors
# combine an approximate November 2026 exchange rate with the regional price
# level (Latin America and India about 50% lower, rest of Europe about 30%
# lower). They are a starting point: edit the rows in the admin afterwards.
NEW_REGION_PRICES = (
    # code, currency, factor against the USD base price
    ("CA", "CAD", Decimal("1.38")),
    ("LA", "USD", Decimal("0.50")),
    ("MX", "MXN", Decimal("18.5") * Decimal("0.50")),
    ("EE", "EUR", Decimal("0.92") * Decimal("0.70")),
    ("PL", "PLN", Decimal("3.70") * Decimal("0.70")),
    ("CZ", "CZK", Decimal("23.0") * Decimal("0.70")),
    ("HU", "HUF", Decimal("360") * Decimal("0.70")),
    ("SE", "SEK", Decimal("10.5")),
    ("NO", "NOK", Decimal("10.8")),
    ("DK", "DKK", Decimal("6.9")),
)
INDIA_FACTOR = Decimal("0.50")
WHOLE_UNIT_CURRENCIES = {"MXN", "PLN", "CZK", "SEK", "NOK", "DKK"}


def _round_half_up(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step


def nice_price(value: Decimal, currency: str) -> Decimal:
    """Round to a price that looks natural locally: 9.99, 49 zł, 4,990 Ft."""
    if currency == "HUF":
        return max(Decimal("990"), _round_half_up(value, Decimal("100")) - 10)
    if currency in WHOLE_UNIT_CURRENCIES:
        return max(Decimal("9"), _round_half_up(value, Decimal("10")) - 1)
    return max(Decimal("0.99"), _round_half_up(value, Decimal("1")) - Decimal("0.01"))


def _prices(plan, currency, factor):
    price = nice_price(plan.price * factor, currency)
    sale_price = None
    if plan.sale_price is not None:
        sale_price = min(price, nice_price(plan.sale_price * factor, currency))
    return price, sale_price


def seed_regional_tiers(apps, schema_editor):
    BillingPlan = apps.get_model("billing", "BillingPlan")
    BillingPlanCountryPrice = apps.get_model("billing", "BillingPlanCountryPrice")
    for plan in BillingPlan.objects.all():
        for code, currency, factor in NEW_REGION_PRICES:
            if BillingPlanCountryPrice.objects.filter(plan=plan, country_code=code).exists():
                continue  # Keep anything an administrator already set up.
            price, sale_price = _prices(plan, currency, factor)
            BillingPlanCountryPrice.objects.create(
                plan=plan, country_code=code, currency=currency,
                price=price, sale_price=sale_price, is_active=True,
            )
        # India checks out through PayPal, which can't take INR on this account,
        # so India gets its own USD price instead of the full US price.
        price, sale_price = _prices(plan, "USD", INDIA_FACTOR)
        india = BillingPlanCountryPrice.objects.filter(plan=plan, country_code="IN").first()
        if india is None:
            BillingPlanCountryPrice.objects.create(
                plan=plan, country_code="IN", currency="USD",
                price=price, sale_price=sale_price, is_active=True,
            )
        elif india.currency != "USD":
            india.currency = "USD"
            india.price = price
            india.sale_price = sale_price
            india.save(update_fields=("currency", "price", "sale_price", "updated_at"))


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0009_razorpay_currencies"),
    ]

    operations = [
        migrations.AlterField(
            model_name="billingplancountryprice",
            name="currency",
            field=models.CharField(choices=[("USD", "US dollar"), ("GBP", "British pound"), ("EUR", "Euro"), ("INR", "Indian rupee"), ("CHF", "Swiss franc"), ("CAD", "Canadian dollar"), ("MXN", "Mexican peso"), ("PLN", "Polish zloty"), ("CZK", "Czech koruna"), ("HUF", "Hungarian forint"), ("SEK", "Swedish krona"), ("NOK", "Norwegian krone"), ("DKK", "Danish krone")], max_length=3),
        ),
        migrations.AlterField(
            model_name="billingplancountryprice",
            name="country_code",
            field=models.CharField(help_text="Two-letter ISO country code, or a region code: EU (Western Europe), EE (rest of Europe), LA (Latin America), GB, IN. An exact country row takes precedence over its region's row.", max_length=2),
        ),
        migrations.RunPython(seed_regional_tiers, migrations.RunPython.noop),
    ]
