# Generated by Django 3.2.18 on 2023-06-25 13:03

import apps.reports.models
from django.conf import settings
import django.core.serializers.json
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('onboarding', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('datetime', models.DateTimeField(default=apps.reports.models.now)),
                ('export_type', models.CharField(default='DOWNLOAD', max_length=55)),
                ('report_name', models.CharField(max_length=100)),
                ('params', models.JSONField(encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('format', models.CharField(default='pdf', max_length=55)),
                ('ctzoffset', models.IntegerField(default=-1, verbose_name='TimeZone')),
                ('cc_mails', models.TextField(max_length=250, null=True)),
                ('to_mails', models.TextField(max_length=250, null=True)),
                ('email_body', models.TextField(max_length=500, null=True)),
                ('traceback', models.CharField(max_length=1000, null=True)),
                ('bu', models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, to='onboarding.bt')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.RESTRICT, to=settings.AUTH_USER_MODEL, verbose_name='')),
            ],
            options={
                'db_table': 'report_history',
            },
        ),
    ]
