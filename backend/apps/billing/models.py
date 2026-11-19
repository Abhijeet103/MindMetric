from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class BillingPlanCode(models.TextChoices):
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"


class BillingCurrency(models.TextChoices):
    USD = "USD", "US dollar"
    GBP = "GBP", "British pound"
    EUR = "EUR", "Euro"
    INR = "INR", "Indian rupee"
    CHF = "CHF", "Swiss franc"
    CAD = "CAD", "Canadian dollar"
    MXN = "MXN", "Mexican peso"
    PLN = "PLN", "Polish zloty"
    CZK = "CZK", "Czech koruna"
    HUF = "HUF", "Hungarian forint"
    SEK = "SEK", "Swedish krona"
    NOK = "NOK", "Norwegian krone"
    DKK = "DKK", "Danish krone"


# PayPal rejects decimal amounts in these currencies.
ZERO_DECIMAL_CURRENCIES = frozenset({"HUF"})
_PREFIX_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "INR": "₹", "CHF": "CHF ", "CAD": "CA$", "MXN": "MX$"}
_SUFFIX_SYMBOLS = {"PLN": " zł", "CZK": " Kč", "HUF": " Ft", "SEK": " kr", "NOK": " kr", "DKK": " kr"}


def format_money(currency: str, amount: Decimal) -> str:
    currency = currency.upper()
    if currency in _SUFFIX_SYMBOLS:
        # Local convention for these currencies: whole amounts without decimals,
        # thousands grouped ("3,990 Ft", "69 zł").
        if currency in ZERO_DECIMAL_CURRENCIES or amount == amount.to_integral_value():
            return f"{amount:,.0f}{_SUFFIX_SYMBOLS[currency]}"
        return f"{amount:,.2f}{_SUFFIX_SYMBOLS[currency]}"
    symbol = _PREFIX_SYMBOLS.get(currency)
    if currency == "MXN" and amount == amount.to_integral_value():
        return f"{symbol}{amount:,.0f}"  # Peso prices are usually whole: MX$179.
    return f"{symbol}{amount:.2f}" if symbol else f"{currency} {amount:.2f}"


def payment_amount_value(currency: str, amount: Decimal) -> str:
    """Amount string for payment APIs: whole units for zero-decimal currencies."""
    if currency.upper() in ZERO_DECIMAL_CURRENCIES:
        return f"{amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)}"
    return f"{amount:.2f}"


class BillingPlan(models.Model):
    code = models.CharField(max_length=16, choices=BillingPlanCode.choices, unique=True)
    title = models.CharField(max_length=80)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        blank=True,
        null=True,
        help_text="Optional amount charged at checkout. Leave blank to charge the regular price.",
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="Three-letter ISO currency code, for example USD.",
    )
    duration_label = models.CharField(max_length=120)
    summary = models.TextField()
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("display_order", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(sale_price__isnull=True) | Q(sale_price__lte=F("price")),
                name="billing_plan_sale_lte_price",
            ),
        ]

    def clean(self):
        super().clean()
        if self.sale_price is not None and self.sale_price > self.price:
            raise ValidationError(
                {"sale_price": "Sale price cannot be greater than the regular price."}
            )

    def save(self, *args, **kwargs):
        self.currency = self.currency.strip().upper()
        super().save(*args, **kwargs)

    @property
    def price_display(self) -> str:
        return format_money(self.currency, self.price)

    @property
    def effective_price(self) -> Decimal:
        return self.sale_price if self.sale_price is not None else self.price

    @property
    def effective_price_display(self) -> str:
        return format_money(self.currency, self.effective_price)

    @property
    def has_discount(self) -> bool:
        return self.sale_price is not None and self.sale_price < self.price

    @property
    def discount_percent(self) -> int:
        if not self.has_discount:
            return 0
        discount = ((self.price - self.sale_price) / self.price) * Decimal("100")
        return int(discount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def __str__(self) -> str:
        return f"{self.title} ({self.effective_price_display})"


class BillingPlanCountryPrice(models.Model):
    plan = models.ForeignKey(
        BillingPlan,
        on_delete=models.CASCADE,
        related_name="country_prices",
    )
    country_code = models.CharField(
        max_length=2,
        help_text=(
            "Two-letter ISO country code, or a region code: EU (Western Europe), "
            "EE (rest of Europe), LA (Latin America), GB, IN. An exact country "
            "row takes precedence over its region's row."
        ),
    )
    currency = models.CharField(max_length=3, choices=BillingCurrency.choices)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        blank=True,
        null=True,
        help_text="Optional regional sale price charged at checkout.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("plan__display_order", "country_code")
        constraints = [
            models.UniqueConstraint(
                fields=("plan", "country_code"),
                name="billing_plan_country_price_unique",
            ),
            models.CheckConstraint(
                condition=Q(sale_price__isnull=True) | Q(sale_price__lte=F("price")),
                name="billing_country_sale_lte_price",
            ),
        ]

    def clean(self):
        super().clean()
        self.country_code = self.country_code.strip().upper()
        self.currency = self.currency.strip().upper()
        if len(self.country_code) != 2 or not self.country_code.isalpha():
            raise ValidationError(
                {"country_code": "Enter a two-letter country code, or a region code such as EU."}
            )
        if self.currency in ZERO_DECIMAL_CURRENCIES:
            for field in ("price", "sale_price"):
                value = getattr(self, field)
                if value is not None and value != value.to_integral_value():
                    raise ValidationError({field: f"{self.currency} prices must be whole amounts."})
        if self.sale_price is not None and self.sale_price > self.price:
            raise ValidationError(
                {"sale_price": "Sale price cannot be greater than the regular price."}
            )

    def save(self, *args, **kwargs):
        self.country_code = self.country_code.strip().upper()
        self.currency = self.currency.strip().upper()
        super().save(*args, **kwargs)

    @property
    def effective_price(self) -> Decimal:
        return self.sale_price if self.sale_price is not None else self.price

    @property
    def price_display(self) -> str:
        return format_money(self.currency, self.price)

    @property
    def effective_price_display(self) -> str:
        return format_money(self.currency, self.effective_price)

    @property
    def has_discount(self) -> bool:
        return self.sale_price is not None and self.sale_price < self.price

    @property
    def discount_percent(self) -> int:
        if not self.has_discount:
            return 0
        discount = ((self.price - self.sale_price) / self.price) * Decimal("100")
        return int(discount.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @property
    def title(self) -> str:
        return f"{self.plan.title} - {self.country_code}"

    def __str__(self) -> str:
        return f"{self.title} ({self.effective_price_display})"


class SubscriptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    CANCELED = "canceled", "Canceled"
    EXPIRED = "expired", "Expired"


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="subscriptions", blank=True, null=True)
    tenant_user = models.ForeignKey(
        "tenants.TenantUser",
        on_delete=models.PROTECT,
        related_name="subscriptions",
        blank=True,
        null=True,
    )
    provider = models.CharField(max_length=32, default="stripe")
    plan_code = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=SubscriptionStatus.choices, default=SubscriptionStatus.PENDING)
    provider_customer_id = models.CharField(max_length=255, blank=True)
    provider_subscription_id = models.CharField(max_length=255, blank=True)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status", "updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.plan_code} - {self.status}"


