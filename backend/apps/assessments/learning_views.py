import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import signing
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView
from backend.apps.tenants.utils import get_current_tenant
from backend.apps.tenants.services import (
    tenant_allows_assessment,
    is_institution_tenant,
    get_tenant_access,
)
from prepgia.learning_content import WORKSHOPS
from .models import LearningSession, ItemExposure, ItemReport, EditorialReview
from .learning import start_workshop, update_workshop, session_payload
from .quality import resolve_receipt, observe_answer


def access_tenant(request, assessment):
    tenant = get_current_tenant() or request.user.tenant
    if not tenant_allows_assessment(tenant, assessment) or (
        is_institution_tenant(tenant)
        and not get_tenant_access(tenant=tenant, user=request.user, auto_enroll=False).allowed
    ):
        raise PermissionDenied("This assessment is not available in your current plan.")
    return tenant


def body(request):
    if len(request.body) > 50000:
        raise ValueError("Request is too large.")
    try:
        result = json.loads(request.body or "{}")
    except (ValueError, UnicodeDecodeError):
        raise ValueError("Send a valid JSON object.")
    if not isinstance(result, dict):
        raise ValueError("Send a JSON object.")
    return result


class WorkshopPageView(LoginRequiredMixin, TemplateView):
    template_name = "pages/workshop.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assessment = kwargs["assessment_slug"]
        if assessment not in WORKSHOPS:
            raise Http404
        access_tenant(self.request, assessment)
        from .config import get_assessment_config

        context.update(
            assessment_slug=assessment,
            assessment=get_assessment_config(assessment),
            workshops=WORKSHOPS[assessment],
        )
        return context


class AuthenticatedJSONMixin(LoginRequiredMixin):
    def handle_no_permission(self):
        return JsonResponse({"detail": "Sign in to continue."}, status=401)


class WorkshopStartView(AuthenticatedJSONMixin, View):
    def post(self, request):
        try:
            data = body(request)
            assessment = data.get("assessment_type")
            if assessment not in WORKSHOPS:
                raise ValueError("Choose a supported assessment.")
            tenant = access_tenant(request, assessment)
            session = start_workshop(request.user, tenant, assessment, data.get("kind"))
            return JsonResponse(session_payload(session))
        except PermissionError as exc:
            return JsonResponse({"detail": str(exc)}, status=403)
        except (ValueError, TypeError) as exc:
            return JsonResponse({"detail": str(exc)}, status=400)


class WorkshopSessionView(AuthenticatedJSONMixin, View):
    def get_session(self, request, session_id):
        tenant = get_current_tenant() or request.user.tenant
        session = get_object_or_404(
            LearningSession, pk=session_id, user=request.user, tenant=tenant
        )
        access_tenant(request, session.assessment_type)
        if (
            session.kind == "passage"
            and EditorialReview.objects.filter(
                content_key=session.content["key"], status="withdrawn"
            ).exists()
        ):
            raise PermissionDenied(
                "This passage was withdrawn for editorial review. Choose a different passage session."
            )
        return session

    def get(self, request, session_id):
        return JsonResponse(session_payload(self.get_session(request, session_id)))

    def post(self, request, session_id):
        session = self.get_session(request, session_id)
        try:
            return JsonResponse(
                update_workshop(session.id, request.user, session.tenant, body(request))
            )
        except (ValueError, TypeError) as exc:
            return JsonResponse({"detail": str(exc)}, status=400)


class ItemEventView(AuthenticatedJSONMixin, View):
    def post(self, request):
        try:
            data = body(request)
            tenant = get_current_tenant() or request.user.tenant
            if data.get("session_id") is not None:
                session = get_object_or_404(
                    LearningSession, pk=data["session_id"], user=request.user, tenant=tenant
                )
                access_tenant(request, session.assessment_type)
                index = data.get("stage_index")
                if type(index) is not int or not 0 <= index <= min(
                    session.state["index"], len(session.content["stages"]) - 1
                ):
                    raise ValueError("You can report only a stage already reached.")
                exposure = None
            else:
                exposure = resolve_receipt(data.get("token", ""), request.user, tenant)
                from .config import get_module_assessment_type

                access_tenant(request, get_module_assessment_type(exposure.section_type))
                session, index = None, 0
            if data.get("action") == "answer" and exposure:
                if not exposure.question.get("allow_client_observation", False):
                    raise ValueError("Test answers must use the test submission endpoint.")
                observe_answer(exposure, data.get("answer"), data.get("response_ms"))
                return JsonResponse({"saved": True})
            if data.get("action") != "report":
                raise ValueError("Unsupported item event.")
            reason, detail = data.get("reason"), data.get("detail", "")
            if (
                reason not in {"ambiguous", "answer", "display", "other"}
                or not isinstance(detail, str)
                or len(detail) > 2000
            ):
                raise ValueError("Choose a report reason and use at most 2,000 characters.")
            ItemReport.objects.get_or_create(
                user=request.user,
                tenant=tenant,
                exposure=exposure,
                session=session,
                stage_index=index,
                reason=reason,
                defaults={"detail": detail},
            )
            return JsonResponse({"saved": True})
        except (signing.BadSignature, ItemExposure.DoesNotExist, KeyError):
            return JsonResponse({"detail": "Question delivery not found."}, status=404)
        except (ValueError, TypeError) as exc:
            return JsonResponse({"detail": str(exc)}, status=400)


