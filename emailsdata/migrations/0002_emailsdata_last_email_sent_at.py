# Generated by Django 5.0.7 on 2024-12-09 14:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emailsdata', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailsdata',
            name='last_email_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Última fecha de envío'),
        ),
    ]