# ------------------------------------------------------------ recruiter credits
# Recruiters pay per candidate. Each purchase or grant is a "lot" of credits
# with its own expiry; a candidate starting an assessment consumes one credit
# from the lot that expires soonest.

RECRUITER_WELCOME_CREDITS = 100
RECRUITER_CREDIT_VALIDITY_DAYS = 365


class RecruiterPriceTier(models.Model):
    """Volume pricing: the whole purchase is charged at the tier its size falls in."""

    name = models.CharField(max_length=60)
    min_candidates = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    max_candidates = models.PositiveIntegerField(blank=True, null=True, help_text="Leave blank for no upper limit.")
    price_per_candidate = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))], help_text="USD, before regional discounts.")
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("min_candidates",)

    def __str__(self) -> str:
        upper = f"–{self.max_candidates}" if self.max_candidates else "+"
        return f"{self.name} ({self.min_candidates}{upper}): ${self.price_per_candidate}/candidate"

    def clean(self):
        if self.max_candidates is not None and self.max_candidates < self.min_candidates:
            raise ValidationError("The maximum must be at least the minimum.")


class RecruiterCreditPurchaseStatus(models.TextChoices):
    PENDING = "pending", "Pending payment"
    PAID = "paid", "Paid"
    REFUNDED = "refunded", "Refunded"
    EXPIRED = "expired", "Abandoned"


class RecruiterCreditPurchase(models.Model):
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recruiter_credit_purchases")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="recruiter_credit_purchases", blank=True, null=True)
    candidates = models.PositiveIntegerField()
    tier_name = models.CharField(max_length=60)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    pricing_region = models.CharField(max_length=8, default="US")
    provider = models.CharField(max_length=32, default="paypal")
    provider_order_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=16, choices=RecruiterCreditPurchaseStatus.choices, default=RecruiterCreditPurchaseStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.recruiter.email} – {self.candidates} credits – {self.status}"


class RecruiterCreditSource(models.TextChoices):
    WELCOME = "welcome", "Free welcome credits"
    PURCHASE = "purchase", "Purchase"
    GRANT = "grant", "Granted by MindMetric"


class RecruiterCreditLot(models.Model):
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recruiter_credit_lots")
    source = models.CharField(max_length=16, choices=RecruiterCreditSource.choices)
    quantity = models.PositiveIntegerField()
    remaining = models.PositiveIntegerField(default=0, help_text="Credits left. Leave at 0 on a new grant to give the full quantity.")
    expires_at = models.DateTimeField()
    purchase = models.OneToOneField(RecruiterCreditPurchase, on_delete=models.PROTECT, related_name="lot", blank=True, null=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("expires_at",)
        indexes = [models.Index(fields=["recruiter", "expires_at"])]
        constraints = [
            models.CheckConstraint(condition=Q(remaining__lte=F("quantity")), name="recruiter_lot_remaining_lte_quantity"),
            models.UniqueConstraint(fields=["recruiter"], condition=Q(source="welcome"), name="one_welcome_lot_per_recruiter"),
        ]

    def __str__(self) -> str:
        return f"{self.recruiter.email} – {self.remaining}/{self.quantity} ({self.get_source_display()})"
