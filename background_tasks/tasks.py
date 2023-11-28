from intelliwiz_config.celery import app
from celery import shared_task
from background_tasks import utils as butils
from apps.core import utils
from django.apps import apps
from logging import getLogger
from django.db import transaction
from datetime import timedelta
import traceback as tb
from apps.core.raw_queries import get_query
from pprint import pformat
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
import requests
import base64
from django.core.mail import EmailMessage
from django.templatetags.static import static
from io import BytesIO


log = getLogger('mobile_service_log')


@app.task(bind=True, default_retry_delay=300, max_retries=5, name='Send Ticket email')
def send_ticket_email(self, ticket=None, id=None):
    from apps.y_helpdesk.models import Ticket
    from django.conf import settings
    from django.template.loader import render_to_string
    try:
        if not ticket and id:
            ticket = Ticket.objects.get(id=id)
        if ticket:
            log.info(f"ticket found with ticket id: {ticket.ticketno}")
            log.info("ticket email sending start ")
            resp = {}
            emails = butils.get_email_recipents_for_ticket(ticket)
            log.info(f"email addresses of recipents: {emails}")
            updated_or_created = "Created" if ticket.cdtz == ticket.mdtz else "Updated"
            context = {
                'subject': f"Ticket with #{ticket.ticketno} is {updated_or_created} at site: {ticket.bu.buname}",
                'desc': ticket.ticketdesc,
                'template': ticket.ticketcategory.taname,
                'status': ticket.status,
                'createdon': ticket.cdtz.strftime("%Y-%m-%d %H:%M:%S"),
                'modifiedon': ticket.mdtz.strftime("%Y-%m-%d %H:%M:%S"),
                'modifiedby': ticket.muser.peoplename,
                'assignedto': ticket.assignedtogroup.groupname if ticket.assignedtopeople_id in [None, 1] else ticket.assignedtopeople.peoplename,
                'comments': ticket.comments,
                "priority": ticket.priority,
                'level': ticket.level
            }
            log.info(f'context for email template: {context}')
            html_message = render_to_string('y_helpdesk/ticket_email.html', context)
            msg = EmailMessage()
            msg.body = html_message
            msg.to = emails
            msg.subject = context['subject']
            msg.from_email = settings.EMAIL_HOST_USER
            msg.content_subtype = 'html'
            msg.send()
            log.info("ticket email sent")
        else:
            log.info('ticket not found no emails will send')
    except Exception as e:
        log.critical("Error while sending ticket email", exc_info=True)
        resp['traceback'] = tb.format_exc()
    return resp


