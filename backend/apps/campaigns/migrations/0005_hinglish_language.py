from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("campaigns", "0004_drop_hinglish_system_voices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campaign",
            name="language",
            field=models.CharField(
                choices=[("hi", "Hindi"), ("hinglish", "Hinglish"), ("en_in", "Indian English")],
                default="hi",
                max_length=16,
            ),
        ),
    ]
