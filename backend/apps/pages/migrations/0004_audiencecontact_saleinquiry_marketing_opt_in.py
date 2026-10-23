from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_audience_contacts(apps, schema_editor):
    AudienceContact = apps.get_model("pages", "AudienceContact")
    SaleInquiry = apps.get_model("pages", "SaleInquiry")
    TestSuggestion = apps.get_model("pages", "TestSuggestion")
    User = apps.get_model("accounts", "User")

    for user in User.objects.all().iterator():
        AudienceContact.objects.get_or_create(
            email=user.email.strip().lower(),
            defaults={
                "tenant_id": user.tenant_id,
                "user_id": user.id,
                "full_name": " ".join(part for part in (user.first_name, user.last_name) if part),
                "source": "user_account",
                "marketing_opt_in": False,
            },
        )
    for inquiry in SaleInquiry.objects.all().iterator():
        AudienceContact.objects.get_or_create(
            email=inquiry.email.strip().lower(),
            defaults={
                "tenant_id": inquiry.tenant_id,
                "full_name": inquiry.full_name,
                "source": "sales_inquiry",
                "marketing_opt_in": False,
            },
        )
    for suggestion in TestSuggestion.objects.all().iterator():
        AudienceContact.objects.get_or_create(
            email=suggestion.email.strip().lower(),
            defaults={
                "tenant_id": suggestion.tenant_id,
                "user_id": suggestion.user_id,
                "source": "test_suggestion",
                "marketing_opt_in": False,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0003_testsuggestion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="saleinquiry",
            name="marketing_opt_in",
            field=models.BooleanField(
                default=False,
                help_text="The contact has agreed to receive MindMetric product updates and offers.",
            ),
        ),
        migrations.CreateModel(
            name="AudienceContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("full_name", models.CharField(blank=True, max_length=255)),
                ("source", models.CharField(choices=[("user_account", "User account"), ("sales_inquiry", "Sales inquiry"), ("test_suggestion", "Test suggestion"), ("admin", "Added by admin")], default="admin", max_length=32)),
                ("marketing_opt_in", models.BooleanField(default=False)),
                ("unsubscribed_at", models.DateTimeField(blank=True, null=True)),
                ("last_campaign_sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audience_contacts", to="tenants.tenant")),
                ("user", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audience_contact", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-updated_at",)},
        ),
        migrations.RunPython(backfill_audience_contacts, migrations.RunPython.noop),
    ]