@shared_task(name="auto_close_jobs")
def autoclose_job(jobneedid=None):
    from django.template.loader import render_to_string
    from django.conf import settings
    try:
        # get all expired jobs
        Jobneed = apps.get_model('activity', 'Jobneed')
        resp = {'story': "", 'traceback': "", 'id': []}
        expired = Jobneed.objects.get_expired_jobs(id=jobneedid)
        resp['story'] += f'total expired jobs = {len(expired)}\n'
        context = {}
        with transaction.atomic(using=utils.get_current_db_name()):
            resp['story'] += f"using database: {utils.get_current_db_name()}\n"
            for rec in expired:
                resp['story'] += f"processing record with id= {rec['id']}\n"
                resp['story'] += f"record category is {rec['ticketcategory__tacode']}\n"

                if rec['ticketcategory__tacode'] in ['AUTOCLOSENOTIFY', 'RAISETICKETNOTIFY']:

                    log.info("notifying through email...")
                    pdate = rec["plandatetime"] + \
                        timedelta(minutes=rec['ctzoffset'])
                    pdate = pdate.strftime("%d-%b-%Y %H:%M")
                    edate = rec["expirydatetime"] + \
                        timedelta(minutes=rec['ctzoffset'])
                    edate = edate.strftime("%d-%b-%Y %H:%M")

                    subject = f'AUTOCLOSE {"TOUR" if rec["identifier"] in  ["INTERNALTOUR", "EXTERNALTOUR"] else rec["identifier"] } planned on \
                    {pdate} not reported in time'
                    context = {
                        'subject': subject,
                        'buname': rec['bu__buname'],
                        'plan_dt': pdate,
                        'creatorname': rec['cuser__peoplename'],
                        'assignedto': rec['assignedto'],
                        'exp_dt': edate,
                        'show_ticket_body': False,
                        'identifier': rec['identifier'],
                        'jobdesc': rec['jobdesc']
                    }

                    emails = utils.get_email_addresses([rec['people_id'], rec['cuser_id'], rec['muser_id']], [
                                                       rec['pgroup_id']], [rec['bu_id']])
                    resp['story'] += f"email recipents are as follows {emails}\n"
                    log.info(f"recipents are as follows...{emails}")
                    msg = EmailMessage()
                    msg.subject = subject
                    msg.from_email = settings.EMAIL_HOST_USER
                    msg.to = emails
                    msg.content_subtype = 'html'

                    if rec['ticketcategory__tacode'] == 'RAISETICKETNOTIFY':
                        log.info("ticket needs to be generated")
                        context['show_ticket_body'] = True
                        jobdesc = f'AUTOCLOSED {"TOUR" if rec["identifier"] in  ["INTERNALTOUR", "EXTERNALTOUR"] else rec["identifier"] } planned on {pdate} not reported in time'
                        # DB OPERATION
                        ticket_data = butils.create_ticket_for_autoclose(
                            rec, jobdesc)
                        log.info(f'{ticket_data}')
                        if esc := butils.get_escalation_of_ticket(ticket_data) and esc['frequencyvalue'] and esc['frequency']:
                            context['escalation'] = True
                            context['next_escalation'] = f"{esc['frequencyvalue']} {esc['frequency']}"
                        created_at = ticket_data['cdtz'] + \
                            timedelta(minutes=ticket_data['ctzoffset'])
                        created_at = created_at.strftime("%d-%b-%Y %H:%M")

                        context['ticketno'] = ticket_data['ticketno']
                        context['tjobdesc'] = jobdesc
                        context['categoryname'] = rec['ticketcategory__taname']
                        context['priority'] = rec['priority']
                        context['status'] = 'NEW'
                        context['tcreatedby'] = rec['cuser__peoplename']
                        context['created_at'] = created_at
                        context['tkt_assignedto'] = rec['assignedto']

                    html_message = render_to_string(
                        'activity/autoclose_mail.html', context=context)
                    resp['story'] += f"context in email template is {context}\n"
                    msg.body = html_message
                    msg.send()
                    log.info(f"mail sent, record_id:{rec['id']}")
                resp = butils.update_job_autoclose_status(rec, resp)

    except Exception as e:
        log.critical(f'context in the template:{context}', exc_info=True)
        log.error(
            "something went wrong while running autoclose_job()", exc_info=True)
        resp['traceback'] += f"{tb.format_exc()}"
    return resp


@shared_task(name="ticket_escalation")
def ticket_escalation():
    result = {'story': "", 'traceback': "", 'id': []}
    try:
        # get all records of tickets which can be escalated
        tickets = utils.runrawsql(get_query('get_ticketlist_for_escalation'))
        result['story'] = f"Total tickets found for escalation are {len(tickets)}\n"
        # update ticket_history, assignments to people & groups, level, mdtz, modifiedon
        result = butils.update_ticket_data(tickets, result)
    except Exception as e:
        log.critical("somwthing went wrong while ticket escalation", exc_info=True)
        result['traceback'] = tb.format_exc()
    return result


