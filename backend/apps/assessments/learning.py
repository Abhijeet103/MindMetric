"""Server-authoritative workshops with progressive disclosure and saved drafts."""

import uuid
from decimal import Decimal, InvalidOperation
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from prepgia.learning_content import WORKSHOPS, SECTIONS, make_workshop
from prepgia.passage_bank import PASSAGES
from .models import LearningSession, EditorialReview
from .policies import resolve_test_configuration


def section_for(assessment, kind):
    if assessment == "consulting_cases":
        return "linked_case"
    if assessment == "consulting" and kind == "case":
        return "consulting_case"
    return SECTIONS[kind]


@transaction.atomic
def start_workshop(user, tenant, assessment, kind):
    from .services import has_unlimited_module_access

    get_user_model().objects.select_for_update().get(pk=user.pk)
    if kind not in dict(WORKSHOPS.get(assessment, [])):
        raise ValueError("Workshop is not available for this assessment.")
    active = (
        LearningSession.objects.filter(
            user=user,
            tenant=tenant,
            assessment_type=assessment,
            kind=kind,
            completed_at__isnull=True,
        )
        .order_by("-id")
        .first()
    )
    if active and not (
        kind == "passage"
        and EditorialReview.objects.filter(
            content_key=active.content["key"], status="withdrawn"
        ).exists()
    ):
        return active
    section = section_for(assessment, kind)
    policy = resolve_test_configuration(tenant, assessment, section)
    limit = (
        policy["paid_practice_questions"]
        if has_unlimited_module_access(user, tenant=tenant)
        else policy["free_practice_questions"]
    )
    if limit == 0:
        raise PermissionError("Practice is disabled by your current practice allowance.")
    passage = None
    if kind == "passage":
        reviews = {r.content_key: r for r in EditorialReview.objects.all()}
        eligible = [
            p
            for p in PASSAGES
            if p["key"] not in reviews or reviews[p["key"]].status != "withdrawn"
        ]
        if not eligible:
            raise ValueError("Passage practice is awaiting editorial review.")
        recent = list(
            LearningSession.objects.filter(user=user, tenant=tenant, kind=kind)
            .order_by("-id")
            .values_list("content", flat=True)[:20]
        )
        keys = [c.get("key") for c in recent]
        passage = next(
            (p for p in eligible if p["key"] not in keys),
            min(eligible, key=lambda p: -keys.index(p["key"]) if p["key"] in keys else -100),
        )
        review = reviews.get(passage["key"])
        if review and review.status == "approved":
            passage = review.content
    content = make_workshop(kind, uuid.uuid4().hex, passage)
    if len(content["stages"]) > limit:
        raise PermissionError(
            f"This workshop needs {len(content['stages'])} practice questions; your configured session allowance is {limit}. Choose a shorter exercise or ask your administrator to adjust it."
        )
    return LearningSession.objects.create(
        user=user,
        tenant=tenant,
        assessment_type=assessment,
        kind=kind,
        content=content,
        state={
            "index": 0,
            "answers": [],
            "drafts": {},
            "self_reviews": {},
            "stage_started_at": timezone.now().isoformat(),
            "practice_allowance": limit,
        },
    )


