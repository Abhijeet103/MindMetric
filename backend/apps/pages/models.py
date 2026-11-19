import uuid

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
    email = models.EmailField(blank=True)
    discovery_key = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
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


class PortalFeedback(models.Model):
    class Category(models.TextChoices):
        GENERAL = "general", "General feedback"
        QUESTION = "question", "Question"
        ISSUE = "issue", "Report a problem"
        SUGGESTION = "suggestion", "Suggestion"

    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWED = "reviewed", "Reviewed"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.SET_NULL, related_name="portal_feedback", blank=True, null=True)
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, related_name="portal_feedback", blank=True, null=True)
    email = models.EmailField()
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.GENERAL)
    message = models.TextField()
    source_page = models.CharField(max_length=255, blank=True)
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="What the browser reported when the problem happened: error, page, test and browser.",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "portal feedback"
        verbose_name_plural = "portal feedback"

    def __str__(self) -> str:
        return f"{self.get_category_display()} from {self.email}"


class ApplicationDeadline(models.Model):
    """A company a student applied to, with the date its online assessment is due."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="application_deadlines")
    company = models.CharField(max_length=120)
    assessment_type = models.CharField(max_length=32, blank=True, help_text="Practice track key, if the student knows the test.")
    due_date = models.DateField()
    reminder_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "company"]
        indexes = [models.Index(fields=["user", "due_date"])]

    def __str__(self):
        return f"{self.company} · {self.due_date:%Y-%m-%d}"

    @property
    def days_left(self) -> int:
        return (self.due_date - timezone.localdate()).days


class EmployerAssessment(models.Model):
    """Which test types an employer is known to use in its screening round.

    Only published entries with a source are shown publicly, so every claim on
    the company lookup page can be traced back to where it came from.
    """

    company = models.CharField(max_length=160)
    industry = models.CharField(max_length=120, blank=True)
    assessment_types = models.JSONField(default=list, help_text="Practice track keys, e.g. [\"ccat\", \"shl_verify\"].")
    roles_note = models.CharField(max_length=200, blank=True, help_text="Which programmes this applies to, e.g. 'Summer analyst internships'.")
    source_url = models.URLField(max_length=1000, help_text="Where this mapping was confirmed.")
    source_label = models.CharField(max_length=160, help_text="Short description of the source, e.g. 'Employer careers FAQ'.")
    verified_on = models.DateField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["company"]

    def __str__(self):
        return self.company


class HiringResearch(models.Model):
    """Cached public-web research, scoped to a tenant; no applicant data is sent."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cache_key = models.CharField(max_length=64, unique=True)
    tenant = models.ForeignKey("tenants.Tenant", null=True, blank=True, on_delete=models.CASCADE)
    company = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    location = models.CharField(max_length=120, blank=True)
    prep_days = models.PositiveSmallIntegerField(default=7)
    status = models.CharField(max_length=16, default="pending")
    response_id = models.CharField(max_length=160, blank=True)
    report = models.JSONField(default=dict)
    error = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    checked_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()


class LegalPage(models.Model):
    """Privacy policy, terms and similar pages, written and published by an admin."""

    class Slug(models.TextChoices):
        PRIVACY = "privacy", "Privacy policy"
        TERMS = "terms", "Terms of service"
        REFUNDS = "refunds", "Refund policy"

    slug = models.CharField(max_length=32, choices=Slug.choices, unique=True)
    title = models.CharField(max_length=160)
    body = models.TextField(help_text="Plain text. Blank lines start new paragraphs; lines starting with '## ' become headings.")
    effective_date = models.DateField()
    is_published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class RecruiterAssessment(models.Model):
    """An owner's shareable hiring assessment, isolated from paid practice quotas."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="recruiter_assessments")
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recruiter_assessments")
    title = models.CharField(max_length=160)
    organization = models.CharField(max_length=160)
    role_title = models.CharField(max_length=160, blank=True)
    instructions = models.TextField(max_length=3000, blank=True)
    modules = models.JSONField(default=list)
    custom_questions = models.JSONField(default=list, blank=True)
    difficulty = models.CharField(max_length=16, default="medium")
    questions_per_module = models.PositiveIntegerField(default=8)
    duration_minutes = models.PositiveIntegerField(default=20)
    max_candidates = models.PositiveIntegerField(default=100)
    allowed_emails = models.JSONField(default=list, blank=True)
    is_open = models.BooleanField(default=True)
    closes_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def accepts_candidates(self):
        return self.is_open and self.closes_at > timezone.now()

    def __str__(self):
        return self.title


class RecruiterSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(RecruiterAssessment, on_delete=models.PROTECT, related_name="submissions")
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recruiter_submissions")
    # This private payload contains answer keys; only sanitised previews leave the server.
    questions = models.JSONField(default=list)
    answers = models.JSONField(default=dict)
    answer_revision = models.PositiveBigIntegerField(default=0)
    status = models.CharField(max_length=16, choices=[("active", "In progress"), ("submitted", "Submitted"), ("expired", "Time expired")], default="active")
    started_at = models.DateTimeField(default=timezone.now)
    deadline_at = models.DateTimeField()
    last_seen_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    consented_at = models.DateTimeField(default=timezone.now)
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    section_scores = models.JSONField(default=list)
    monitoring_events = models.JSONField(default=list)
    # The recruiter credit this candidate start used (null for starts before credits existed).
    credit_lot = models.ForeignKey("billing.RecruiterCreditLot", on_delete=models.PROTECT, null=True, blank=True, related_name="submissions")

    class Meta:
        ordering = ("-started_at",)
        constraints = [models.UniqueConstraint(fields=["assessment", "candidate"], name="one_recruiter_attempt_per_candidate")]

    @property
    def percentage(self):
        return round(100 * self.score / self.total_questions) if self.total_questions else 0


class RecruiterQuestionImport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="recruiter_question_imports")
    recruiter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="question_imports")
    filename = models.CharField(max_length=255)
    sheets = models.JSONField(default=list)
    mapping = models.JSONField(default=dict)
    questions = models.JSONField(default=list)
    errors = models.JSONField(default=list)
    assessment = models.OneToOneField(RecruiterAssessment, on_delete=models.SET_NULL, null=True, blank=True, related_name="source_import")
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
