from datetime import date
from django.db import migrations

RESOURCES = [
    ("McKinsey PST Practice Test A — 2013 official sample (26 questions)", "consulting", "https://www.mckinsey.com/~/media/mckinsey/careers%20redesign/interviewing/main/problem%20solving%20test%20pdfs/practice-test-a.ashx", "McKinsey / APTMetrics", "historical_practice", "Publisher-hosted historical practice sample, copyright 2013 APTMetrics. Includes 26 questions and an answer key. Not a verified actual past examination paper or current Solve assessment. External link only; no reproduction permission established."),
    ("McKinsey PST Practice Test B — 2006 official sample (26 questions)", "consulting", "https://www.mckinsey.com/~/media/mckinsey/careers%20redesign/interviewing/main/problem%20solving%20test%20pdfs/practice-test-b.ashx", "McKinsey / APTMetrics", "historical_practice", "Publisher-hosted historical practice sample, copyright 2006 APTMetrics. Includes 26 questions and an answer key. Not a verified actual past examination paper or current Solve assessment. External link only; no reproduction permission established."),
    ("McKinsey official case study — Talbot Trucks", "consulting_cases", "https://www.mckinsey.com/careers/interviewing/talbot-trucks", "McKinsey", "official_sample", "Official interview practice case linked from McKinsey's interviewing page. Not a verified previous-year examination question. External link only; no copying into the playable bank."),
    ("McKinsey official case study — Beautify", "consulting_cases", "https://www.mckinsey.com/careers/interviewing/beautify", "McKinsey", "official_sample", "Official interview practice case linked from McKinsey's interviewing page. Not a verified previous-year examination question. External link only."),
    ("Bain official case study — Coffee Shop Co.", "consulting_cases", "https://www.bain.com/careers/hiring-process/interviewing/coffee-case-study/", "Bain", "official_sample", "Bain-authored public case preparation with calculations and recommendation guidance. Published as a practice case, not a verified actual past exam. External link only."),
    ("Bain official case study — FashionCo.", "consulting_cases", "https://www.bain.com/careers/hiring-process/interviewing/fashion-case-study/", "Bain", "official_sample", "Bain-authored public case preparation. Published as a practice case, not a verified actual past exam. External link only."),
    ("Bain official case interview preparation hub", "consulting_cases", "https://www.bain.com/careers/hiring-process/case-interview/", "Bain", "official_sample", "Official hub containing Bain-designed practice cases and separately labelled external resources. External link only; not a past-paper archive."),
]


def seed(apps, schema_editor):
    Resource = apps.get_model("assessments", "AssessmentResource")
    for title, assessment, url, publisher, kind, notes in RESOURCES:
        Resource.objects.using(schema_editor.connection.alias).get_or_create(url=url, defaults={"title": title, "assessment_type": assessment, "publisher": publisher, "resource_type": kind, "rights_status": "link_only", "permission_notes": notes, "verified_at": date(2026, 11, 14)})


class Migration(migrations.Migration):
    dependencies = [("assessments", "0022_peer_review_invitation")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
