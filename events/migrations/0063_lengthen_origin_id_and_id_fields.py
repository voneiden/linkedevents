# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-10-01 07:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0062_add_super_event_type_index_for_filtering"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="id",
            field=models.CharField(max_length=100, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="event",
            name="origin_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=100,
                null=True,
                verbose_name="Origin ID",
            ),
        ),
        migrations.AlterField(
            model_name="keyword",
            name="id",
            field=models.CharField(max_length=100, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="keyword",
            name="origin_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=100,
                null=True,
                verbose_name="Origin ID",
            ),
        ),
        migrations.AlterField(
            model_name="keywordset",
            name="id",
            field=models.CharField(max_length=100, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="keywordset",
            name="origin_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=100,
                null=True,
                verbose_name="Origin ID",
            ),
        ),
        migrations.AlterField(
            model_name="place",
            name="id",
            field=models.CharField(max_length=100, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="place",
            name="origin_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=100,
                null=True,
                verbose_name="Origin ID",
            ),
        ),
    ]
