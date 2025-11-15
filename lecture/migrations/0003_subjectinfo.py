from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lecture", "0002_alter_session_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubjectInfo",
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
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField()),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Subject info",
                "verbose_name_plural": "Subject infos",
            },
        ),
    ]


