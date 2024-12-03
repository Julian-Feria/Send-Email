# Generated by Django 5.0.7 on 2024-12-03 16:03

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('credentials', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='credentials',
            name='emails_sent_today',
            field=models.IntegerField(default=0, verbose_name='Correos enviados hoy'),
        ),
        migrations.AddField(
            model_name='credentials',
            name='last_reset',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
