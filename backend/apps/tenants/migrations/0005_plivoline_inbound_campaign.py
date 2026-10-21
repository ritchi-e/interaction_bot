from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0004_providerkeys_default_rumik"),
    ]

    operations = [
        migrations.AddField(
            model_name="plivoline",
            name="inbound_campaign_id",
            field=models.UUIDField(blank=True, null=True),
        ),
    ]