class WorkshopReviewInviteView(AuthenticatedJSONMixin, View):
    @transaction.atomic
    def post(self, request, session_id):
        import hashlib
        import secrets
        from datetime import timedelta
        from django.urls import reverse
        from django.utils import timezone
        from .models import LearningReviewInvite

        tenant = get_current_tenant() or request.user.tenant
        session = get_object_or_404(
            LearningSession.objects.select_for_update(),
            pk=session_id,
            user=request.user,
            tenant=tenant,
            completed_at__isnull=False,
        )
        access_tenant(request, session.assessment_type)
        try:
            data = body(request)
        except ValueError as exc:
            return JsonResponse({"detail": str(exc)}, status=400)
        if data.get("revoke") is True:
            session.peer_invites.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
            return JsonResponse({"revoked": True})
        # Replace prior links so there is at most one live review invitation.
        session.peer_invites.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
        token = secrets.token_urlsafe(32)
        LearningReviewInvite.objects.create(
            session=session,
            tenant=tenant,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=timezone.now() + timedelta(days=7),
        )
        return JsonResponse(
            {
                "url": request.build_absolute_uri(
                    reverse("pages:workshop-peer-review", args=[token])
                ),
                "expires_in_days": 7,
            }
        )


class WorkshopPeerReviewView(LoginRequiredMixin, TemplateView):
    template_name = "pages/workshop_peer_review.html"

    def get_invite(self, request, token, lock=False):
        import hashlib
        from django.utils import timezone
        from .models import LearningReviewInvite

        tenant = get_current_tenant() or request.user.tenant
        from backend.apps.tenants.models import TenantMembership

        if (
            request.user.tenant_id != getattr(tenant, "id", None)
            and not request.user.is_superuser
            and not TenantMembership.objects.filter(
                tenant=tenant,
                user=request.user,
                status="active",
                access_expires_at__gt=timezone.now(),
            ).exists()
        ):
            raise Http404
        rows = LearningReviewInvite.objects.select_related("session")
        if lock:
            rows = rows.select_for_update()
        invite = get_object_or_404(
            rows,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            tenant=tenant,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            session__completed_at__isnull=False,
        )
        access_tenant(request, invite.session.assessment_type)
        return invite

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invite = self.get_invite(self.request, kwargs["token"])
        stages = invite.session.content["stages"]
        answers = invite.session.state["answers"]
        rows = [
            {
                "question": stage["question"],
                "passage": stage.get("passage", ""),
                "answer": answer["answer"].get("text", str(answer["answer"]))
                if isinstance(answer["answer"], dict)
                else answer["answer"],
                "tables": [
                    *stage.get("context_tables", []),
                    *([stage["data_table"]] if stage.get("data_table") else []),
                ],
                "rubric": stage.get("rubric", []),
                "reference": stage.get("reference", ""),
                "explanation": stage["explanation"],
            }
            for stage, answer in zip(stages, answers)
        ]
        context.update(
            invite=invite,
            review_rows=rows,
            can_review=self.request.user.id != invite.session.user_id
            and (not invite.reviewer_id or invite.reviewer_id == self.request.user.id),
        )
        return context

    def post(self, request, token):
        from django.db import transaction
        from django.utils import timezone

        with transaction.atomic():
            invite = self.get_invite(request, token, lock=True)
            if request.user.id == invite.session.user_id or (
                invite.reviewer_id and invite.reviewer_id != request.user.id
            ):
                raise PermissionDenied(
                    "This link is reserved for another reviewer. Use the workshop self-review rubric for your own response."
                )
            feedback = request.POST.get("feedback", "").strip()
            if not 30 <= len(feedback) <= 6000:
                return self.render_to_response(
                    {
                        **self.get_context_data(token=token),
                        "error": "Write between 30 and 6,000 characters of specific feedback.",
                    },
                    status=400,
                )
            invite.reviewer = request.user
            invite.feedback = feedback
            invite.reviewed_at = timezone.now()
            invite.save(update_fields=["reviewer", "feedback", "reviewed_at"])
        return self.render_to_response({**self.get_context_data(token=token), "saved": True})