@shared_task(name="send_reminder_emails")
def send_reminder_email():
    from django.template.loader import render_to_string
    from django.conf import settings
    from apps.reminder.models import Reminder

    resp = {'story': "", "traceback": "", 'id': []}
    # get all reminders which are not sent
    reminders = Reminder.objects.get_all_due_reminders()
    resp['story'] += f"total due reminders are: {len(reminders)}\n"
    log.info(f"total due reminders are {len(reminders)}")
    try:
        for rem in reminders:
            resp['story'] += f"processing reminder with id: {rem['id']}"
            emails = utils.get_email_addresses(
                [rem['people_id'], rem['cuser_id'], rem['muser_id']], [rem['group_id']])
            resp['story'] += f"emails recipents are as follows {emails}\n"
            recipents = list(set(emails + rem['mailids'].split(',')))
            subject = f"Reminder For {rem['job__jobname']}"
            context = {'job': rem['job__jobname'], 'plandatetime': rem['pdate'], 'jobdesc': rem['job__jobdesc'], 'sitename': rem['bu__buname'],
                       'creator': rem['cuser__peoplename'], 'modifier': rem['muser__peoplename'], 'subject': subject}
            html_message = render_to_string(
                'activity/reminder_mail.html', context=context)
            resp['story'] += f"context in email template is {context}\n"
            log.info(f"Sending reminder mail with subject {subject}")

            msg = EmailMessage()
            msg.subject = subject
            msg.body = html_message
            msg.from_email = settings.EMAIL_HOST_USER
            msg.to = recipents
            msg.content_subtype = 'html'
            # returns 1 if mail sent successfully else 0
            if is_mail_sent := msg.send(fail_silently=True):
                Reminder.objects.filter(id=rem['id']).update(
                    status="SUCCESS", mdtz=timezone.now())
            else:
                Reminder.objects.filter(id=rem['id']).update(
                    status="FAILED", mdtz=timezone.now())
            resp['id'].append(rem['id'])
            log.info(
                f"Reminder mail sent to {recipents} with subject {subject}")
    except Exception as e:
        log.critical("Error while sending reminder email", exc_info=True)
        resp['traceback'] = tb.format_exc()
    return resp


@shared_task(name="schedule_ppm_jobs")
def create_ppm_job(jobid=None):
    F, d = {}, []
    #resp = {'story':"", 'traceback':""}
    startdtz = enddtz = msg = resp = None
    from apps.activity.models import Job, Asset
    from apps.schedhuler.utils import (calculate_startdtz_enddtz_for_ppm, get_datetime_list,
                                       insert_into_jn_and_jnd, get_readable_dates, create_ppm_reminder)
    result = {'story': "", "traceback": "", 'id': []}

    try:
        # atomic transaction
        with transaction.atomic(using=utils.get_current_db_name()):
            if jobid:
                jobs = Job.objects.filter(id=jobid).values(
                    *utils.JobFields.fields)
            else:
                jobs = Job.objects.filter(
                    ~Q(jobname='NONE'),
                    ~Q(asset__runningstatus=Asset.RunningStatus.SCRAPPED),
                    identifier=Job.Identifier.PPM.value,
                    parent_id=1
                ).select_related('asset', 'pgroup', 'cuser', 'muser', 'people', 'qset').values(
                    *utils.JobFields.fields
                )

            if not jobs:
                msg = "No jobs found schedhuling terminated"
                result['story'] += f"{msg}\n"
                log.warning(f"{msg}", exc_info=True)
            total_jobs = len(jobs)

            if total_jobs > 0 and jobs is not None:
                log.info("processing jobs started found:= '%s' jobs", (len(jobs)))
                result['story'] += f"total jobs found {total_jobs}\n"
                for job in jobs:
                    result['story'] += f'\nprocessing job with id: {job["id"]}'
                    startdtz, enddtz = calculate_startdtz_enddtz_for_ppm(job)
                    log.debug(
                        f"Jobs to be schedhuled from startdatetime {startdtz} to enddatetime {enddtz}")
                    DT, is_cron, resp = get_datetime_list(
                        job['cron'], startdtz, enddtz, resp)
                    if not DT:
                        resp = {
                            'msg': "Please check your Valid From and Valid To dates"}
                        continue
                    log.debug(
                        "Jobneed will going to create for all this datetimes\n %s", (pformat(get_readable_dates(DT))))
                    if not is_cron:
                        F[str(job['id'])] = {'cron': job['cron']}
                    status, resp = insert_into_jn_and_jnd(job, DT, resp)
                    if status:
                        d.append({
                            "job": job['id'],
                            "jobname": job['jobname'],
                            "cron": job['cron'],
                            "iscron": is_cron,
                            "count": len(DT),
                            "status": status
                        })
                create_ppm_reminder(d)
                if F:
                    result['story'] += f'create_ppm_job failed job schedule list {pformat(F)}\n'
                    log.info(
                        f"create_ppm_job Failed job schedule list:={pformat(F)}")
                    for key, value in list(F.items()):
                        log.info(
                            f"create_ppm_job job_id: {key} | cron: {value}")
    except Exception as e:
        log.critical("something went wrong create_ppm_job", exc_info=True)
        F[str(job['id'])] = {'tb': tb.format_exc()}

    return resp, F, d, result


