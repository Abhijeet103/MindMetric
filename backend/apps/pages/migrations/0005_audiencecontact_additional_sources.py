from django.db import migrations, models


def backfill_additional_audience_contacts(apps, schema_editor):
    AudienceContact = apps.get_model("pages", "AudienceContact")
    AssessmentTrackWaitlistEntry = apps.get_model("assessments", "AssessmentTrackWaitlistEntry")
    TenantStudentInvite = apps.get_model("tenants", "TenantStudentInvite")

    for entry in AssessmentTrackWaitlistEntry.objects.all().iterator():
        AudienceContact.objects.get_or_create(
            email=entry.email.strip().lower(),
            defaults={
                "tenant_id": entry.tenant_id,
                "user_id": entry.user_id,
                "source": "assessment_waitlist",
                "marketing_opt_in": False,
            },
        )
    for invite in TenantStudentInvite.objects.all().iterator():
        AudienceContact.objects.get_or_create(
            email=invite.email.strip().lower(),
            defaults={
                "tenant_id": invite.tenant_id,
                "user_id": invite.accepted_by_id,
                "full_name": invite.full_name,
                "source": "institution_invite",
                "marketing_opt_in": False,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0004_audiencecontact_saleinquiry_marketing_opt_in"),
        ("assessments", "0014_freetiermodulelimit"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="audiencecontact",
            name="source",
            field=models.CharField(
                choices=[
                    ("user_account", "User account"),
                    ("sales_inquiry", "Sales inquiry"),
                    ("test_suggestion", "Test suggestion"),
                    ("assessment_waitlist", "Assessment waitlist"),
                    ("institution_invite", "Institution invite"),
                    ("admin", "Added by admin"),
                ],
                default="admin",
                max_length=32,
            ),
        ),
        migrations.RunPython(backfill_additional_audience_contacts, migrations.RunPython.noop),
    ]
