import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("calls", "0005_callattempt_log"),
        ("tenants", "0004_providerkeys_default_rumik"),
        ("campaigns", "0005_hinglish_language"),
    ]

    operations = [
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("caller_name", models.CharField(max_length=200)),
                ("appointment_date", models.DateField()),
                ("appointment_time", models.TimeField()),
                ("status", models.CharField(choices=[("booked", "Booked")], default="booked", max_length=16)),
                (
                    "call_request",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="appointments",
                        to="calls.callrequest",
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="appointments",
                        to="campaigns.campaign",
                    ),
                ),
                (
                    "organisation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="appointments",
                        to="tenants.organisation",
                    ),
                ),
            ],
            options={
                "ordering": ["-appointment_date", "-appointment_time"],
            },
        ),
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "booked")),
                fields=("campaign", "appointment_date", "appointment_time"),
                name="one_booked_appointment_slot",
            ),
        ),
    ]
