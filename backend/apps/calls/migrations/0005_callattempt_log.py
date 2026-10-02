from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calls", "0004_alter_callrequest_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="callattempt",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="callattempt",
            name="duration_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="callattempt",
            name="ended_by",
            field=models.CharField(
                blank=True,
                choices=[("agent", "Agent hung up"), ("caller", "Caller hung up")],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="callattempt",
            name="end_reason",
            field=models.CharField(blank=True, max_length=80),
        ),
    ]
