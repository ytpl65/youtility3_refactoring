# Generated by Django 3.2.18 on 2023-12-13 03:07

import apps.reports.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_schedulereport'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedulereport',
            name='lastgeneratedon',
            field=models.DateTimeField(default=apps.reports.models.now, verbose_name='Last Generated On'),
        ),
        migrations.AlterField(
            model_name='reporthistory',
            name='datetime',
            field=models.DateTimeField(default=apps.reports.models.now),
        ),
        migrations.AlterField(
            model_name='schedulereport',
            name='cc',
            field=models.TextField(blank=True, verbose_name='CC'),
        ),
        migrations.AlterField(
            model_name='schedulereport',
            name='to_addr',
            field=models.TextField(blank=True, verbose_name='To Address'),
        ),
    ]
