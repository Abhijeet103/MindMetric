from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0008_saleinquiry_contacted_back"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenants", "0007_tenantenrollmentcode_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="PortalFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("category", models.CharField(choices=[("general", "General feedback"), ("question", "Question"), ("issue", "Report a problem"), ("suggestion", "Suggestion")], default="general", max_length=16)),
                ("message", models.TextField()),
                ("source_page", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("new", "New"), ("reviewed", "Reviewed")], default="new", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="portal_feedback", to="tenants.tenant")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="portal_feedback", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "portal feedback",
                "verbose_name_plural": "portal feedback",
                "ordering": ("-created_at",),
            },
        ),
    ]
