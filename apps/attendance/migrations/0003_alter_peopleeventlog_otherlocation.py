# Generated by Django 3.2.18 on 2023-07-04 09:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='peopleeventlog',
            name='otherlocation',
            field=models.CharField(max_length=50, null=True, verbose_name='Other Location'),
        ),
    ]
