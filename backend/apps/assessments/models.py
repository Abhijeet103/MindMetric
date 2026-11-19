from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AttemptMode(models.TextChoices):
    FULL_TEST = "full_test", "Full Test"
    SECTION = "section", "Section"


class AttemptStatus(models.TextChoices):
    CREATED = "created", "Created"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    EXPIRED = "expired", "Expired"


class SectionType(models.TextChoices):
    REASONING = "reasoning", "Reasoning"
    PERCEPTUAL_SPEED = "perceptual_speed", "Perceptual Speed"
    NUMBER_SPEED_ACCURACY = "number_speed_accuracy", "Number Speed & Accuracy"
    WORD_MEANING = "word_meaning", "Word Meaning"
    SPATIAL_VISUALIZATION = "spatial_visualization", "Spatial Visualization"
    CCAT_NUMERICAL = "ccat_numerical", "CCAT Math & Numerical Reasoning"
    CCAT_VERBAL = "ccat_verbal", "CCAT Verbal Reasoning"
    CCAT_SPATIAL = "ccat_spatial", "CCAT Spatial & Abstract Reasoning"
    SHL_NUMERICAL = "shl_numerical", "SHL-style Numerical Reasoning"
    SHL_DEDUCTIVE = "shl_deductive", "SHL-style Deductive Reasoning"
    SHL_INDUCTIVE = "shl_inductive", "SHL-style Inductive Reasoning"
    CONSULTING_MATH = "consulting_math", "Consulting Business Mathematics"
    CONSULTING_EVIDENCE = "consulting_evidence", "Consulting Evidence Evaluation"
    CONSULTING_CASE = "consulting_case", "Consulting Short Cases"
    WG_INFERENCE = "wg_inference", "Watson–Glaser-style Inference"
    WG_ASSUMPTIONS = "wg_assumptions", "Watson–Glaser-style Assumptions"
    WG_DEDUCTION = "wg_deduction", "Watson–Glaser-style Deduction"
    WG_INTERPRETATION = "wg_interpretation", "Watson–Glaser-style Interpretation"
    WG_ARGUMENTS = "wg_arguments", "Watson–Glaser-style Arguments"
    LINKED_CASE = "linked_case", "Linked Consulting Cases"
    SJT_WORKPLACE = "sjt_workplace", "Workplace Judgement"
    WORK_SIMULATION = "work_simulation", "Inbox and Business Simulation"
    VERBAL_PASSAGES = "verbal_passages", "Passage-based Verbal Reasoning"
    APTITUDE_ARITHMETIC = "aptitude_arithmetic", "Arithmetic Reasoning"
    APTITUDE_VERBAL = "aptitude_verbal", "Verbal and Logical Reasoning"
    APTITUDE_VISUAL = "aptitude_visual", "Visual Reasoning"


class PracticeTrackVisibility(models.TextChoices):
    ACCESSIBLE = "accessible", "Accessible"
    UPCOMING = "upcoming", "Upcoming"
    HIDDEN = "hidden", "Hidden"


class AssessmentTrack(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="assessment_tracks", blank=True, null=True)
    assessment_type = models.CharField(max_length=64)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    module_count = models.PositiveIntegerField(default=0)
    trust_line = models.CharField(max_length=255, blank=True)
    available_languages = models.JSONField(default=list, blank=True)
    visibility_state = models.CharField(
        max_length=24,
        choices=PracticeTrackVisibility.choices,
        default=PracticeTrackVisibility.ACCESSIBLE,
    )
    is_active = models.BooleanField(default=True)
    last_released_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "assessment_type")
        indexes = [
            models.Index(fields=["tenant", "visibility_state", "assessment_type"]),
        ]
        ordering = ("title",)

    def __str__(self) -> str:
        return f"{self.title} ({self.assessment_type})"


