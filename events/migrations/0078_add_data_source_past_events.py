# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-09-22 09:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0077_place_has_upcoming_events"),
    ]

    operations = [
        migrations.AddField(
            model_name="datasource",
            name="create_past_events",
            field=models.BooleanField(
                default=False, verbose_name="Past events may be created using API"
            ),
        ),
        migrations.AddField(
            model_name="datasource",
            name="edit_past_events",
            field=models.BooleanField(
                default=False, verbose_name="Past events may be edited using API"
            ),
        ),
    ]
