# Generated by Django 3.2.18 on 2023-09-29 11:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity', '0008_alter_location_loccode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='assetcode',
            field=models.CharField(max_length=50, verbose_name='Asset Code'),
        ),
    ]
