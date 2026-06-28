# Generated manually for Nexo KoBo incremental ingestion.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("coordinacion", "0003_foto"),
    ]

    operations = [
        migrations.CreateModel(
            name="KoboCursor",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "tipo_formulario",
                    models.CharField(
                        choices=[
                            ("necesidad", "Necesidad"),
                            ("donacion", "Donación"),
                        ],
                        max_length=20,
                        unique=True,
                    ),
                ),
                ("asset_uid", models.CharField(blank=True, max_length=120)),
                ("ultimo_submission_time", models.DateTimeField(blank=True, null=True)),
                ("ultimo_uuid", models.CharField(blank=True, max_length=120)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
