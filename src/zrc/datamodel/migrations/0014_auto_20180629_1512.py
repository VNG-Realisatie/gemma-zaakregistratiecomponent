# Generated by Django 2.0.6 on 2018-06-29 15:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("datamodel", "0013_organisatorischeeenheid_rol")]

    operations = [
        migrations.RemoveField(model_name="zaakinformatieobject", name="zaak"),
        migrations.DeleteModel(name="ZaakInformatieObject"),
    ]
