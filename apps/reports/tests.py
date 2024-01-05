
import pytest
from datetime import datetime
from background_tasks.report_tasks import create_scheduled_reports
from apps.reports.models import ScheduleReport
from unittest.mock import patch


def create_records():
    
ScheduleReport.objects.create(
    report_type='TourSummary',
    report_name='Report_3',
    workingdays='6',
    cron='* * * * *',
    report_sendtime=datetime.now().time(),
    cc=[],
    to_addr=[],
    enable=True,
    crontype='monthly',
    fromdatetime=datetime.now() - timedelta(days=2),
    uptodatetime=datetime.now() - timedelta(days=1),
    lastgeneratedon=datetime.now() - timedelta(days=31),
    report_params={},
    bu_id=9,
    client_id=8
)


ScheduleReport.objects.create(
    report_type='ListOfTasks',
    report_name='Report_38',
    workingdays='5',
    cron='* * * * *',
    report_sendtime=datetime.now().time(),
    cc=[],
    to_addr=[],
    enable=True,
    crontype='monthly',
    fromdatetime=datetime.now() - timedelta(days=2),
    uptodatetime=datetime.now() - timedelta(days=1),
    lastgeneratedon=datetime.now() - timedelta(days=31),
    report_params={},
    bu_id=9,
    client_id=8
)


ScheduleReport.objects.create(
    report_type='ListOfTasks',
    report_name='Report_52',
    workingdays='5',
    cron='* * * * *',
    report_sendtime=datetime.now().time(),
    cc=[],
    to_addr=[],
    enable=True,
    crontype='',
    fromdatetime=NULL,
    uptodatetime=NULL,
    lastgeneratedon=NULL,
    report_params={},
    bu_id=9,
    client_id=8
)


ScheduleReport.objects.create(
    report_type='TaskSummary',
    report_name='Report_85',
    workingdays='6',
    cron='* * * * *',
    report_sendtime=datetime.now().time(),
    cc=[],
    to_addr=[],
    enable=True,
    crontype='daily',
    fromdatetime=datetime.now() - timedelta(days=2),
    uptodatetime=datetime.now() - timedelta(days=1),
    lastgeneratedon=datetime.now() - timedelta(days=2),
    report_params={},
    bu_id=9,
    client_id=8
)


ScheduleReport.objects.create(
    report_type='ListOfTasks',
    report_name='Report_100',
    workingdays='6',
    cron='* * * * *',
    report_sendtime=datetime.now().time(),
    cc=[],
    to_addr=[],
    enable=True,
    crontype='weekly',
    fromdatetime=datetime.now() - timedelta(days=2),
    uptodatetime=datetime.now() - timedelta(days=1),
    lastgeneratedon=datetime.now() - timedelta(weeks=2),
    report_params={},
    bu_id=9,
    client_id=9
)


@pytest.mark.django_db
def test_create_scheduled_reports_daily_crontype():
    # Setup: Create a ScheduleReport instance with crontype 'daily'
    # ...

    # Execute
    create_scheduled_reports()

    # Assert: Verify that the report was updated/created as expected
    # ...

@pytest.mark.django_db
def test_create_scheduled_reports_weekly_crontype():
    # Similar setup and assertions for 'weekly' crontype
    # ...

@pytest.mark.django_db
def test_create_scheduled_reports_at_specific_time():
    with patch('myapp.reports.datetime') as mock_datetime:
        # Set mock datetime to a specific time
        mock_datetime.now.return_value = datetime(2023, 12, 15, 8, 0, 0)

        # Execute
        create_scheduled_reports()

        # Assert: Verify the behavior of the function at the mocked time
        # ...

# Additional tests for monthly crontype, error handling, etc.

# Create your tests here.
