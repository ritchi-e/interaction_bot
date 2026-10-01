from django.db import migrations, models


def use_rumik(apps, schema_editor):
    ProviderKeys = apps.get_model("tenants", "ProviderKeys")
    ProviderKeys.objects.filter(tts_provider="sarvam").update(tts_provider="rumik")


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0003_plivoline"),
    ]

    operations = [
        migrations.RunPython(use_rumik, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="providerkeys",
            name="tts_provider",
            field=models.CharField(
                choices=[
                    ("sarvam", "Sarvam Bulbul"),
                    ("rumik", "Rumik"),
                    ("cartesia", "Cartesia"),
                    ("elevenlabs", "ElevenLabs"),
                ],
                default="rumik",
                max_length=32,
            ),
        ),
    ]
