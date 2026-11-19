"""Student-facing features from the Nov 2026 redesign: application deadlines,
the company lookup and admin-published legal pages."""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.template.loader import render_to_string

from . import hiring_research

from .models import ApplicationDeadline, EmployerAssessment, HiringResearch, LegalPage

MAX_DEADLINES_PER_USER = 50


def _track_choices(request) -> list[tuple[str, str]]:
    from .views import HOME_TEST_PICKER_LABELS, _build_practice_assessment_cards

    choices = [("", "I don't know yet")]
    for card in _build_practice_assessment_cards(request):
        if card.get("can_open"):
            label = HOME_TEST_PICKER_LABELS.get(card["key"], (card["title"], ""))[0]
            choices.append((card["key"], label))
    return choices


def _track_titles(request) -> dict[str, str]:
    return dict(_track_choices(request)[1:])


class ApplicationDeadlineForm(forms.ModelForm):
    class Meta:
        model = ApplicationDeadline
        fields = ["company", "assessment_type", "due_date"]
        labels = {"company": "Company", "assessment_type": "Test", "due_date": "Assessment due"}
        widgets = {
            "company": forms.TextInput(attrs={"placeholder": "e.g. the bank or firm you applied to", "autocomplete": "organization"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assessment_type"] = forms.ChoiceField(
            choices=_track_choices(request) if request else [("", "I don't know yet")],
            required=False,
            label="Test",
        )

    def clean_company(self):
        return self.cleaned_data["company"].strip()

    def clean_due_date(self):
        due_date = self.cleaned_data["due_date"]
        if due_date < timezone.localdate():
            raise forms.ValidationError("Pick today or a later date.")
        return due_date


def build_study_plan(deadline: ApplicationDeadline | None, track_titles: dict[str, str]) -> dict | None:
    """Suggest today's step for the nearest deadline.

    The steps follow the plan on the home page: learn the formats first, then
    run timed simulations, then keep the last day light.
    """
    if deadline is None:
        return None
    days = deadline.days_left
    test = track_titles.get(deadline.assessment_type, "")
    practice_url = (
        reverse("pages:assessment-practice", args=[deadline.assessment_type])
        if deadline.assessment_type
        else reverse("pages:practice")
    )
    full_test_url = (
        reverse("pages:assessment-full-test", args=[deadline.assessment_type]) if deadline.assessment_type else practice_url
    )
    if not deadline.assessment_type:
        return {
            "headline": f"Find out which test {deadline.company} uses",
            "detail": "Check your invite email or search the company lookup, then add the test here so we can plan your days.",
            "action_label": "Search companies",
            "action_url": reverse("pages:company-lookup") + f"?q={deadline.company}",
        }
    if days <= 0:
        return {
            "headline": "Assessment day",
            "detail": f"Skip new material. Do one short {test} warm-up to get your pace, then take the real test somewhere quiet.",
            "action_label": "Warm up",
            "action_url": practice_url,
        }
    if days <= 2:
        return {
            "headline": f"Run a timed {test} simulation",
            "detail": "You're close. A full test under real timing shows whether your pace is ready, and the results point to one last thing to fix.",
            "action_label": "Start full test",
            "action_url": full_test_url,
        }
    return {
        "headline": f"Drill one {test} section",
        "detail": f"{days} days to go. Spend 20 minutes on untimed practice in your weakest section and read every explanation.",
        "action_label": "Practice now",
        "action_url": practice_url,
    }


def dashboard_deadline_context(request) -> dict:
    today = timezone.localdate()
    deadlines = list(ApplicationDeadline.objects.filter(user=request.user, due_date__gte=today))
    titles = _track_titles(request)
    for deadline in deadlines:
        deadline.test_title = titles.get(deadline.assessment_type, "")
    return {
        "application_deadlines": deadlines,
        "study_plan": build_study_plan(deadlines[0] if deadlines else None, titles),
        "deadline_form": ApplicationDeadlineForm(request=request),
    }


class ApplicationDeadlineCreateView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request):
        form = ApplicationDeadlineForm(request.POST, request=request)
        if ApplicationDeadline.objects.filter(user=request.user).count() >= MAX_DEADLINES_PER_USER:
            messages.error(request, "You've reached the limit of saved applications. Remove an old one first.")
        elif form.is_valid():
            deadline = form.save(commit=False)
            deadline.user = request.user
            deadline.save()
            messages.success(request, f"Added {deadline.company}.")
        else:
            errors = "; ".join(error for field_errors in form.errors.values() for error in field_errors)
            messages.error(request, f"Couldn't add that application: {errors}")
        return redirect(reverse("pages:dashboard") + "#applications")


class ApplicationDeadlineDeleteView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, deadline_id: int):
        deadline = get_object_or_404(ApplicationDeadline, id=deadline_id, user=request.user)
        deadline.delete()
        messages.success(request, f"Removed {deadline.company}.")
        return redirect(reverse("pages:dashboard") + "#applications")


