"""Free tier: one full test and one timed test per section, for every exam.

Lowers any stored override above one. Paid and institution users are not limited.
"""
from django.db import migrations


def cap_free_attempts(apps, schema_editor):
    TestConfiguration = apps.get_model("assessments", "TestConfiguration")
    FreeTierModuleLimit = apps.get_model("assessments", "FreeTierModuleLimit")
    TestConfiguration.objects.filter(free_full_test_attempts__gt=1).update(free_full_test_attempts=1)
    TestConfiguration.objects.filter(free_module_test_attempts__gt=1).update(free_module_test_attempts=1)
    FreeTierModuleLimit.objects.filter(test_attempt_limit__gt=1).update(test_attempt_limit=1)


class Migration(migrations.Migration):
    dependencies = [("assessments", "0024_gia_german_spanish")]
    operations = [migrations.RunPython(cap_free_attempts, migrations.RunPython.noop)]