def numeric(value):
    if isinstance(value, bool):
        raise ValueError("Enter a number.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError("Enter a valid finite number.")
    if not result.is_finite() or abs(result) > Decimal("1e15"):
        raise ValueError("Enter a finite number within the supported range.")
    return float(result)


def check_answer(stage, answer):
    kind = stage["kind"]
    if kind in {"written", "estimate"}:
        if (
            not isinstance(answer, dict)
            or not isinstance(answer.get("text"), str)
            or not 30 <= len(answer["text"].strip()) <= 6000
        ):
            raise ValueError(
                "Write between 30 and 6,000 characters so the rubric can be used meaningfully."
            )
        cleaned = {"text": answer["text"].strip()}
        if kind == "estimate":
            value = numeric(answer.get("estimate"))
            if value < 0:
                raise ValueError("Revenue estimates cannot be negative.")
            cleaned["estimate"] = value
        return cleaned, None
    if kind == "numeric":
        cleaned = numeric(answer)
        return cleaned, abs(cleaned - stage["answer"]) <= stage.get("tolerance", 0.01) + 1e-9
    if kind == "choice":
        if answer not in stage["options"]:
            raise ValueError("Choose an offered option.")
        return answer, answer == stage["answer"]
    if kind in {"schedule", "chart_builder", "node_path"}:
        if not isinstance(answer, list):
            raise ValueError("Complete the interactive response.")
        if kind == "chart_builder":
            if len(answer) != len(stage["labels"]):
                raise ValueError("Set every bar value.")
            cleaned = [numeric(v) for v in answer]
            if any(v < 0 for v in cleaned):
                raise ValueError("Request counts cannot be negative.")
            return cleaned, all(abs(a - b) <= 0.01 for a, b in zip(cleaned, stage["answer"]))
        if (
            len(answer) != (len(stage["options"]) if kind == "schedule" else stage["length"])
            or len(set(str(a) for a in answer)) != len(answer)
            or any(a not in stage["options"] for a in answer)
        ):
            raise ValueError("Use the required number of distinct offered names or nodes.")
        if kind == "schedule":
            rules = stage["rules"]
            valid = (
                all(answer.index(a) < answer.index(b) for a, b in rules["before"])
                and abs(
                    answer.index(rules["not_adjacent"][0]) - answer.index(rules["not_adjacent"][1])
                )
                > 1
            )
            return answer, valid
        return answer, answer == stage["answer"]
    raise ValueError("Unsupported response type.")


def session_payload(session):
    index = session.state["index"]
    stages = session.content["stages"]
    answers = session.state["answers"]
    result = {
        "session_id": session.id,
        "title": session.content["title"],
        "intro": session.content["intro"],
        "stage_index": index,
        "total": len(stages),
        "complete": bool(session.completed_at),
        "assessment_type": session.assessment_type,
        "review_status": "Original practice; independent review pending",
    }
    if session.kind == "passage":
        review = EditorialReview.objects.filter(content_key=session.content["key"]).first()
        if (
            review
            and review.status == "approved"
            and review.content == session.content.get("editorial_snapshot")
        ):
            result["review_status"] = (
                "Editorially approved; practice material, not publisher calibrated"
            )
    if session.completed_at:
        result["human_review"] = session.review_notes if session.reviewed_at else ""
        result["peer_reviews"] = list(
            session.peer_invites.filter(reviewed_at__isnull=False).values("feedback", "reviewed_at")
        )
        result.update(
            correct=sum(a["correct"] is True for a in answers),
            graded=sum(a["correct"] is not None for a in answers),
            written=sum(a["correct"] is None for a in answers),
            responses=answers,
            self_reviews=session.state["self_reviews"],
        )
        return result
    stage = stages[index]
    public = {
        k: v
        for k, v in stage.items()
        if k not in {"answer", "explanation", "rubric", "reference", "rules"}
    }
    result.update(
        stage=public,
        draft=session.state["drafts"].get(str(index), ""),
        answered=index < len(answers),
    )
    if result["answered"]:
        result["feedback"] = {
            "correct": answers[index]["correct"],
            "explanation": stage["explanation"],
            "rubric": stage.get("rubric", []),
            "reference": stage.get("reference", ""),
            "answer": stage.get("answer"),
            "response": answers[index]["answer"],
            "self_review": session.state["self_reviews"].get(str(index), []),
        }
    return result


@transaction.atomic
def update_workshop(session_id, user, tenant, payload):
    session = LearningSession.objects.select_for_update().get(
        pk=session_id, user=user, tenant=tenant
    )
    if session.completed_at:
        return session_payload(session)
    index = session.state["index"]
    action = payload.get("action")
    supplied = payload.get("stage_index")
    if not isinstance(supplied, int) or isinstance(supplied, bool):
        raise ValueError("A valid stage index is required.")
    if action == "next" and supplied == index - 1:
        return session_payload(session)
    if supplied != index:
        raise ValueError("The session has moved to another stage. Reload to resume.")
    state, stage = session.state, session.content["stages"][index]
    if action == "draft":
        text = payload.get("text")
        if (
            stage["kind"] not in {"written", "estimate"}
            or not isinstance(text, str)
            or len(text) > 6000
            or index < len(state["answers"])
        ):
            raise ValueError("This draft cannot be saved.")
        if stage["kind"] == "estimate":
            estimate = payload.get("estimate", "")
            if estimate != "":
                estimate = numeric(estimate)
                if estimate < 0:
                    raise ValueError("Revenue estimates cannot be negative.")
            state["drafts"][str(index)] = {"text": text, "estimate": estimate}
        else:
            state["drafts"][str(index)] = text
    elif action == "answer":
        answer, correct = check_answer(stage, payload.get("answer"))
        if index < len(state["answers"]):
            if state["answers"][index]["answer"] != answer:
                raise ValueError("A submitted response cannot be changed.")
        else:
            from django.utils.dateparse import parse_datetime

            elapsed = int(
                (timezone.now() - parse_datetime(state["stage_started_at"])).total_seconds() * 1000
            )
            state["answers"].append(
                {"answer": answer, "correct": correct, "response_ms": max(0, elapsed)}
            )
    elif action == "self_review":
        values = payload.get("scores")
        if (
            index >= len(state["answers"])
            or not stage.get("rubric")
            or not isinstance(values, list)
            or len(values) != len(stage["rubric"])
            or any(type(v) is not int or not 0 <= v <= 2 for v in values)
        ):
            raise ValueError("Review each rubric criterion on the 0–2 self-review scale.")
        state["self_reviews"][str(index)] = values
    elif action == "next":
        if index >= len(state["answers"]):
            raise ValueError("Submit this response first.")
        state["index"] += 1
        state["stage_started_at"] = timezone.now().isoformat()
        if state["index"] == len(session.content["stages"]):
            session.completed_at = timezone.now()
    else:
        raise ValueError("Unknown workshop action.")
    session.state = state
    session.save(update_fields=["state", "completed_at", "updated_at"])
    return session_payload(session)
