# Generated by Django 2.2.13 on 2021-12-01 06:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0007_signup_attendee_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="signup",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True, verbose_name="Date of birth"),
        ),
    ]
