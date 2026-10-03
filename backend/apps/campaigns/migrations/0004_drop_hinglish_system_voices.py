from django.db import migrations, models


def hinglish_to_hi(apps, schema_editor):
    Campaign = apps.get_model("campaigns", "Campaign")
    Campaign.objects.filter(language="hinglish").update(language="hi")
    # Normalise leftover cloud voice ids to female/male.
    Campaign.objects.exclude(tts_voice__in=["female", "male"]).filter(
        tts_voice__in=[
            "abhilash",
            "karun",
            "saurabh",
            "rahul",
            "arjun",
            "vikram",
            "amit",
        ]
    ).update(tts_voice="male")
    Campaign.objects.exclude(tts_voice__in=["female", "male"]).update(tts_voice="female")


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0003_campaign_permission_message"),
    ]

    operations = [
        migrations.RunPython(hinglish_to_hi, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="campaign",
            name="language",
            field=models.CharField(
                choices=[("hi", "Hindi"), ("en_in", "Indian English")],
                default="hi",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="campaign",
            name="tts_voice",
            field=models.CharField(
                blank=True,
                choices=[("female", "Female"), ("male", "Male")],
                default="female",
                max_length=80,
            ),
        ),
    ]