class AssessmentTrackWaitlistEntry(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="assessment_track_waitlist_entries", blank=True, null=True)
    assessment_type = models.CharField(max_length=64)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="assessment_track_waitlist_entries", blank=True, null=True)
    email = models.EmailField()
    source_page = models.CharField(max_length=64, blank=True)
    notified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "assessment_type", "email")
        indexes = [
            models.Index(fields=["tenant", "assessment_type", "notified_at"]),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.email} waiting for {self.assessment_type}"


class FreeTierModuleLimit(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.PROTECT,
        related_name="free_tier_module_limits",
    )
    assessment_type = models.CharField(max_length=64)
    section_type = models.CharField(max_length=32, choices=SectionType.choices)
    practice_question_limit = models.PositiveIntegerField(default=10)
    test_attempt_limit = models.PositiveIntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "assessment_type", "section_type"),
                name="unique_free_tier_module_limit",
            ),
        ]
        ordering = ("tenant", "assessment_type", "section_type")

    def clean(self):
        from .config import get_module_assessment_type
        try:
            expected_assessment = get_module_assessment_type(self.section_type)
        except KeyError:
            expected_assessment = None
        if expected_assessment and self.assessment_type != expected_assessment:
            raise ValidationError(
                {"assessment_type": f"{self.get_section_type_display()} belongs to {expected_assessment}."}
            )

    def __str__(self) -> str:
        return f"{self.tenant}: {self.get_section_type_display()} free-tier limits"


class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="attempts", blank=True, null=True)
    tenant_user = models.ForeignKey(
        "tenants.TenantUser",
        on_delete=models.PROTECT,
        related_name="attempts",
        blank=True,
        null=True,
    )
    assessment_type = models.CharField(max_length=24, default="prepgia")
    mode = models.CharField(max_length=24, choices=AttemptMode.choices)
    status = models.CharField(max_length=24, choices=AttemptStatus.choices, default=AttemptStatus.CREATED)
    configuration = models.JSONField(default=dict, blank=True)
    overall_adjusted_score = models.FloatField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "mode", "assessment_type"]),
            models.Index(fields=["user", "status", "started_at"]),
        ]


class AttemptSection(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="sections")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="attempt_sections", blank=True, null=True)
    section_type = models.CharField(max_length=32, choices=SectionType.choices)
    order_index = models.PositiveIntegerField(default=0)
    difficulty = models.CharField(max_length=16, default="easy")
    time_limit_seconds = models.PositiveIntegerField()
    question_count = models.PositiveIntegerField(default=10)
    adjusted_score = models.FloatField(default=0)
    correct_answers_count = models.PositiveIntegerField(default=0)
    incorrect_answers_count = models.PositiveIntegerField(default=0)
    question_payload = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=["attempt", "order_index"]),
        ]


class AttemptAnswer(models.Model):
    attempt_section = models.ForeignKey(AttemptSection, on_delete=models.CASCADE, related_name="answers")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="attempt_answers", blank=True, null=True)
    question_index = models.PositiveIntegerField()
    user_answer = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(blank=True, null=True)
    penalty_applied = models.FloatField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)


class SectionProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="section_progress")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="section_progress_rows", blank=True, null=True)
    tenant_user = models.ForeignKey(
        "tenants.TenantUser",
        on_delete=models.PROTECT,
        related_name="section_progress_rows",
        blank=True,
        null=True,
    )
    assessment_type = models.CharField(max_length=24, default="prepgia")
    section_type = models.CharField(max_length=32, choices=SectionType.choices)
    practice_questions_solved = models.PositiveIntegerField(default=0)
    tests_taken = models.PositiveIntegerField(default=0)
    last_test_score = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "user", "assessment_type", "section_type")


class WordMeaningItem(models.Model):
    pair_word_1 = models.CharField(max_length=128)
    pair_word_2 = models.CharField(max_length=128)
    relationship_type = models.CharField(max_length=64)
    explanation = models.TextField(blank=True)
    odd_word = models.CharField(max_length=128)
    difficulty = models.CharField(max_length=16, default="easy")
    language = models.CharField(
        max_length=8,
        default="en",
        db_index=True,
        help_text="Language of the words: en, de or es.",
    )
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["difficulty", "id"]

    def __str__(self) -> str:
        return f"{self.pair_word_1} / {self.pair_word_2} -> {self.odd_word}"


