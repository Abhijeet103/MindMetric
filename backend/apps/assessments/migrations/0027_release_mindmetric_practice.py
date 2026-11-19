from django.db import migrations


TRACKS = {
    "situational_judgement": ("MindMetric Situational Judgement", "Original workplace decisions with explicit principles and explanations.", 1),
    "work_simulation": ("MindMetric Work Simulations", "Linked inbox, operational data, policy and email-response exercises.", 1),
    "verbal_reasoning": ("MindMetric Verbal Reasoning", "Original passage-based true, false and cannot-say practice.", 1),
    "aptitude": ("MindMetric Aptitude", "Arithmetic, verbal logic and visual reasoning by subject and difficulty.", 3),
}


def release(apps, schema_editor):
    alias = schema_editor.connection.alias
    Tenant = apps.get_model("tenants", "Tenant")
    Track = apps.get_model("assessments", "AssessmentTrack")
    for tenant in Tenant.objects.using(alias).filter(tenant_type="platform"):
        allowed = list(tenant.allowed_assessments or [])
        for key, (title, description, count) in TRACKS.items():
            if key not in allowed:
                allowed.append(key)
            Track.objects.using(alias).get_or_create(tenant_id=tenant.pk, assessment_type=key, defaults={
                "title": title, "description": description, "module_count": count,
                "trust_line": "Original MindMetric practice · Three difficulty levels",
                "available_languages": ["English"], "visibility_state": "accessible", "is_active": True,
            })
        tenant.allowed_assessments = allowed
        tenant.save(using=alias, update_fields=["allowed_assessments"])


class Migration(migrations.Migration):
    dependencies = [("assessments", "0026_mindmetric_practice_sections"), ("tenants", "0005_seed_demo_tenant")]
    operations = [migrations.RunPython(release, migrations.RunPython.noop)]