@app.task(bind=True, default_retry_delay=300, max_retries=5, name='Face recognition')
def perform_facerecognition_bgt(self, pel_uuid, peopleid, db='default'):
    # sourcery skip: remove-redundant-except-handler
    result = {'story': "perform_facerecognition_bgt()\n", "traceback": ""}
    result['story'] += f"inputs are {pel_uuid = } {peopleid = }, {db = }\n"
    try:
        log.info("perform_facerecognition ...start [+]")
        with transaction.atomic(using=utils.get_current_db_name()):
            utils.set_db_for_router(db)
            if pel_uuid not in [None, 'NONE', '', 1] and peopleid not in [None, 'NONE', 1, ""]:
                Attachment = apps.get_model('activity', 'Attachment')
                pel_att = Attachment.objects.get_people_pic(
                    pel_uuid, db)  # people event pic
                # people default profile pic
                People = apps.get_model('peoples', 'People')
                people_obj = People.objects.get(id=peopleid)
                default_peopleimg = f'{settings.MEDIA_ROOT}/{people_obj.peopleimg.url.replace("/youtility4_media/", "")}'
                default_peopleimg = static('assets/media/images/blank.png') if default_peopleimg.endswith('blank.png') else default_peopleimg  
                if default_peopleimg and pel_att.people_event_pic:
                    images_info = f"default image path:{default_peopleimg} and uploaded file path:{pel_att.people_event_pic}"
                    log.info(f'{images_info}')
                    result['story'] += f'{images_info}\n'
                    from deepface import DeepFace
                    fr_results = DeepFace.verify(
                        img1_path=default_peopleimg, img2_path=pel_att.people_event_pic, enforce_detection=True, detector_backend='ssd')
                    log.info(
                        f"deepface verification completed and results are {fr_results}")
                    result[
                        'story'] += f"deepface verification completed and results are {fr_results}\n"
                    PeopleEventlog = apps.get_model(
                        'attendance', 'PeopleEventlog')
                    if PeopleEventlog.objects.update_fr_results(fr_results, pel_uuid, peopleid, db):
                        log.info(
                            "updation of fr_results in peopleeventlog is completed...")
    except ValueError as v:
        log.error(
            "face recogntion image not found or face is not there...", exc_info=True)
        result['traceback'] += f'{tb.format_exc()}'
    except Exception as e:
        log.critical(
            "something went wrong! while performing face-recogntion in background", exc_info=True)
        result['traceback'] += f'{tb.format_exc()}'
        self.retry(e)
        raise
    return result


@app.task(bind=True, default_retry_delay=300, max_retries=5, name="alert_sendmail()")
def alert_sendmail(self, id, event, atts=False):
    '''
    takes uuid, ownername (which is the model name) and event (observation or deviation)
    gets the record from model if record has alerts set to true then send mail based on event
    '''
    Jobneed = apps.get_model('activity', 'Jobneed')
    from .utils import alert_deviation, alert_observation
    obj = Jobneed.objects.filter(id=id).first()
    if event == 'observation' and obj:
        return alert_observation(obj, atts)
    if event == 'deviation' and obj:
        return alert_deviation(obj, atts)


@shared_task(bind=True, name="task_every_min()")
def task_every_min(self):
    from django.utils import timezone
    return f"task completed at {timezone.now()}"


