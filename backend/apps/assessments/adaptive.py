"""Durable, server-authoritative staircase practice sessions.

Difficulty is a training heuristic, not an IRT ability estimate or publisher score.
Answers are locked when accepted; an idempotent retry cannot change an answer.
"""

from dataclasses import asdict
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from prepgia.generators import generate_question
from prepgia.question_types import semantic_question_signature
from .models import AdaptiveSession, Attempt, AttemptMode, AttemptStatus, AttemptAnswer
from .config import get_module_meta

LEVELS = ("easy", "medium", "hard")


class AdaptiveInputError(ValueError):
    pass


def adaptive_order(attempt):
    sections = list(attempt.sections.order_by("order_index"))
    result = []
    used = {s.id: 0 for s in sections}
    while any(used[s.id] < s.question_count for s in sections):
        for section in sections:
            group = get_module_meta(section.section_type).get("case_group_size", 1)
            for _ in range(min(group, section.question_count - used[section.id])):
                result.append(
                    {
                        "section_id": section.id,
                        "section_type": section.section_type,
                        "module_index": used[section.id],
                    }
                )
                used[section.id] += 1
    return result


def _complete(attempt, session):
    from .services import record_test_progress

    sections = list(attempt.sections.order_by("order_index"))
    for section in sections:
        rows = [row for row in session.state["answers"] if row["section_id"] == section.id]
        section.correct_answers_count = sum(row["correct"] for row in rows)
        section.incorrect_answers_count = len(rows) - section.correct_answers_count
        section.adjusted_score = section.correct_answers_count
        section.save(
            update_fields=["correct_answers_count", "incorrect_answers_count", "adjusted_score"]
        )
        AttemptAnswer.objects.bulk_create(
            [
                AttemptAnswer(
                    attempt_section=section,
                    tenant=attempt.tenant,
                    question_index=row["module_index"],
                    user_answer={
                        "selected_option": row["selected_option"],
                        "difficulty": row["difficulty"],
                    },
                    is_correct=row["correct"],
                )
                for row in rows
            ]
        )
        record_test_progress(
            attempt.user, section.section_type, section.adjusted_score, tenant=attempt.tenant
        )
    attempt.overall_adjusted_score = sum(s.correct_answers_count for s in sections)
    attempt.status = AttemptStatus.COMPLETED
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["overall_adjusted_score", "status", "completed_at"])


def _response(attempt, state):
    from .services import _serialize_generated_question_for_player

    done = attempt.status == AttemptStatus.COMPLETED
    response = {
        "attempt_id": attempt.id,
        "complete": done,
        "answered": len(state.get("answers", [])),
        "total": len(state.get("order", [])),
        "deadline": state.get("deadline"),
    }
    if done:
        response.update(
            score=attempt.overall_adjusted_score,
            overall_score=attempt.overall_adjusted_score,
            sections=[
                {
                    "title": get_module_meta(s.section_type)["title"],
                    "correct": s.correct_answers_count,
                    "incorrect": s.incorrect_answers_count,
                }
                for s in attempt.sections.order_by("order_index")
            ],
            scoring_note="Practice raw score; difficulty adapts during training. Not a publisher percentile.",
        )
    else:
        index = len(state["answers"])
        from .quality import issue_question
        current = _serialize_generated_question_for_player(state["questions"][index], False)
        current["report_token"] = issue_question(attempt.user, attempt.tenant, state["questions"][index], allow_observation=False)
        response.update(
            question_index=index,
            question=current,
            module_title=get_module_meta(state["order"][index]["section_type"])["title"],
        )
    return response


