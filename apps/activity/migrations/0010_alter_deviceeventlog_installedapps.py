# Generated by Django 3.2.18 on 2023-09-30 07:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0009_alter_asset_assetcode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deviceeventlog',
            name='installedapps',
            field=models.TextField(default='NA', verbose_name='Installed Apps'),
        ),
    ]
