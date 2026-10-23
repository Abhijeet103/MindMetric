from django.db import migrations, models


def backfill_contacted_back(apps, schema_editor):
    inquiries = apps.get_model("pages", "SaleInquiry").objects.using(schema_editor.connection.alias)
    replies = apps.get_model("pages", "AdminEmail").objects.using(schema_editor.connection.alias)
    inquiries.filter(
        models.Q(contacted_at__isnull=False)
        | models.Q(status="contacted")
        | models.Q(pk__in=replies.filter(inquiry_id__isnull=False).values("inquiry_id"))
    ).update(contacted_back=True)


class Migration(migrations.Migration):
    dependencies = [("pages", "0007_audiencecontact_marketing_default")]
    operations = [
        migrations.AddField(
            model_name="saleinquiry",
            name="contacted_back",
            field=models.BooleanField(default=False, help_text="Whether we have responded to this enquiry. Set automatically after an admin email reply, or manually for other channels."),
        ),
        migrations.RunPython(backfill_contacted_back, migrations.RunPython.noop),
    ]
