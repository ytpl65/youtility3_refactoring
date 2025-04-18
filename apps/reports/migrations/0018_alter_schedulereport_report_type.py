# Generated by Django 4.2 on 2024-06-25 09:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0017_alter_schedulereport_cuser_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedulereport',
            name='report_type',
            field=models.CharField(choices=[('', 'Select Report'), ('TASKSUMMARY', 'Task Summary'), ('TOURSUMMARY', 'Tour Summary'), ('LISTOFTASKS', 'List of Tasks'), ('LISTOFTOURS', 'List of Internal Tours'), ('PPMSUMMARY', 'PPM Summary'), ('LISTOFTICKETS', 'List of Tickets'), ('WORKORDERLIST', 'Work Order List'), ('SITEVISITREPORT', 'Site Visit Report'), ('SITEREPORT', 'Site Report'), ('PeopleQR', 'People-QR'), ('ASSETQR', 'Asset-QR'), ('CHECKPOINTQR', 'Checkpoint-QR'), ('ASSETWISETASKSTATUS', 'Assetwise Task Status'), ('DetailedTourSummary', 'Detailed Tour Summary'), ('STATICDETAILEDTOURSUMMARY', 'Static Detailed Tour Summary'), ('DYNAMICDETAILEDTOURSUMMARY', 'Dynamic Detailed Tour Summary'), ('DYNAMICTOURDETAILS', 'Dynamic Tour Details'), ('STATICTOURDETAILS', 'Static Tour Details'), ('RP_SITEVISITREPORT', 'RP Site Visit Report'), ('LOGSHEET', 'Log Sheet')], max_length=50, verbose_name='Report Type'),
        ),
    ]
