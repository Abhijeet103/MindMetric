from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pages", "0006_adminemail")]
    operations = [
        migrations.AlterField(
            model_name="audiencecontact",
            name="marketing_opt_in",
            field=models.BooleanField(default=True),
        ),
    ]
