"""Tenant-scoped exposure history and server-checked pilot observations."""

import hashlib
from django.core import signing
from django.db import transaction
from django.utils import timezone
from prepgia.question_types import semantic_question_signature
from .models import ItemExposure, EditorialReview


def item_signature(question):
    return hashlib.sha256(semantic_question_signature(question["payload"]).encode()).hexdigest()


def recent_signatures(user, tenant, section):
    if not user or not user.is_authenticated:
        return set()
    return set(
        ItemExposure.objects.filter(user=user, tenant=tenant, section_type=section)
        .order_by("-issued_at")
        .values_list("signature", flat=True)[:200]
    )


def issue_question(user, tenant, question, allow_observation=True):
    """An issuance is not proof that a question was viewed or answered."""
    if not user or not user.is_authenticated:
        return ""
    exposure, _ = ItemExposure.objects.get_or_create(
        user=user,
        source_key=question["payload"]["question_id"],
        defaults={
            "tenant": tenant,
            "section_type": question["section_type"],
            "signature": item_signature(question),
            "question": {**question, "allow_client_observation": allow_observation},
        },
    )
    return signing.dumps({"id": exposure.id}, salt="item-delivery", compress=True)


def resolve_receipt(token, user, tenant):
    data = signing.loads(token, salt="item-delivery", max_age=60 * 60 * 24 * 30)
    return ItemExposure.objects.get(pk=data["id"], user=user, tenant=tenant)


@transaction.atomic
def observe_answer(exposure, answer, response_ms=None):
    exposure = ItemExposure.objects.select_for_update().get(pk=exposure.pk)
    allowed = [str(option) for option in exposure.question["payload"]["options"]]
    selected = str(answer)
    if selected not in allowed:
        raise ValueError("Select an offered answer.")
    if exposure.answered_at:
        if exposure.selected_answer != selected:
            raise ValueError("An accepted observation cannot be changed.")
        return exposure
    exposure.selected_answer = selected
    exposure.is_correct = selected == str(exposure.question["correct_answer"]["answer"])
    # Client timing is optional and is not used for scoring or calibration.
    if response_ms is not None:
        if (
            isinstance(response_ms, bool)
            or not isinstance(response_ms, int)
            or not 0 <= response_ms <= 86400000
        ):
            raise ValueError("Invalid response time.")
        exposure.response_ms = response_ms
    exposure.answered_at = timezone.now()
    exposure.save(update_fields=["selected_answer", "is_correct", "response_ms", "answered_at"])
    return exposure


def family_key(question):
    family = question["payload"].get("metadata", {}).get("subtype", "unknown")
    return family.split("_step_")[0] if "_step_" in family else family


def withdrawn_families(section):
    prefix = f"template:{section}:"
    return {
        key.removeprefix(prefix)
        for key in EditorialReview.objects.filter(
            status="withdrawn", content_key__startswith=prefix
        ).values_list("content_key", flat=True)
    }
