# -*- coding: utf-8 -*-
# Generated by Django 1.9.11 on 2017-01-02 16:44
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from modeltranslation.manager import MultilingualManager


def forward(apps, schema_editor):
    Place = apps.get_model("events", "Place")
    for place in Place.objects.exclude(events=None):
        n_events = place.events.all().count()
        if n_events != place.n_events:
            place.n_events = n_events
            place.save(update_fields=("n_events",))


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0035_add_n_events_to_keyword"),
    ]

    operations = [
        migrations.AddField(
            model_name="place",
            name="n_events",
            field=models.IntegerField(
                db_index=True,
                default=0,
                editable=False,
                help_text="number of events in this location",
                verbose_name="event count",
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="location",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="events",
                to="events.Place",
            ),
        ),
        # the following row needed for forward data migration, due to bug #489 in django-mptt
        migrations.AlterModelManagers(
            name="place",
            managers=[],
        ),
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
