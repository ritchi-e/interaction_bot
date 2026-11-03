import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("calls", "0005_callattempt_log"),
        ("tenants", "0004_providerkeys_default_rumik"),
        ("campaigns", "0006_appointment"),
    ]

    operations = [
        migrations.CreateModel(
            name="LocumInterest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("phone_e164", models.CharField(max_length=20)),
                ("doctor_name", models.CharField(blank=True, max_length=200)),
                ("job_id", models.CharField(blank=True, max_length=120)),
                ("job_title", models.CharField(blank=True, max_length=300)),
                ("job_location", models.CharField(blank=True, max_length=300)),
                ("job_specialty", models.CharField(blank=True, max_length=200)),
                ("job_duration", models.CharField(blank=True, max_length=120)),
                ("job_facility", models.CharField(blank=True, max_length=300)),
                ("job_details", models.JSONField(blank=True, default=dict)),
                ("source_payload", models.JSONField(blank=True, default=dict)),
                (
                    "interested",
                    models.CharField(
                        choices=[("unknown", "Unknown"), ("yes", "Interested"), ("no", "Not interested")],
                        default="unknown",
                        max_length=16,
                    ),
                ),
                (
                    "call_request",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="locum_interests",
                        to="calls.callrequest",
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="locum_interests",
                        to="campaigns.campaign",
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="locum_interests",
                        to="tenants.organisation",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
