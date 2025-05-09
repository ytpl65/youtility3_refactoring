# Generated by Django 3.2.18 on 2023-12-07 07:09

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0010_alter_deviceeventlog_installedapps'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attachment',
            name='gpslocation',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, geography=True, null=True, srid=4326, verbose_name='GPS Location'),
        ),
        migrations.AlterField(
            model_name='deviceeventlog',
            name='gpslocation',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, geography=True, null=True, srid=4326),
        ),
        migrations.AlterField(
            model_name='jobneed',
            name='gpslocation',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, geography=True, null=True, srid=4326, verbose_name='GPS Location'),
        ),
    ]