@shared_task(bind=True, name="Execute Report")
def execute_report(self, params, formdata):
    try:
        log.info("report execution started")
        # prepare basic auth headers
        username = settings.KNOWAGE_USERNAME
        password = settings.KNOWAGE_PASS
        auth_creds = base64.b64encode(
            f'{username}:{password}'.encode('utf-8')).decode('utf-8')
        auth_headers = {'Authorization': f'Basic {auth_creds}'}
        log.info(f'{auth_creds = }, {auth_headers = }')

        # execute the report
        report_execution_url = f"{settings.KNOWAGE_SERVER_URL}restful-services/2.0/documents/{formdata['report_name']}/content?outputType={formdata['format']}"
        print(f'{report_execution_url = }, {params = }')
        log.info(f'{report_execution_url = }, {params = }')
        return requests.post(report_execution_url, headers=auth_headers, json=params)
    except Exception as e:
        log.critical("report execution failed with exception ", exc_info=True)


@shared_task(bind=True, name="Send report on email")
def send_report_on_email(self, formdata, json_report):
    
    import mimetypes
    import json
    jsonresp = {"story": "", "traceback": ""}
    try:
        jsonresp['story'] += f'formdata: {formdata}'
        file_buffer = BytesIO()
        jsonrep = json.loads(json_report)
        report_content = base64.b64decode(jsonrep['report'])
        file_buffer.write(report_content)
        file_buffer.seek(0)
        mime_type, encoding = mimetypes.guess_type(f'.{formdata["format"]}')
        email = EmailMessage(
            subject=f"Per your request, please find the report attached from {settings.COMPANYNAME}",
            from_email=settings.EMAIL_HOST_USER,
            to=formdata['to_addr'],
            cc=formdata['cc'],
            body=formdata.get('email_body'),
        )
        email.attach(
            filename=f'{formdata["report_name"]}.{formdata["format"]}',
            content=file_buffer.getvalue(),
            mimetype=mime_type
        )
        email.send()
        jsonresp['story'] += "email sent"
    except Exception as e:
        log.critical(
            "something went wrong while sending report on email", exc_info=True)
        jsonresp['traceback'] = tb.format_exc()
    return jsonresp


@shared_task(bind=True, name="Create report history")
def create_report_history(self, formdata, userid, buid, EI):
    jsonresp = {'story': "", "traceback": ""}
    try:
        ReportHistory = apps.get_model('reports', "ReportHistory")
        obj = ReportHistory.objects.create(
            traceback=EI[2] if EI[0] else None,
            user_id=userid,
            report_name=formdata['report_name'],
            params={"params": f"{formdata}"},
            export_type=formdata['export_type'],
            bu_id=buid,
            ctzoffset=formdata['ctzoffset'],
            cc_mails=formdata['cc'],
            to_mails=formdata['to_addr'],
            email_body=formdata['email_body'],
        )
        jsonresp['story'] += f"A Report history object created with pk: {obj.pk}"
    except Exception as e:
        log.critical(
            "something went wron while running create_report_history()", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp


@shared_task(bind=True, name="Create Workpermit email notification")
def send_email_notification_for_wp(self, womid, qsetid, approvers, client_id, bu_id):
    jsonresp = {'story': "", "traceback": ""}
    try:
        from django.apps import apps
        from django.template.loader import render_to_string
        Wom = apps.get_model('work_order_management', 'Wom')
        People = apps.get_model('peoples', 'People')
        wp_details = Wom.objects.get_wp_answers(womid)
        wp_obj = Wom.objects.get(id=womid)
        jsonresp['story'] += f"\n{wp_details}"
        if wp_details:
            qset = People.objects.filter(peoplecode__in = approvers)
            for p in qset.values('email', 'id'):
                log.info(f"sending email to {p['email'] = }")
                jsonresp['story'] += f"sending email to {p['email'] = }"
                msg = EmailMessage()
                msg.subject = f"Following Work Permit #{wp_obj.other_data['wp_seqno']} needs your action"
                msg.to = [p['email']]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {'sections': wp_details, 'peopleid':p['id'],
                    "HOST": settings.HOST, "workpermitid": womid}
                html = render_to_string(
                    'work_order_management/workpermit_approver_action.html', context=cxt)
                msg.body = html
                msg.content_subtype = 'html'
                msg.send()
                log.info(f"email sent to {p['email'] = }")
                jsonresp['story'] += f"email sent to {p['email'] = }"
        jsonresp['story'] += f"A Workpermit email sent of pk: {womid}"
    except Exception as e:
        log.critical(
            "something went wron while running create_report_history()", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp
