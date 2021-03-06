# Generated by Django 2.0.6 on 2018-06-12 08:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("datamodel", "0010_klantcontact_zaak")]

    operations = [
        migrations.CreateModel(
            name="ZaakInformatieObject",
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
                    "informatieobject",
                    models.URLField(
                        help_text="URL naar het INFORMATIEOBJECT in het DRC."
                    ),
                ),
                (
                    "zaak",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="datamodel.Zaak"
                    ),
                ),
            ],
            options={
                "verbose_name": "Zaakinformatieobject",
                "verbose_name_plural": "Zaakinformatieobjecten",
            },
        )
    ]
