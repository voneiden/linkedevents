# Generated by Django 2.2.11 on 2020-07-02 09:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0075_add_trigram_extension"),
    ]

    operations = [
        migrations.AddField(
            model_name="keyword",
            name="has_upcoming_events",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
