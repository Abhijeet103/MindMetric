"""Recruiter-owned assessments with server-authoritative timing and reviewable browser signals."""

import json
from copy import deepcopy
import secrets
from datetime import timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views import View
from django.views.generic import TemplateView

from backend.apps.accounts.models import AccountType
from backend.apps.billing import recruiter_credits
from backend.apps.billing.models import RECRUITER_WELCOME_CREDITS
from backend.apps.billing.regions import get_request_country_code
from backend.apps.billing.services import BillingConfigurationError, BillingWebhookError
from backend.apps.assessments.config import ASSESSMENT_CONFIG, get_module_meta
from backend.apps.assessments.services import _build_question_batch, _serialize_generated_question_for_player
from backend.apps.tenants.services import tenant_allows_assessment
from .models import RecruiterAssessment, RecruiterSubmission

EVENT_KINDS = {"tab_hidden", "window_blur", "fullscreen_exit", "paste_attempt", "copy_attempt", "fullscreen_unavailable"}
MAX_EVENTS = 200


def current_tenant(request):
    tenant = getattr(request, "tenant", None)
    if tenant is None:
        raise PermissionDenied("Open the workspace on your MindMetric site.")
    return tenant


class RecruiterAssessmentForm(forms.Form):
    title = forms.CharField(max_length=160, label="Assessment title")
    organization = forms.CharField(max_length=160, label="Company or organisation")
    role_title = forms.CharField(max_length=160, required=False, label="Role being hired for")
    instructions = forms.CharField(max_length=3000, required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Instructions for candidates")
    modules = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, label="Skills to assess")
    difficulty = forms.ChoiceField(choices=[("easy", "Foundation"), ("medium", "Intermediate"), ("hard", "Advanced"), ("mixed", "Mixed levels")], initial="medium")
    questions_per_module = forms.TypedChoiceField(choices=[(4, "4"), (8, "8"), (12, "12")], coerce=int, initial=8)
    duration_minutes = forms.IntegerField(min_value=5, max_value=120, initial=20, label="Total time (minutes)")
    open_days = forms.TypedChoiceField(choices=[(1, "1 day"), (3, "3 days"), (7, "7 days"), (14, "14 days"), (30, "30 days")], coerce=int, initial=7, label="Accept starts for")
    max_candidates = forms.IntegerField(min_value=1, max_value=500, initial=100, label="Maximum candidates")
    allowed_emails = forms.CharField(max_length=5000, required=False, widget=forms.Textarea(attrs={"rows": 3}), label="Restrict to these candidate emails (optional)", help_text="One email per line, or comma-separated. Leave blank to allow signed-in students with the link.")

    def __init__(self, *args, tenant, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_groups = available_test_groups(tenant)
        self.fields["modules"].choices = [
            (group["title"], [(module["key"], module["title"]) for module in group["modules"]]) for group in self.test_groups
        ]

    def clean_allowed_emails(self):
        raw = self.cleaned_data["allowed_emails"].replace(",", "\n").splitlines()
        emails = list(dict.fromkeys(value.strip().casefold() for value in raw if value.strip()))
        if len(emails) > 100:
            raise forms.ValidationError("Use at most 100 email addresses.")
        for email in emails:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError("Enter valid email addresses only.")
        return emails

    def clean(self):
        data = super().clean()
        if len(data.get("modules", [])) * data.get("questions_per_module", 0) > 60:
            raise forms.ValidationError("Choose at most 60 questions in total. Reduce the number of modules or questions per module.")
        return data


def available_test_groups(tenant):
    """Tests the tenant offers, each with its sections, for the step-by-step picker."""
    return [
        {"key": key, "title": config["title"], "description": config.get("description", ""),
         "modules": [{"key": module["key"], "title": module["title"], "description": module.get("description", "")} for module in config["modules"]]}
        for key, config in ASSESSMENT_CONFIG.items() if tenant_allows_assessment(tenant, key) and config.get("modules")
    ]


WORKSPACE_MODE_KEY = "workspace_mode"


def set_workspace_mode(request, mode):
    """Remember whether a dual-role account is currently working as a student or a recruiter."""
    if request.user.is_authenticated and request.user.is_recruiter and request.session.get(WORKSPACE_MODE_KEY) != mode:
        request.session[WORKSPACE_MODE_KEY] = mode


def prefers_recruiter_workspace(request):
    return getattr(request.user, "is_recruiter", False) and request.session.get(WORKSPACE_MODE_KEY) != "student"


class RecruiterEnableForm(forms.Form):
    organization = forms.CharField(max_length=160, label="Company or organisation")


def employers_only(request, form=None, status=403):
    """Student accounts see no recruiter tools until they explicitly add a recruiter workspace."""
    if form is None and request.user.is_authenticated:
        form = RecruiterEnableForm(initial={"organization": request.user.organization})
    return render(request, "pages/recruiter/employers_only.html", {"page_title": "For employers | MindMetric", "welcome_credits": RECRUITER_WELCOME_CREDITS, "form": form}, status=status)


class RecruiterOnlyMixin(LoginRequiredMixin):
    login_url = "/login/?as=recruiter"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_recruiter:
            return employers_only(request)
        set_workspace_mode(request, "recruiter")
        return super().dispatch(request, *args, **kwargs)


class RecruiterEnableView(LoginRequiredMixin, View):
    """Add a recruiter workspace to an existing (student) account. The account keeps its student side."""

    login_url = "/login/?as=recruiter"

    def post(self, request):
        if request.user.is_recruiter:
            return redirect("pages:recruiter-dashboard")
        form = RecruiterEnableForm(request.POST)
        if not form.is_valid():
            return employers_only(request, form=form, status=400)
        current_tenant(request)
        request.user.account_type = AccountType.RECRUITER
        request.user.organization = form.cleaned_data["organization"]
        request.user.save(update_fields=["account_type", "organization"])
        recruiter_credits.grant_welcome_credits(request.user)
        set_workspace_mode(request, "recruiter")
        messages.success(request, f"Recruiter workspace added with {RECRUITER_WELCOME_CREDITS} free candidate credits. Switch back to Student anytime from the top bar.")
        return redirect("pages:recruiter-dashboard")


class RequiresCreditsMixin:
    """Creating an assessment needs at least one candidate credit."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_recruiter and recruiter_credits.credit_balance(request.user) < 1:
            messages.info(request, "You have no candidate credits left. Buy a credit pack to create a new assessment.")
            return redirect("pages:recruiter-credits")
        return super().dispatch(request, *args, **kwargs)


def assessment_skills(assessment):
    if assessment.custom_questions:
        return list(dict.fromkeys(item["payload"]["metadata"]["subject"] for item in assessment.custom_questions))
    return [get_module_meta(key)["title"] for key in assessment.modules]


def assessment_question_total(assessment):
    return len(assessment.custom_questions) if assessment.custom_questions else len(assessment.modules)*assessment.questions_per_module


def owned_assessment(request, assessment_id):
    return get_object_or_404(RecruiterAssessment, pk=assessment_id, tenant=current_tenant(request), recruiter=request.user)


@transaction.atomic
def finish_submission(submission, status):
    # Caller locks the submission; keep completion idempotent.
    if submission.status != "active":
        return
    totals = {}
    score = 0
    for index, item in enumerate(submission.questions):
        key = item["section_type"]
        if key == "recruiter_custom":
            title = item["payload"]["metadata"]["subject"]
            key = "custom:" + title
        else:
            title = get_module_meta(key)["title"]
        total = totals.setdefault(key, {"title": title, "correct": 0, "total": 0})
        total["total"] += 1
        if submission.answers.get(str(index)) == str(item["correct_answer"]["answer"]):
            score += 1
            total["correct"] += 1
    submission.status = status
    submission.score = score
    submission.section_scores = list(totals.values())
    submission.completed_at = timezone.now()
    submission.save(update_fields=["status", "score", "section_scores", "completed_at"])


def expire_submissions(assessment):
    for pk in assessment.submissions.filter(status="active", deadline_at__lte=timezone.now()).values_list("pk", flat=True):
        with transaction.atomic():
            submission = RecruiterSubmission.objects.select_for_update().get(pk=pk)
            finish_submission(submission, "expired")


@method_decorator(never_cache, name="dispatch")
class RecruiterDashboardView(RecruiterOnlyMixin, View):
    def get(self, request):
        recruiter_credits.grant_welcome_credits(request.user)
        assessments = RecruiterAssessment.objects.filter(recruiter=request.user, tenant=current_tenant(request))
        for assessment in assessments:
            expire_submissions(assessment)
        assessments = assessments.annotate(candidate_count=Count("submissions"))
        return render(request, "pages/recruiter/dashboard.html", {"page_title": "Recruiter dashboard | MindMetric", "assessments": assessments,
            "credit_balance": recruiter_credits.credit_balance(request.user)})


@method_decorator(never_cache, name="dispatch")
class RecruiterCreditsView(RecruiterOnlyMixin, View):
    def context(self, request, **extra):
        country = get_request_country_code(request)
        tiers = recruiter_credits.tier_prices(country)
        return {
            "page_title": "Candidate credits | MindMetric",
            "credit_balance": recruiter_credits.credit_balance(request.user),
            "tiers": tiers,
            "tiers_json": [{"name": t.name, "min": t.min_candidates, "max": t.max_candidates, "unit": str(t.unit_price)} for t in tiers],
            "lots": request.user.recruiter_credit_lots.order_by("-created_at")[:20],
            "purchases": request.user.recruiter_credit_purchases.exclude(status="expired")[:20],
            "min_purchase": recruiter_credits.MIN_PURCHASE,
            "max_purchase": recruiter_credits.MAX_PURCHASE,
            "welcome_credits": RECRUITER_WELCOME_CREDITS,
            "candidates_value": 50,
            **extra,
        }

    def get(self, request):
        recruiter_credits.grant_welcome_credits(request.user)
        return render(request, "pages/recruiter/credits.html", self.context(request))

    def post(self, request):
        try:
            candidates = int(request.POST.get("candidates", ""))
        except ValueError:
            candidates = None
        try:
            if candidates is None:
                raise recruiter_credits.RecruiterCreditError("Enter a whole number of candidates.")
            approval_url = recruiter_credits.create_credit_order(
                request.user, candidates, base_url=f"{request.scheme}://{request.get_host()}",
                country_code=get_request_country_code(request), tenant=getattr(request, "tenant", None),
            )
        except (recruiter_credits.RecruiterCreditError, BillingConfigurationError, BillingWebhookError) as exc:
            messages.error(request, str(exc))
            return render(request, "pages/recruiter/credits.html", self.context(request, candidates_value=candidates or 50), status=400)
        return redirect(approval_url)


@method_decorator(never_cache, name="dispatch")
class RecruiterCreateView(RecruiterOnlyMixin, RequiresCreditsMixin, View):
    def render_form(self, request, form, status=200):
        selected = set(form.data.getlist("modules")) if form.is_bound else set()
        groups = [{**group, "selected": any(m["key"] in selected for m in group["modules"])} for group in form.test_groups]
        return render(request, "pages/recruiter/create.html", {"page_title": "Create assessment | MindMetric", "form": form, "test_groups": groups,
            "selected_modules": selected, "credit_balance": recruiter_credits.credit_balance(request.user)}, status=status)

    def get(self, request):
        form = RecruiterAssessmentForm(tenant=current_tenant(request), initial={"organization": request.user.organization})
        return self.render_form(request, form)

    def post(self, request):
        tenant = current_tenant(request)
        form = RecruiterAssessmentForm(request.POST, tenant=tenant)
        if form.is_valid():
            values = dict(form.cleaned_data)
            days = values.pop("open_days")
            assessment = RecruiterAssessment.objects.create(tenant=tenant, recruiter=request.user, closes_at=timezone.now() + timedelta(days=days), **values)
            messages.success(request, "Assessment created. Copy the link below to share it with candidates.")
            return redirect("pages:recruiter-assessment", assessment_id=assessment.pk)
        return self.render_form(request, form, status=400)


@method_decorator(never_cache, name="dispatch")
class RecruiterAssessmentView(RecruiterOnlyMixin, View):
    def get(self, request, assessment_id):
        assessment = owned_assessment(request, assessment_id)
        expire_submissions(assessment)
        submissions = assessment.submissions.select_related("candidate").all()
        share_url = request.build_absolute_uri(reverse("pages:recruiter-invite", args=[assessment.share_token]))
        return render(request, "pages/recruiter/detail.html", {"page_title": f"{assessment.title} | Recruiter", "assessment": assessment, "submissions": submissions, "share_url": share_url,
            "skills": assessment_skills(assessment), "question_total": assessment_question_total(assessment), "credit_balance": recruiter_credits.credit_balance(request.user)})

    def post(self, request, assessment_id):
        assessment = owned_assessment(request, assessment_id)
        action = request.POST.get("action")
        if action not in {"close", "open"}:
            return JsonResponse({"detail": "Choose open or close."}, status=400)
        assessment.is_open = action == "open"
        assessment.save(update_fields=["is_open"])
        return redirect("pages:recruiter-assessment", assessment_id=assessment.pk)


@method_decorator(never_cache, name="dispatch")
class RecruiterResultView(RecruiterOnlyMixin, TemplateView):
    template_name = "pages/recruiter/result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = get_object_or_404(RecruiterSubmission.objects.select_related("assessment", "candidate"), pk=kwargs["submission_id"], assessment__recruiter=self.request.user, assessment__tenant=current_tenant(self.request))
        expire_submissions(submission.assessment)
        submission.refresh_from_db()
        counts = {}
        for event in submission.monitoring_events:
            counts[event["kind"]] = counts.get(event["kind"], 0) + 1
        context.update(page_title="Candidate result | MindMetric", submission=submission, event_counts=counts)
        return context


def candidate_assessment(request, token):
    return get_object_or_404(RecruiterAssessment, share_token=token, tenant=current_tenant(request))


@method_decorator(never_cache, name="dispatch")
class RecruiterInviteView(View):
    def get(self, request, token):
        assessment = candidate_assessment(request, token)
        submission = None
        eligible = True
        if request.user.is_authenticated:
            eligible = not assessment.allowed_emails or request.user.email.casefold() in assessment.allowed_emails
            submission = assessment.submissions.filter(candidate=request.user).first()
            if submission and submission.status == "active" and submission.deadline_at <= timezone.now():
                with transaction.atomic():
                    submission = RecruiterSubmission.objects.select_for_update().get(pk=submission.pk)
                    finish_submission(submission, "expired")
        return render(request, "pages/recruiter/invite.html", {"page_title": f"{assessment.title} | MindMetric", "assessment": assessment, "submission": submission, "eligible": eligible,
            "skills": assessment_skills(assessment), "question_total": assessment_question_total(assessment)})


class CandidateJSONMixin(LoginRequiredMixin):
    login_url = "/login/"

    def handle_no_permission(self):
        return JsonResponse({"detail": "Sign in to take this assessment."}, status=401)


def request_data(request):
    if len(request.body) > 100000:
        raise ValueError("Request is too large.")
    try:
        data = json.loads(request.body or "{}")
    except (ValueError, UnicodeDecodeError):
        raise ValueError("Send a valid JSON object.")
    if not isinstance(data, dict):
        raise ValueError("Send a JSON object.")
    return data


def candidate_preview(item):
    preview = _serialize_generated_question_for_player(item, False)
    if item["section_type"] == "recruiter_custom":
        preview.update(instruction=item["payload"]["prompt"]["instruction"], question_text=item["payload"]["prompt"]["question"], reveal_mode="question_only")
    # Linked generators use their seed in the internal case ID. Never expose it.
    if preview.get("case_study"):
        preview["case_study"] = {key: value for key, value in preview["case_study"].items() if key != "id"}
    return preview


def submission_payload(submission):
    result = {"id": str(submission.pk), "status": submission.status, "deadline": submission.deadline_at.isoformat(), "server_now": timezone.now().isoformat(),
        "url": reverse("pages:recruiter-candidate-session", args=[submission.pk])}
    if submission.status == "active":
        result["questions"] = [candidate_preview(item) for item in submission.questions]
        result["answers"] = submission.answers
        result["revision"] = submission.answer_revision
    # Candidates get submission confirmation, never keys, explanations or recruiter-only results.
    return result


@method_decorator(never_cache, name="dispatch")
class RecruiterCandidateStartView(CandidateJSONMixin, View):
    def post(self, request, token):
        try:
            data = request_data(request)
            if data.get("consent") is not True:
                raise ValueError("Acknowledge the monitoring notice before starting.")
            with transaction.atomic():
                assessment = get_object_or_404(RecruiterAssessment.objects.select_for_update(), share_token=token, tenant=current_tenant(request))
                if assessment.allowed_emails and request.user.email.casefold() not in assessment.allowed_emails:
                    raise PermissionDenied("This assessment is restricted to invited email addresses.")
                if assessment.recruiter_id == request.user.pk:
                    raise ValueError("Use a separate student account to take your assessment.")
                submission = assessment.submissions.filter(candidate=request.user).first()
                if submission:
                    submission = RecruiterSubmission.objects.select_for_update().get(pk=submission.pk)
                    if submission.status == "active" and submission.deadline_at <= timezone.now():
                        finish_submission(submission, "expired")
                    return JsonResponse(submission_payload(submission))
                if not assessment.accepts_candidates:
                    raise ValueError("This assessment is closed to new starts.")
                if assessment.submissions.count() >= assessment.max_candidates:
                    raise ValueError("This assessment has reached its candidate limit.")
                # Each new candidate start uses one of the recruiter's credits (resumes are free).
                credit_lot = recruiter_credits.consume_credit(assessment.recruiter)
                questions = deepcopy(assessment.custom_questions)
                seed = secrets.token_hex(24)
                for key in assessment.modules:
                    if not tenant_allows_assessment(assessment.tenant, get_module_meta(key)["assessment_type"]):
                        raise PermissionDenied("A skill in this assessment is no longer available.")
                    questions.extend(_build_question_batch(seed, key, "recruitment", assessment.questions_per_module, assessment.difficulty))
                now = timezone.now()
                submission = RecruiterSubmission.objects.create(assessment=assessment, candidate=request.user, questions=questions, total_questions=len(questions), started_at=now,
                    deadline_at=now + timedelta(minutes=assessment.duration_minutes), last_seen_at=now, consented_at=now, credit_lot=credit_lot)
                return JsonResponse(submission_payload(submission), status=201)
        except (ValueError, TypeError, KeyError, recruiter_credits.RecruiterCreditError) as exc:
            return JsonResponse({"detail": str(exc)}, status=400)


@method_decorator(never_cache, name="dispatch")
class RecruiterCandidateSessionView(CandidateJSONMixin, View):
    def get(self, request, submission_id):
        with transaction.atomic():
            submission = get_object_or_404(RecruiterSubmission.objects.select_for_update(), pk=submission_id, candidate=request.user, assessment__tenant=current_tenant(request))
            if submission.status == "active" and submission.deadline_at <= timezone.now():
                finish_submission(submission, "expired")
            return JsonResponse(submission_payload(submission))

    def post(self, request, submission_id):
        try:
            data = request_data(request)
            with transaction.atomic():
                submission = get_object_or_404(RecruiterSubmission.objects.select_for_update(), pk=submission_id, candidate=request.user, assessment__tenant=current_tenant(request))
                if submission.status != "active":
                    return JsonResponse(submission_payload(submission))
                now = timezone.now()
                if now >= submission.deadline_at:
                    finish_submission(submission, "expired")
                    return JsonResponse(submission_payload(submission))
                answers = data.get("answers", {})
                revision = data.get("revision", 0)
                if type(revision) is not int or not 0 <= revision <= 1_000_000_000:
                    raise ValueError("Invalid answer revision.")
                if answers and "revision" not in data:
                    raise ValueError("Include an answer revision.")
                if not isinstance(answers, dict) or len(answers) > submission.total_questions:
                    raise ValueError("Invalid answers.")
                valid = {}
                for index, answer in answers.items():
                    if not isinstance(index, str) or not index.isdigit() or str(int(index)) != index or not 0 <= int(index) < submission.total_questions:
                        raise ValueError("Invalid question index.")
                    options = [str(value) for value in submission.questions[int(index)]["payload"]["options"]]
                    if not isinstance(answer, str) or answer not in options:
                        raise ValueError("Select an offered answer.")
                    valid[index] = answer
                events = data.get("events", [])
                if not isinstance(events, list) or len(events) > 20 or any(not isinstance(kind, str) or kind not in EVENT_KINDS for kind in events):
                    raise ValueError("Invalid monitoring event.")
                if type(data.get("submit", False)) is not bool:
                    raise ValueError("Invalid submission action.")
                records = [{"kind": kind, "at": now.isoformat(), "source": "browser"} for kind in events]
                if now - submission.last_seen_at > timedelta(seconds=40):
                    records.append({"kind": "connection_gap", "at": now.isoformat(), "source": "server", "seconds": int((now-submission.last_seen_at).total_seconds())})
                if valid and revision > submission.answer_revision:
                    submission.answers.update(valid)
                    submission.answer_revision = revision
                submission.monitoring_events = (submission.monitoring_events + records)[:MAX_EVENTS]
                submission.last_seen_at = now
                submission.save(update_fields=["answers", "answer_revision", "monitoring_events", "last_seen_at"])
                if data.get("submit") is True:
                    finish_submission(submission, "submitted")
                return JsonResponse({key: value for key, value in submission_payload(submission).items() if key not in {"questions", "answers"}})
        except (ValueError, TypeError) as exc:
            return JsonResponse({"detail": str(exc)}, status=400)
