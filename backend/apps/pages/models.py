from django.db import models
from django.conf import settings
from django.utils import timezone


class AudienceContact(models.Model):
    class Source(models.TextChoices):
        USER_ACCOUNT = "user_account", "User account"
        SALES_INQUIRY = "sales_inquiry", "Sales inquiry"
        TEST_SUGGESTION = "test_suggestion", "Test suggestion"
        ASSESSMENT_WAITLIST = "assessment_waitlist", "Assessment waitlist"
        INSTITUTION_INVITE = "institution_invite", "Institution invite"
        ADMIN = "admin", "Added by admin"

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.SET_NULL,
        related_name="audience_contacts",
        blank=True,
        null=True,
    )
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="audience_contact",
        blank=True,
        null=True,
    )
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.ADMIN)
    marketing_opt_in = models.BooleanField(default=True)
    unsubscribed_at = models.DateTimeField(blank=True, null=True)
    last_campaign_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        if self.marketing_opt_in:
            self.unsubscribed_at = None
        super().save(*args, **kwargs)

    def unsubscribe(self) -> None:
        self.marketing_opt_in = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=("marketing_opt_in", "unsubscribed_at", "updated_at"))

    def __str__(self) -> str:
        return self.email


class SaleInquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        CLOSED = "closed", "Closed"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="sale_inquiries", blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=64, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    team_size = models.CharField(max_length=64, blank=True)
    message = models.TextField()
    source_page = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True)
    marketing_opt_in = models.BooleanField(
        default=False,
        help_text="The contact has agreed to receive MindMetric product updates and offers.",
    )
    contacted_back = models.BooleanField(
        default=False,
        help_text="Whether we have responded to this enquiry. Set automatically after an admin email reply, or manually for other channels.",
    )
    contacted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        label = self.full_name or self.email
        return f"{label} ({self.email})"


class AdminEmail(models.Model):
    recipient = models.EmailField()
    subject = models.CharField(max_length=180)
    body = models.TextField()
    inquiry = models.ForeignKey(SaleInquiry, on_delete=models.SET_NULL, null=True, blank=True, related_name="replies")
    sent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-sent_at",)
        verbose_name = "sent email"
        verbose_name_plural = "sent emails"

    def __str__(self):
        return f"{self.subject} — {self.recipient}"


class TestSuggestion(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWED = "reviewed", "Reviewed"
        PLANNED = "planned", "Planned"
        CLOSED = "closed", "Closed"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="test_suggestions", blank=True, null=True)
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, related_name="test_suggestions", blank=True, null=True)
    email = models.EmailField()
    requested_test = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    source_page = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.requested_test} ({self.email})"
