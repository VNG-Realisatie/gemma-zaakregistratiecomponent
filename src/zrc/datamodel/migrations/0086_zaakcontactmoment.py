# Generated by Django 2.2.4 on 2019-10-30 09:00

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("datamodel", "0085_merge_20190912_1049"),
    ]

    operations = [
        migrations.CreateModel(
            name="ZaakContactMoment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        help_text="Unieke resource identifier (UUID4)",
                        unique=True,
                    ),
                ),
                (
                    "contactmoment",
                    models.URLField(
                        help_text="URL-referentie naar het CONTACTMOMENT (in de KCC API)",
                        max_length=1000,
                        verbose_name="contactmoment",
                    ),
                ),
                (
                    "_objectcontactmoment",
                    models.URLField(
                        blank=True,
                        help_text="Link to the related object in the KCC API",
                        verbose_name="objectcontactmoment",
                    ),
                ),
                (
                    "zaak",
                    models.ForeignKey(
                        help_text="URL-referentie naar de ZAAK.",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="datamodel.Zaak",
                    ),
                ),
            ],
            options={
                "verbose_name": "contactmoment",
                "verbose_name_plural": "contactmomenten",
                "unique_together": {("zaak", "contactmoment")},
            },
        ),
    ]