@transaction.atomic
def advance_adaptive(attempt_id, user, payload, tenant=None):
    from backend.apps.tenants.utils import get_current_tenant

    tenant = tenant or get_current_tenant() or user.tenant
    attempt = (
        Attempt.objects.select_for_update()
        .select_related("user")
        .get(pk=attempt_id, user=user, tenant=tenant)
    )
    from backend.apps.tenants.services import (
        tenant_allows_assessment,
        is_institution_tenant,
        get_tenant_access,
    )

    if not tenant_allows_assessment(tenant, attempt.assessment_type) or (
        is_institution_tenant(tenant)
        and not get_tenant_access(tenant=tenant, user=user, auto_enroll=False).allowed
    ):
        raise AdaptiveInputError("This assessment is no longer available in your plan.")
    if attempt.configuration.get("test_type") != "adaptive":
        raise AdaptiveInputError("This is not an adaptive attempt.")
    session, _ = AdaptiveSession.objects.select_for_update().get_or_create(
        attempt=attempt, defaults={"state": {}}
    )
    if attempt.status == AttemptStatus.COMPLETED:
        return _response(attempt, session.state)
    if attempt.status not in {AttemptStatus.CREATED, AttemptStatus.IN_PROGRESS}:
        raise AdaptiveInputError("This attempt is no longer active.")
    state = session.state
    policy = attempt.configuration
    if not state:
        duration = (
            policy["full_test_time_seconds"]
            if attempt.mode == AttemptMode.FULL_TEST
            else next(iter(policy["modules"].values()))["module_time_seconds"]
        )
        state.update(
            order=adaptive_order(attempt),
            questions=[],
            answers=[],
            levels={},
            streaks={},
            groups={},
            deadline=(timezone.now() + timedelta(seconds=duration)).isoformat(),
        )
    if timezone.now() >= parse_datetime(state["deadline"]) or payload.get("finish") is True:
        session.state = state
        session.save()
        _complete(attempt, session)
        return _response(attempt, state)
    if "selected_option" in payload:
        index = payload.get("question_index")
        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or not 0 <= index < len(state["questions"])
        ):
            raise AdaptiveInputError("Invalid question index.")
        if index > len(state["answers"]):
            raise AdaptiveInputError("Answer the current question before proceeding.")
        selected = str(payload["selected_option"])
        if index < len(state["answers"]):
            if state["answers"][index]["selected_option"] != selected:
                raise AdaptiveInputError("An accepted answer cannot be changed.")
        elif index == len(state["answers"]):
            generated = state["questions"][index]
            if selected not in [str(value) for value in generated["payload"]["options"]]:
                raise AdaptiveInputError("Select one of the offered answers.")
            slot = state["order"][index]
            section = slot["section_type"]
            correct = selected == str(generated["correct_answer"]["answer"])
            from .quality import issue_question, resolve_receipt, observe_answer
            token = issue_question(user, tenant, generated, allow_observation=False)
            observe_answer(resolve_receipt(token, user, tenant), selected)
            state["answers"].append(
                {
                    **slot,
                    "selected_option": selected,
                    "correct": correct,
                    "difficulty": generated["difficulty"],
                }
            )
            rules = policy["modules"][section]
            level = state["levels"].get(section, LEVELS.index(rules["starting_difficulty"]))
            streak = state["streaks"].get(section, 0)
            streak = max(streak, 0) + 1 if correct else min(streak, 0) - 1
            if streak >= rules["correct_to_increase"]:
                level, streak = min(level + 1, 2), 0
            elif streak <= -rules["incorrect_to_decrease"]:
                level, streak = max(level - 1, 0), 0
            state["levels"][section], state["streaks"][section] = level, streak
    if len(state["answers"]) == len(state["order"]):
        session.state = state
        session.save()
        _complete(attempt, session)
        return _response(attempt, state)
    index = len(state["answers"])
    if index == len(state["questions"]):
        slot = state["order"][index]
        section = slot["section_type"]
        group_size = get_module_meta(section).get("case_group_size", 1)
        group_id = f"{section}:{slot['module_index'] // group_size}"
        rules = policy["modules"][section]
        level = state["levels"].get(section, LEVELS.index(rules["starting_difficulty"]))
        level = state["groups"].setdefault(group_id, level)
        difficulty = LEVELS[level]
        seen = {semantic_question_signature(q["payload"]) for q in state["questions"]}
        group_start = slot["module_index"] - slot["module_index"] % group_size
        from .quality import recent_signatures, item_signature, family_key, withdrawn_families
        withdrawn = withdrawn_families(section)
        recent = recent_signatures(user, tenant, section)
        for retry in range(100):
            candidates = [
                generate_question(
                    section,
                    difficulty,
                    f"adaptive:{attempt.id}:{section}:{difficulty}:retry-{retry}:{module_index}",
                )
                for module_index in range(group_start, group_start + group_size)
            ]
            signatures = [
                semantic_question_signature(candidate.payload) for candidate in candidates
            ]
            repeated = recent.intersection(item_signature(asdict(q)) for q in candidates)
            if any(family_key(asdict(q)) in withdrawn for q in candidates):
                continue
            if not seen.intersection(signatures) and len(set(signatures)) == group_size and (not repeated or retry >= 60):
                state["questions"].extend(asdict(candidate) for candidate in candidates)
                break
        else:
            raise AdaptiveInputError(
                "No eligible distinct question is available. End this attempt and ask your administrator to check the bank and review settings."
            )
    session.state = state
    session.save()
    return _response(attempt, state)