class TestConfiguration(models.Model):
    """Nullable fields inherit from the wider scope or the built-in defaults."""
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, null=True, blank=True)
    assessment_type = models.CharField(max_length=24, blank=True, help_text="Blank applies to all assessments.")
    section_type = models.CharField(max_length=32, blank=True, choices=SectionType.choices, help_text="Blank applies to the entire assessment.")
    free_practice_questions = models.PositiveIntegerField(null=True, blank=True)
    paid_practice_questions = models.PositiveIntegerField(null=True, blank=True)
    free_module_test_attempts = models.PositiveIntegerField(null=True, blank=True)
    free_full_test_attempts = models.PositiveIntegerField(null=True, blank=True)
    module_test_questions = models.PositiveIntegerField(null=True, blank=True)
    full_test_module_questions = models.PositiveIntegerField(null=True, blank=True)
    module_time_seconds = models.PositiveIntegerField(null=True, blank=True)
    full_test_time_seconds = models.PositiveIntegerField(null=True, blank=True)
    warmup_questions = models.PositiveIntegerField(null=True, blank=True)
    test_type = models.CharField(max_length=16, blank=True, choices=[("normal", "Normal"), ("adaptive", "Adaptive")])
    starting_difficulty = models.CharField(max_length=8, blank=True, choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")])
    correct_to_increase = models.PositiveIntegerField(null=True, blank=True)
    incorrect_to_decrease = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "assessment_type", "section_type"], condition=models.Q(tenant__isnull=False), name="unique_tenant_test_configuration"),
            models.UniqueConstraint(fields=["assessment_type", "section_type"], condition=models.Q(tenant__isnull=True), name="unique_global_test_configuration"),
        ]
        ordering = ["tenant_id", "assessment_type", "section_type"]

    def clean(self):
        from .config import ASSESSMENT_CONFIG, get_assessment_module_keys
        if self.assessment_type and self.assessment_type not in ASSESSMENT_CONFIG:
            raise ValidationError({"assessment_type": "Unknown assessment."})
        if self.section_type and (not self.assessment_type or self.section_type not in get_assessment_module_keys(self.assessment_type)):
            raise ValidationError({"section_type": "Select the assessment that contains this module."})
        for name in ("module_test_questions", "full_test_module_questions", "module_time_seconds", "full_test_time_seconds", "correct_to_increase", "incorrect_to_decrease"):
            value = getattr(self, name)
            if value is not None and not 1 <= value <= (86400 if "seconds" in name else 1000):
                raise ValidationError({name: "Enter a positive value within the supported limit."})
        for name in ("free_practice_questions", "paid_practice_questions", "warmup_questions", "free_module_test_attempts", "free_full_test_attempts"):
            value = getattr(self, name)
            if value is not None and value > 1000:
                raise ValidationError({name: "At most 1,000 questions per session."})
        from .config import get_module_meta
        if self.section_type:
            group_size = get_module_meta(self.section_type).get("case_group_size", 1)
            for name in ("module_test_questions", "full_test_module_questions", "free_practice_questions", "paid_practice_questions"):
                value = getattr(self, name)
                if value is not None and value % group_size:
                    raise ValidationError({name: f"Use a multiple of {group_size} to include complete linked cases."})

    def __str__(self):
        return f"{self.tenant or 'Platform defaults'} / {self.assessment_type or 'All assessments'} / {self.section_type or 'All modules'}"


class AdaptiveSession(models.Model):
    attempt = models.OneToOneField(Attempt, on_delete=models.CASCADE, related_name="adaptive_session")
    state = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)


