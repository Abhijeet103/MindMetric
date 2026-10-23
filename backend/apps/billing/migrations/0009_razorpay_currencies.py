from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


def seed_razorpay_currency_prices(apps, schema_editor):
    BillingPlan = apps.get_model("billing", "BillingPlan")
    BillingPlanCountryPrice = apps.get_model("billing", "BillingPlanCountryPrice")
    for plan in BillingPlan.objects.all():
        inr_price = (plan.price * Decimal("83.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        inr_sale_price = (
            (plan.sale_price * Decimal("83.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if plan.sale_price is not None
            else None
        )
        BillingPlanCountryPrice.objects.update_or_create(
            plan=plan,
            country_code="IN",
            defaults={
                "currency": "INR",
                "price": inr_price,
                "sale_price": inr_sale_price,
                "is_active": True,
            },
        )
        swiss_price = (plan.price * Decimal("0.90")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        swiss_sale_price = (
            (plan.sale_price * Decimal("0.90")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if plan.sale_price is not None
            else None
        )
        BillingPlanCountryPrice.objects.update_or_create(
            plan=plan,
            country_code="CH",
            defaults={
                "currency": "CHF",
                "price": swiss_price,
                "sale_price": swiss_sale_price,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("billing", "0008_india_usd_regional_prices")]

    operations = [
        migrations.RemoveConstraint(
            model_name="billingplancountryprice",
            name="billing_india_price_uses_usd",
        ),
        migrations.AlterField(
            model_name="billingplancountryprice",
            name="currency",
            field=models.CharField(
                choices=[
                    ("USD", "US dollar"),
                    ("GBP", "British pound"),
                    ("EUR", "Euro"),
                    ("INR", "Indian rupee"),
                    ("CHF", "Swiss franc"),
                ],
                max_length=3,
            ),
        ),
        migrations.RunPython(seed_razorpay_currency_prices, migrations.RunPython.noop),
    ]
