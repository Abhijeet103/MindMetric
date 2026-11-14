"""Results screen shown after a timed section test, full test or adaptive test."""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.urls import NoReverseMatch, reverse
from django.views.generic import TemplateView

from backend.apps.assessments.config import get_assessment_config, get_module_meta
from backend.apps.assessments.models import Attempt, AttemptMode, AttemptStatus


def _module_title(section_type: str) -> str:
    try:
        return get_module_meta(section_type)["title"]
    except KeyError:
        return section_type.replace("_", " ").title()


def _drill_url(assessment_type: str, section_type: str) -> str:
    try:
        return reverse("pages:assessment-section-detail", args=[assessment_type, section_type]) + "?mode=practice"
    except NoReverseMatch:
        return reverse("pages:practice")


def _format_duration(seconds: int) -> str:
    minutes, secs = divmod(max(0, int(seconds)), 60)
    return f"{minutes}:{secs:02d}"


def build_attempt_results(attempt: Attempt) -> dict:
    """Summarise a completed attempt for the results screen.

    Accuracy is correct answers over the questions in the section, so unanswered
    questions count against the section just as they would on the real test.
    """
    sections = []
    for section in attempt.sections.order_by("order_index"):
        total = section.question_count or (section.correct_answers_count + section.incorrect_answers_count)
        correct = section.correct_answers_count
        answered = correct + section.incorrect_answers_count
        accuracy = round((correct / total) * 100) if total else 0
        sections.append(
            {
                "section_type": section.section_type,
                "title": _module_title(section.section_type),
                "correct": correct,
                "incorrect": section.incorrect_answers_count,
                "answered": answered,
                "unanswered": max(0, total - answered),
                "total": total,
                "accuracy": accuracy,
                "drill_url": _drill_url(attempt.assessment_type, section.section_type),
            }
        )

    total_questions = sum(item["total"] for item in sections)
    total_correct = sum(item["correct"] for item in sections)
    total_answered = sum(item["answered"] for item in sections)
    weakest = min(sections, key=lambda item: (item["accuracy"], -item["unanswered"])) if sections else None
    if weakest and len(sections) > 1 and all(item["accuracy"] == weakest["accuracy"] for item in sections):
        weakest = None

    elapsed_seconds = None
    if attempt.completed_at and attempt.started_at:
        elapsed_seconds = int((attempt.completed_at - attempt.started_at).total_seconds())

    try:
        assessment_title = get_assessment_config(attempt.assessment_type)["title"]
    except KeyError:
        assessment_title = attempt.assessment_type

    is_full_test = attempt.mode == AttemptMode.FULL_TEST or len(sections) > 1
    return {
        "attempt": attempt,
        "assessment_title": assessment_title,
        "assessment_slug": attempt.assessment_type,
        "title": f"{assessment_title} full test" if is_full_test else (sections[0]["title"] if sections else assessment_title),
        "is_full_test": is_full_test,
        "sections": sections,
        "total_questions": total_questions,
        "total_correct": total_correct,
        "total_answered": total_answered,
        "accuracy": round((total_correct / total_questions) * 100) if total_questions else 0,
        "weakest": weakest,
        "elapsed": _format_duration(elapsed_seconds) if elapsed_seconds is not None else "",
        "seconds_per_answer": round(elapsed_seconds / total_answered) if elapsed_seconds and total_answered else None,
    }


class AttemptResultsView(LoginRequiredMixin, TemplateView):
    template_name = "pages/results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = (
            Attempt.objects.filter(id=self.kwargs["attempt_id"], user=self.request.user, status__in=[AttemptStatus.COMPLETED, AttemptStatus.EXPIRED])
            .prefetch_related("sections")
            .first()
        )
        if attempt is None:
            raise Http404("Result not found.")
        results = build_attempt_results(attempt)
        context.update(results)
        context.update(
            {
                "page_title": f"Your results: {results['title']} | MindMetric",
                "show_upgrade": not getattr(self.request, "effective_access_active", False),
                "assessment_url": reverse("pages:assessment-practice", args=[attempt.assessment_type]),
            }
        )
        return context
