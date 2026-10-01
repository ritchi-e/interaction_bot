import django.db.models.deletion
from django.db import migrations, models

import apps.common.fields


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_alter_user_managers_whatsappcalling_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlivoLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("auth_id", models.CharField(blank=True, max_length=64)),
                ("auth_token", apps.common.fields.EncryptedTextField(blank=True)),
                ("caller_id", models.CharField(blank=True, max_length=20)),
                ("dograh_config_id", models.PositiveIntegerField(blank=True, null=True)),
                ("dograh_phone_number_id", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "organisation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="plivo",
                        to="tenants.organisation",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]
