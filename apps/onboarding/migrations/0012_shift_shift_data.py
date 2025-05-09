# Generated by Django 3.2.18 on 2024-08-20 06:34

import apps.onboarding.models
import django.core.serializers.json
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('onboarding', '0011_alter_bt_cuser_alter_bt_muser_alter_device_cuser_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='shift',
            name='shift_data',
            field=models.JSONField(blank=True, default=apps.onboarding.models.shiftdata_json, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True),
        ),
    ]
