# Generated by Django 3.2.18 on 2023-08-22 09:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('onboarding', '0003_remove_typeassist_code_unique2'),
        ('work_order_management', '0002_auto_20230821_0711'),
    ]

    operations = [
        migrations.AddField(
            model_name='approver',
            name='client',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='approver_clients', to='onboarding.bt'),
        ),
    ]