class AssessmentResource(models.Model):
    title = models.CharField(max_length=200)
    assessment_type = models.CharField(max_length=24)
    url = models.URLField(max_length=1000, unique=True)
    publisher = models.CharField(max_length=120)
    resource_type = models.CharField(max_length=24, choices=[("official_sample", "Official sample"), ("historical_practice", "Historical practice paper"), ("licensed_paper", "Licensed past paper")])
    rights_status = models.CharField(max_length=24, default="link_only", choices=[("link_only", "External link only"), ("permission_granted", "Reuse permission recorded"), ("public_domain", "Public domain")])
    permission_notes = models.TextField(blank=True)
    verified_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def clean(self):
        if self.rights_status != "link_only" and not self.permission_notes.strip():
            raise ValidationError({"permission_notes": "Record the permission or public-domain basis before enabling reuse."})

    def __str__(self):
        return self.title


class LearningSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, null=True, blank=True)
    assessment_type = models.CharField(max_length=32)
    kind = models.CharField(max_length=32)
    content = models.JSONField(default=dict)
    state = models.JSONField(default=dict)
    completed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="workshop_reviews")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "user", "assessment_type", "completed_at"])]


class ItemExposure(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, null=True, blank=True)
    section_type = models.CharField(max_length=32)
    signature = models.CharField(max_length=64)
    source_key = models.CharField(max_length=100)
    question = models.JSONField(default=dict)
    selected_answer = models.JSONField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    response_ms = models.PositiveIntegerField(null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "source_key"], name="unique_item_delivery")]
        indexes = [models.Index(fields=["tenant", "user", "section_type", "issued_at"])]


class ItemReport(models.Model):
    exposure = models.ForeignKey(ItemExposure, on_delete=models.CASCADE, null=True, blank=True)
    session = models.ForeignKey(LearningSession, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, null=True, blank=True)
    stage_index = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=32, choices=[("ambiguous", "Ambiguous wording"), ("answer", "Answer key"), ("display", "Display problem"), ("other", "Other")])
    detail = models.TextField(blank=True, max_length=2000)
    status = models.CharField(max_length=16, choices=[("open", "Open"), ("resolved", "Resolved")], default="open")
    reviewer_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class EditorialReview(models.Model):
    content_key = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=160)
    status = models.CharField(max_length=24, choices=[("needs_review", "Needs independent review"), ("approved", "Approved by reviewer"), ("withdrawn", "Withdrawn")], default="needs_review")
    content = models.JSONField(default=dict)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reviewer_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def clean(self):
        if isinstance(self.content, dict) and self.content.get("kind") == "template":
            if self.content.get("key") != self.content_key or not self.content.get("examples") or not isinstance(self.content["examples"], list):
                raise ValidationError("A template review requires a matching key and example questions.")
            for example in self.content["examples"]:
                if not isinstance(example, dict) or not isinstance(example.get("payload"), dict) or example.get("correct_answer", {}).get("answer") not in example["payload"].get("options", []):
                    raise ValidationError("Template examples require an offered answer key.")
        elif self.content:
            if not isinstance(self.content, dict) or not all(isinstance(self.content.get(k), str) and self.content[k].strip() for k in ("key", "title", "body")) or self.content.get("key") != self.content_key:
                raise ValidationError("A passage requires matching key, title and body.")
            items = self.content.get("items")
            if not isinstance(items, list) or not 1 <= len(items) <= 20:
                raise ValidationError("A passage requires 1–20 questions.")
            for item in items:
                if not isinstance(item, dict) or item.get("skill") not in {"inference", "assumptions", "deduction", "interpretation", "arguments"} or item.get("kind") != "choice" or not isinstance(item.get("options"), list) or len(item["options"]) != len(set(str(x) for x in item["options"])) or item.get("answer") not in item["options"] or not item.get("question") or not item.get("explanation"):
                    raise ValidationError("Each passage question requires a supported skill, unique options, a valid answer and an explanation.")
        if self.status == "approved" and (not self.content or not self.reviewer_id or not self.reviewer_notes.strip()):
            raise ValidationError("Approval requires an identified reviewer and review notes.")


class LearningReviewInvite(models.Model):
    session = models.ForeignKey(LearningSession, on_delete=models.CASCADE, related_name="peer_invites")
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, null=True, blank=True)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    feedback = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