class CompanyLookupView(TemplateView):
    template_name = "pages/company_lookup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("company", self.request.GET.get("q", "")).strip()[:120]
        entries = EmployerAssessment.objects.filter(is_published=True)
        if query:
            normalized = hiring_research.normalize_search(query)
            entries = [entry for entry in entries if normalized and (
                normalized in hiring_research.normalize_search(entry.company)
                or normalized in hiring_research.normalize_search(entry.industry)
            )]
        titles = _track_titles(self.request)
        results = []
        for entry in entries[:50]:
            tests = [
                {"key": key, "title": titles[key], "url": reverse("pages:assessment-practice", args=[key])}
                for key in entry.assessment_types
                if key in titles
            ]
            if tests:
                results.append({"entry": entry, "tests": tests})
        context.update(
            {
                "page_title": "Company hiring process and interview preparation | MindMetric",
                "meta_description": "Research hiring stages and interview experiences for your company and role, then build a preparation plan with MindMetric practice.",
                "query": query,
                "research_role": self.request.GET.get("role", "").strip()[:120],
                "results": results,
                "has_any_entries": EmployerAssessment.objects.filter(is_published=True).exists(),
                "research_available": hiring_research.available(),
            }
        )
        report_id = self.request.GET.get("report", "")
        if report_id and self.request.user.is_authenticated:
            try:
                from uuid import UUID
                job = HiringResearch.objects.filter(pk=UUID(report_id), tenant_id=_research_tenant_id(self.request)).first()
            except ValueError:
                job = None
            if job:
                context.update(_research_context(self.request, job))
                context.update(query=job.company, research_role=job.role)
        return context


def _research_tenant_id(request):
    return getattr(getattr(request, "tenant", None), "pk", None)


def _research_context(request, job):
    from copy import deepcopy

    report = deepcopy(job.report)
    titles = _track_titles(request)
    def practice_link(key):
        return {"title": titles[key], "url": reverse("pages:assessment-practice", args=[key])}
    if report:
        catalogue = hiring_research.assessment_catalogue(job.tenant_id)
        for assessment in report.get("assessments", []):
            match = catalogue.get(hiring_research.normalize_search(assessment["name"]))
            assessment["in_catalogue"] = bool(match)
            if match and match["key"] in titles:
                assessment["test"] = practice_link(match["key"])
        report["practice"] = [
            {**item, **practice_link(item["key"])} for item in report["practice"] if item["key"] in titles
        ]
        for step in report["plan"]:
            step["tests"] = [practice_link(key) for key in step["practice_keys"] if key in titles]
    return {"research_job": job, "research_report": report,
            "research_status_url": reverse("pages:hiring-research-status", args=[job.pk])}


def _research_json(request, job):
    result = {"id": str(job.pk), "status": job.status,
              "cached": getattr(job, "from_cache", False),
              "status_url": reverse("pages:hiring-research-status", args=[job.pk])}
    if job.status in {"completed", "failed"}:
        result["html"] = render_to_string("pages/_hiring_report.html", _research_context(request, job), request=request)
    response = JsonResponse(result, status=202 if job.status == "pending" else 200)
    response["Cache-Control"] = "no-store"
    return response


class HiringResearchStartView(View):
    http_method_names = ["post"]

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Sign in to research a company and role."}, status=401)
        if not hiring_research.available():
            return JsonResponse({"error": "Live hiring research is not available yet. You can still browse sourced assessment entries below."}, status=503)
        form_class = hiring_research.HiringSearchForm if "query" in request.POST else hiring_research.HiringResearchForm
        form = form_class(request.POST)
        if not form.is_valid():
            return JsonResponse({"error": "Enter a valid company or role to search.", "fields": form.errors.get_json_data()}, status=400)
        try:
            job = hiring_research.start_research(form.cleaned_data, request.user.pk, _research_tenant_id(request))
        except hiring_research.ResearchLimit as exc:
            return JsonResponse({"error": str(exc)}, status=429)
        except hiring_research.ResearchError as exc:
            return JsonResponse({"error": str(exc)}, status=503)
        return _research_json(request, job)


class HiringResearchStatusView(View):
    http_method_names = ["get"]

    def get(self, request, report_id):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Sign in again to view your research."}, status=401)
        job = get_object_or_404(HiringResearch, pk=report_id, tenant_id=_research_tenant_id(request))
        if job.status == "pending" and not hiring_research.available():
            return JsonResponse({"error": "Live hiring research is temporarily unavailable."}, status=503)
        try:
            hiring_research.refresh_research(job)
        except hiring_research.ResearchError as exc:
            return JsonResponse({"error": str(exc)}, status=503)
        return _research_json(request, job)


class LegalPageView(TemplateView):
    template_name = "pages/legal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = LegalPage.objects.filter(slug=self.kwargs["slug"], is_published=True).first()
        if page is None:
            raise Http404("Page not found.")
        blocks = []
        for chunk in page.body.replace("\r\n", "\n").split("\n\n"):
            chunk = chunk.strip()
            if not chunk:
                continue
            if chunk.startswith("## "):
                blocks.append({"kind": "heading", "text": chunk[3:].strip()})
            else:
                blocks.append({"kind": "paragraph", "text": chunk})
        context.update({"page": page, "blocks": blocks, "page_title": f"{page.title} | MindMetric"})
        return context


def legal_links(request):
    """Footer links to published legal pages; unpublished ones fall back to email."""
    try:
        published = set(LegalPage.objects.filter(is_published=True).values_list("slug", flat=True))
    except Exception:  # Database not ready (e.g. during migrate).
        published = set()
    return {"legal_published": published}


def feedback_categories(request):
    """Categories for the site-wide feedback popup in base.html."""
    from .models import PortalFeedback

    return {"feedback_categories": PortalFeedback.Category.choices}
