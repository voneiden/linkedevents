# -*- coding: utf-8 -*-
# Generated by Django 1.9.11 on 2016-12-13 17:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0033_add_data_source_to_image"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="event",
            managers=[],
        ),
        migrations.AddField(
            model_name="keyword",
            name="deprecated",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
