'''
This file contains functions related to executing
reports in background
'''
from apps.reports.utils import ReportEssentials
from apps.reports.models import ScheduleReport
from django.db.models import Q, F
from apps.core.utils import runrawsql
from django.conf import settings
from croniter import croniter
from datetime import datetime , timedelta, timezone
from django.utils import timezone as dtimezone
from logging import getLogger
from pprint import pformat
import json
from celery import shared_task
import traceback as tb
import os

# make it false when u deploy
MOCK=True
now = datetime.now() if not MOCK else datetime(2023,12,11,17,2,0)

log = getLogger('reports')
DATETIME_FORMAT = '%d-%b-%Y %H-%M-%S'
DATE_FORMAT = '%d-%b-%Y'
TIME_FORMAT = "%H-%M-%S"


def get_scheduled_reports_fromdb():
    query ='''
        SELECT *
        FROM schedule_report
        WHERE enable = TRUE AND
        (fromdatetime is NULL and uptodatetime is NULL)
        OR
        (
            (
                (crontype = 'daily' AND lastgeneratedon <= uptodatetime - INTERVAL '1 day')
                OR (crontype = 'weekly' AND lastgeneratedon <= uptodatetime - INTERVAL '1 week')
                OR (crontype = 'monthly' AND lastgeneratedon <= uptodatetime - INTERVAL '1 month')
            )
            AND fromdatetime <= CURRENT_TIMESTAMP
            AND uptodatetime <= CURRENT_TIMESTAMP
        )
    '''
    return runrawsql(query)


def remove_star(li):
    return [item.replace('*', "") for item in li]


def update_record(data, fromdatetime, uptodatetime, lastgeneratedon):
    ScheduleReport.objects.filter(
        pk = data['id']
    ).update(
        fromdatetime=fromdatetime,
        uptodatetime=uptodatetime,
        lastgeneratedon=lastgeneratedon
    )


def calculate_from_and_upto(data, firsttime=False):
    days_crontype_map = {'weekly':7, 'monthly':31, 'daily':1, 'workingdays':data['workingdays']}
    if firsttime:
        log.info("The report is generating for the first time")
        basedatetime = now - timedelta(days=days_crontype_map[data['crontype']]+1)
        log.info(f'{basedatetime = } {data["cron"] = }')
        cron = croniter(data['cron'], basedatetime)
        tz = timezone(timedelta(minutes = data['ctzoffset']))
        fromdatetime = cron.get_prev(datetime)
        log.info(f'{fromdatetime = } {type(fromdatetime)}')
        fromdatetime = fromdatetime.replace(tzinfo=tz, microsecond=0)
        uptodatetime = cron.get_next(datetime)
        uptodatetime = uptodatetime.replace(tzinfo=tz, microsecond=0)
        lastgeneratedon = now
        #create the record
        update_record(data, fromdatetime, uptodatetime, lastgeneratedon)
    else:
        basedatetime = data['lastgeneratedon'] - timedelta(days=days_crontype_map[data['crontype']]+1)
        cron = croniter(data['cron'], basedatetime)
        fromdatetime = cron.get_prev(datetime)
        fromdatetime = fromdatetime.replace(tzinfo=tz, microsecond=0)
        uptodatetime = cron.get_next(datetime)
        uptodatetime = uptodatetime.replace(tzinfo=tz, microsecond=0)
        lastgeneratedon = now
        current_time = now - timedelta(days=1)
        if current_time.date() == lastgeneratedon.date():
            #update the record
            update_record(data, fromdatetime, uptodatetime, lastgeneratedon)
    return fromdatetime, uptodatetime
            


def get_fromdate_uptodate(data):
    if data['fromdatetime'] is None and data['uptodatetime'] is None:
        #report is generating for the first time
        fromdatetime, uptodatetime = calculate_from_and_upto(data, firsttime=True)
    else: 
        fromdatetime, uptodatetime = calculate_from_and_upto(data, firsttime=False)
    return fromdatetime, uptodatetime


def build_form_data(data, report_params, behaviour):
    date_range = None
    fields = remove_star(behaviour['fields'])
    fromdatetime, uptodatetime = get_fromdate_uptodate(data)
    formdata = {
        'preview':False,
        'format':report_params['format'],
        'ctzoffset':data['ctzoffset'],
    }
    if 'fromdate' in fields:
        formdata.update({'fromdate':fromdatetime.date(), 'uptodate':uptodatetime.date()})
        date_range = f"{formdata['fromdate'].strftime(DATE_FORMAT)}--{formdata['uptodate'].strftime(DATE_FORMAT)}"
    if 'fromdatetime' in fields:
        formdata.update({'fromdatetime':fromdatetime, 'uptodatetime':uptodatetime.date()})
        date_range = f"{formdata['fromdatetime'].strftime(DATETIME_FORMAT)}--{formdata['uptodatetime'].strftime(DATETIME_FORMAT)}"
    log.debug(f'formdata = {pformat(formdata)}, fields = {fields}')
    required_params = {key: report_params[key] for key in fields if key not in formdata}
    formdata.update(required_params)
    return formdata, date_range
    
    
def generate_filename(report_type, date_range, sendtime):
    #eg: filename = TaskSummary__2023-DEC-1--2023-DEC-30__23-34-23.pdf
    return f"{report_type}__{date_range}__{sendtime.strftime(TIME_FORMAT)}" 


def execute_report(RE, report_type, client_id, formdata):
    report_export = RE(
            filename=report_type,
            client_id=client_id,
            returnfile=True,
            formdata=formdata)
    return report_export.execute()


def save_report_to_tmp_folder(filename, ext, report_output):
    if report_output:
        directory = settings.TEMP_REPORTS_GENERATED
        filepath = os.path.join(directory, f"{filename}.{ext}")
        # Check if the directory exists, if not, create it
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(filepath, 'wb') as f:
            f.write(report_output)
        return filepath
    else:
        pass

def generate_scheduled_report(record):
    """
    Generate a scheduled report based on the provided data.

    Args:
        data (dict): A dictionary containing information about the scheduled report.

    Returns:
        None: This method generates and saves the report but does not return any value.

    Raises:
        Any relevant exceptions: Document any exceptions that may be raised during report generation.
    """
    resp = dict()
    if record:
        report_params = json.loads(record['report_params'])
        re = ReportEssentials(record['report_type'])
        behaviour = re.behaviour_json
        RE = re.get_report_export_object()
        log.info(f"Got RE of type {type(RE)}")
        formdata, date_range = build_form_data(record, report_params, behaviour)
        log.info(f"formdata: {pformat(formdata)} {date_range = }")
        report_output = execute_report(RE, record['report_type'], record['client_id'], formdata)
        sendtime = record['report_sendtime']
        report_type = record['report_type']
        filename = generate_filename(report_type, date_range, sendtime)
        log.info(f"filename generated {filename = }")
        ext = report_params['format']
        log.info(f"file extension {ext = }")
        filepath = save_report_to_tmp_folder(filename, ext, report_output)
        log.info(f"file saved at location {filepath =}")
        resp[str(record['id'])] = filepath
    else:
        resp['msg'] = 'No reports are currently due for being generated'
         
         

@shared_task(name='create_reports_bg')
def create_scheduled_reports():
    resp = dict()
    try:
        data = get_scheduled_reports_fromdb()
        log.info(f"Found {len(data)} for reports for generation in background")
        if data:
            for record in data:
                generate_scheduled_report(record)
        resp['msg'] = f'Total {len(data)} reports generated at {timezone.now()}'
    except Exception as e:
        resp['traceback'] = tb.format_exc()
        log.critical("Error while creating report:", exc_info=True)
    return resp