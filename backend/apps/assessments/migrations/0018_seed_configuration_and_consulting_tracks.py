from datetime import date
from django.db import migrations

TRACKS = {
    "consulting": ("Consulting Problem Solving", "Charts, business mathematics, evidence evaluation and short cases.", 3),
    "watson_glaser": ("Watson–Glaser-style Critical Thinking", "Inference, assumptions, deduction, interpretation and arguments using original passages.", 5),
    "consulting_cases": ("Consulting Case Practice", "Independent BCG/Bain-style case skills with original linked exhibits and questions.", 1),
}

RESOURCES = [
    ("McKinsey official interview practice cases", "consulting", "https://www.mckinsey.com/careers/interviewing", "McKinsey", "official_sample", "Official preparation cases, not past exam papers. External link only; no republication permission verified."),
    ("McKinsey PST Practice Test C — historical sample", "consulting", "https://www.mckinsey.com/~/media/McKinsey/Careers%20REDESIGN/Interviewing/Main/Problem%20Solving%20Test%20PDFs/practice-test-C.ashx", "McKinsey / APTMetrics", "historical_practice", "Dated 2006; official historical practice paper, not verified previous-year questions or the current Solve format. Copyright retained by APTMetrics; link only."),
    ("Pearson TalentLens official Watson Glaser practice", "watson_glaser", "https://www.talentlens.com/practice-tests.html", "Pearson TalentLens", "official_sample", "Publisher-hosted practice and explanations. All rights reserved; external link only."),
    ("BCG official case preparation", "consulting_cases", "https://careers.bcg.com/global/en/case-interview-preparation", "BCG", "official_sample", "Official case preparation and simulation links. External link only."),
    ("Bain official interview preparation", "consulting_cases", "https://www.bain.com/careers/hiring-process/interviewing/", "Bain", "official_sample", "Official interview preparation. External link only; no copied questions."),
]


def seed(apps, schema_editor):
    alias = schema_editor.connection.alias
    Configuration = apps.get_model("assessments", "TestConfiguration")
    Legacy = apps.get_model("assessments", "FreeTierModuleLimit")
    Track = apps.get_model("assessments", "AssessmentTrack")
    Tenant = apps.get_model("tenants", "Tenant")
    Resource = apps.get_model("assessments", "AssessmentResource")
    Configuration.objects.using(alias).get_or_create(tenant=None, assessment_type="", section_type="")
    # Carry forward customised legacy limits; ordinary seeded defaults inherit.
    for old in Legacy.objects.using(alias).all():
        changes = {}
        if old.practice_question_limit != 10:
            changes["free_practice_questions"] = old.practice_question_limit
        if old.test_attempt_limit != 2:
            changes["free_module_test_attempts"] = old.test_attempt_limit
        if changes:
            Configuration.objects.using(alias).get_or_create(tenant_id=old.tenant_id, assessment_type=old.assessment_type, section_type=old.section_type, defaults=changes)
    # New business/case tracks start as adaptive practice. Existing GIA/CCAT/SHL
    # stay normal until an administrator explicitly opts them in.
    for key in ("consulting", "consulting_cases"):
        Configuration.objects.using(alias).get_or_create(tenant=None, assessment_type=key, section_type="", defaults={"test_type": "adaptive"})
    for tenant in Tenant.objects.using(alias).all():
        allowed = list(tenant.allowed_assessments or [])
        if tenant.tenant_type == "platform":
            for key in TRACKS:
                if key not in allowed:
                    allowed.append(key)
            tenant.allowed_assessments = allowed
            tenant.save(using=alias, update_fields=["allowed_assessments"])
        for key, (title, description, count) in TRACKS.items():
            if key not in allowed:
                continue
            track, created = Track.objects.using(alias).get_or_create(tenant=tenant, assessment_type=key, defaults={"title": title, "description": description, "module_count": count, "trust_line": "Original questions · Independent practice", "available_languages": ["English"], "visibility_state": "accessible", "is_active": True})
            if not created:
                track.module_count = count
                track.title, track.description = title, description
                track.trust_line = "Original questions · Independent practice"
                if track.visibility_state == "upcoming":
                    track.visibility_state = "accessible"
                track.save(using=alias, update_fields=["module_count", "title", "description", "trust_line", "visibility_state"])
    for title, assessment, url, publisher, kind, notes in RESOURCES:
        Resource.objects.using(alias).get_or_create(url=url, defaults={"title": title, "assessment_type": assessment, "publisher": publisher, "resource_type": kind, "rights_status": "link_only", "permission_notes": notes, "verified_at": date(2026, 11, 14)})


class Migration(migrations.Migration):
    dependencies = [("assessments", "0017_central_configuration_adaptive_and_cases")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
