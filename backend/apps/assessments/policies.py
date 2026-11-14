from copy import deepcopy
from django.db.models import Q
from .config import get_assessment_config, get_module_meta, get_section_question_count
from .models import TestConfiguration, FreeTierModuleLimit

POLICY_FIELDS = [
    field.name
    for field in TestConfiguration._meta.fields
    if field.name not in {"id", "tenant", "assessment_type", "section_type", "updated_at"}
]


def resolve_test_configuration(tenant, assessment_type, section_type=""):
    config = get_assessment_config(assessment_type)
    module = get_module_meta(section_type) if section_type else {}
    values = dict(
        free_practice_questions=10,
        paid_practice_questions=100,
        free_module_test_attempts=2,
        free_full_test_attempts=1,
        module_test_questions=get_section_question_count(section_type) if section_type else 30,
        full_test_module_questions=int(
            config.get("full_test_question_counts", {}).get(
                section_type, module.get("time_limit_seconds", 30)
            )
        ),
        module_time_seconds=module.get("time_limit_seconds", 180),
        full_test_time_seconds=int(config["full_test_duration_minutes"] * 60),
        warmup_questions=config["full_test_practice_count"],
        test_type="normal",
        starting_difficulty="medium",
        correct_to_increase=2,
        incorrect_to_decrease=1,
    )
    old = (
        FreeTierModuleLimit.objects.filter(
            tenant=tenant, assessment_type=assessment_type, section_type=section_type
        ).first()
        if section_type
        else None
    )
    candidates = TestConfiguration.objects.filter(
        Q(tenant__isnull=True) | Q(tenant=tenant),
        assessment_type__in=["", assessment_type],
        section_type__in=["", section_type],
    )
    ordered = sorted(
        candidates,
        key=lambda row: (
            row.tenant_id is not None,
            bool(row.assessment_type),
            bool(row.section_type),
        ),
    )
    for row in ordered:
        for name in POLICY_FIELDS:
            value = getattr(row, name)
            if value is not None and value != "":
                values[name] = value
    # Backward compatibility for legacy callers which still create special
    # limits. Default legacy rows never mask an administrator's central values.
    if old:
        explicit = {
            name
            for row in ordered
            for name in POLICY_FIELDS
            if getattr(row, name) is not None and getattr(row, name) != ""
        }
        if old.practice_question_limit != 10 and "free_practice_questions" not in explicit:
            values["free_practice_questions"] = old.practice_question_limit
        if old.test_attempt_limit != 2 and "free_module_test_attempts" not in explicit:
            values["free_module_test_attempts"] = old.test_attempt_limit
    group_size = module.get("case_group_size", 1)
    if (
        values["module_test_questions"] % group_size
        or values["full_test_module_questions"] % group_size
    ):
        # Global settings also apply to cases: round up to keep every case whole.
        for name in ("module_test_questions", "full_test_module_questions"):
            values[name] = ((values[name] + group_size - 1) // group_size) * group_size
    for name in ("free_practice_questions", "paid_practice_questions"):
        values[name] = ((values[name] + group_size - 1) // group_size) * group_size
    return values


def runtime_assessment_config(tenant, assessment_type):
    config = deepcopy(get_assessment_config(assessment_type))
    policy = resolve_test_configuration(tenant, assessment_type)
    config["test_type"] = policy["test_type"]
    config["full_test_duration_minutes"] = policy["full_test_time_seconds"] / 60
    config["full_test_practice_count"] = policy["warmup_questions"]
    config["full_test_question_counts"] = {
        m["key"]: resolve_test_configuration(tenant, assessment_type, m["key"])[
            "full_test_module_questions"
        ]
        for m in config["modules"]
    }
    count = sum(config["full_test_question_counts"].values())
    is_adaptive = policy["test_type"] == "adaptive"
    config["full_test_meta_tail"] = f"{count} questions" + (" · Adaptive" if is_adaptive else "")
    config["full_test_description"] = (
        f"Every section, back to back, in {policy['full_test_time_seconds'] / 60:g} minutes. "
        + (
            "Timed like the real test, and the difficulty adjusts to your answers."
            if is_adaptive
            else "Timed like the real test, with a score for every section at the end."
        )
    )
    return config
