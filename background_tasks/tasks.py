from intelliwiz_config.celery import app
from celery import shared_task
from background_tasks import utils as butils
from apps.core import utils
from django.apps import apps
from logging import getLogger
from django.db import transaction
from datetime import timedelta, datetime
import traceback as tb
from apps.core.raw_queries import get_query
from pprint import pformat
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
import base64, os, json
from django.core.mail import EmailMessage
from apps.reports.models import ScheduleReport
from apps.reports import utils as rutils
from django.templatetags.static import static


from .move_files_to_GCS import move_files_to_GCS, del_empty_dir, get_files
from .report_tasks import (
    get_scheduled_reports_fromdb, generate_scheduled_report, handle_error,  
    walk_directory, get_report_record, check_time_of_report, 
    remove_reportfile, save_report_to_tmp_folder)
from io import BytesIO


mqlog = getLogger('message_q')
dlog = getLogger('django')
tlog = getLogger('tracking')

@app.task(bind=True, default_retry_delay=300, max_retries=5, name='Send Ticket email')
def send_ticket_email(self, ticket=None, id=None):
    from apps.y_helpdesk.models import Ticket
    from django.conf import settings
    from django.template.loader import render_to_string
    try:
        if not ticket and id:
            ticket = Ticket.objects.get(id=id)
        if ticket:
            dlog.info(f"ticket found with ticket id: {ticket.ticketno}")
            dlog.info("ticket email sending start ")
            resp = {}
            emails = butils.get_email_recipents_for_ticket(ticket)
            dlog.info(f"email addresses of recipents: {emails}")
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
            dlog.info(f'context for email template: {context}')
            html_message = render_to_string('y_helpdesk/ticket_email.html', context)
            msg = EmailMessage()
            msg.body = html_message
            msg.to = emails
            msg.subject = context['subject']
            msg.from_email = settings.EMAIL_HOST_USER
            msg.content_subtype = 'html'
            msg.send()
            dlog.info("ticket email sent")
        else:
            dlog.info('ticket not found no emails will send')
    except Exception as e:
        dlog.critical("Error while sending ticket email", exc_info=True)
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

                    dlog.info("notifying through email...")
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

                    emails = butils.get_email_recipients(rec['bu_id'], rec['client_id'])
                    resp['story'] += f"email recipents are as follows {emails}\n"
                    dlog.info(f"recipents are as follows...{emails}")
                    msg = EmailMessage()
                    msg.subject = subject
                    msg.from_email = settings.EMAIL_HOST_USER
                    msg.to = emails
                    msg.content_subtype = 'html'

                    if rec['ticketcategory__tacode'] == 'RAISETICKETNOTIFY':
                        dlog.info("ticket needs to be generated")
                        context['show_ticket_body'] = True
                        jobdesc = f'AUTOCLOSED {"TOUR" if rec["identifier"] in  ["INTERNALTOUR", "EXTERNALTOUR"] else rec["identifier"] } planned on {pdate} not reported in time'
                        # DB OPERATION
                        ticket_data = butils.create_ticket_for_autoclose(
                            rec, jobdesc)
                        dlog.info(f'{ticket_data}')
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
                    dlog.info(f"mail sent, record_id:{rec['id']}")
                resp = butils.update_job_autoclose_status(rec, resp)

    except Exception as e:
        dlog.critical(f'context in the template:{context}', exc_info=True)
        dlog.error(
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
        dlog.critical("somwthing went wrong while ticket escalation", exc_info=True)
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
    dlog.info(f"total due reminders are {len(reminders)}")
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
            dlog.info(f"Sending reminder mail with subject {subject}")

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
            dlog.info(
                f"Reminder mail sent to {recipents} with subject {subject}")
    except Exception as e:
        dlog.critical("Error while sending reminder email", exc_info=True)
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
                dlog.warning(f"{msg}", exc_info=True)
            total_jobs = len(jobs)

            if total_jobs > 0 and jobs is not None:
                dlog.info("processing jobs started found:= '%s' jobs", (len(jobs)))
                result['story'] += f"total jobs found {total_jobs}\n"
                for job in jobs:
                    result['story'] += f'\nprocessing job with id: {job["id"]}'
                    startdtz, enddtz = calculate_startdtz_enddtz_for_ppm(job)
                    dlog.debug(
                        f"Jobs to be schedhuled from startdatetime {startdtz} to enddatetime {enddtz}")
                    DT, is_cron, resp = get_datetime_list(
                        job['cron'], startdtz, enddtz, resp)
                    if not DT:
                        resp = {
                            'msg': "Please check your Valid From and Valid To dates"}
                        continue
                    dlog.debug(
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
                    dlog.info(
                        f"create_ppm_job Failed job schedule list:={pformat(F)}")
                    for key, value in list(F.items()):
                        dlog.info(
                            f"create_ppm_job job_id: {key} | cron: {value}")
    except Exception as e:
        dlog.critical("something went wrong create_ppm_job", exc_info=True)
        F[str(job['id'])] = {'tb': tb.format_exc()}

    return resp, F, d, result


@app.task(bind=True, default_retry_delay=300, max_retries=5, name='Face recognition')
def perform_facerecognition_bgt(self, pel_uuid, peopleid, db='default'):
    # sourcery skip: remove-redundant-except-handler
    result = {'story': "perform_facerecognition_bgt()\n", "traceback": ""}
    result['story'] += f"inputs are {pel_uuid = } {peopleid = }, {db = }\n"
    try:
        mqlog.info("perform_facerecognition ...start [+]")
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
                    mqlog.info(f'{images_info}')
                    result['story'] += f'{images_info}\n'
                    from deepface import DeepFace
                    fr_results = DeepFace.verify(
                        img1_path=default_peopleimg, img2_path=pel_att.people_event_pic, enforce_detection=True, detector_backend='ssd')
                    mqlog.info(
                        f"deepface verification completed and results are {fr_results}")
                    result[
                        'story'] += f"deepface verification completed and results are {fr_results}\n"
                    PeopleEventlog = apps.get_model(
                        'attendance', 'PeopleEventlog')
                    if PeopleEventlog.objects.update_fr_results(fr_results, pel_uuid, peopleid, db):
                        mqlog.info(
                            "updation of fr_results in peopleeventlog is completed...")
    except ValueError as v:
        mqlog.error(
            "face recogntion image not found or face is not there...", exc_info=True)
        result['traceback'] += f'{tb.format_exc()}'
    except Exception as e:
        mqlog.critical(
            "something went wrong! while performing face-recogntion in background", exc_info=True)
        result['traceback'] += f'{tb.format_exc()}'
        self.retry(e)
        raise
    return result


@app.task(bind=True,  name="alert_sendmail()")
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
        dlog.critical(
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
        dlog.critical(
            "something went wron while running create_report_history()", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp


@shared_task(bind=True, name = "Send Email Notificatio to Verifier")
def send_email_notification_for_wp_verifier(self,womid,verifiers,sitename,workpermit_status,permit_name,workpermit_attachment,vendor_name):
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
            qset = People.objects.filter(peoplecode__in = verifiers)
            for p in qset.values('email','id'):
                dlog.info(f"Sending Email to {p['email'] = }")
                msg = EmailMessage()
                msg.subject = f"{permit_name}-{wp_obj.other_data['wp_seqno']}-{sitename}-Verification Pending"            
                msg.to = [p['email']]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {
                    'peopleid':p['id'],
                    'HOST':settings.HOST,
                    'workpermitid':womid,
                    'sitename':sitename,
                    'status':workpermit_status,
                    'permit_no':wp_obj.other_data['wp_seqno'],
                    'permit_name':permit_name,
                    'vendor_name':vendor_name
                }
                html = render_to_string(
                    'work_order_management/workpermit_verifier_action.html',context=cxt
                )
                msg.body = html
                msg.content_subtype = 'html'
                msg.attach_file(workpermit_attachment, mimetype='application/pdf')
                msg.send()
                dlog.info(f"Email sent to {p['email'] = }")
                jsonresp['story']+=f"Email sent to {p['email'] = }"
        jsonresp['story'] += f"A {permit_name} email sent of pk: {womid}: "
    except Exception as e:
        dlog.critical(
            "Something went wrong while running send_email_notification_for_wp_verifier",exc_info=True
            )
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp
        
@shared_task(bind=True, name="Create Workpermit email notification")
def send_email_notification_for_wp(self, womid, qsetid, approvers, client_id, bu_id,sitename,workpermit_status,vendor_name):
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
            dlog.info("Qset: ",qset)
            for p in qset.values('email', 'id'):
                dlog.info(f"sending email to {p['email'] = }")
                jsonresp['story'] += f"sending email to {p['email'] = }"
                msg = EmailMessage()
                msg.subject = f"General Work Permit #{wp_obj.other_data['wp_seqno']} needs your approval"
                msg.to = [p['email']]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {
                    'peopleid':p['id'],
                    "HOST": settings.HOST, 
                    "workpermitid": womid,
                    'sitename':sitename,
                    'status':workpermit_status,
                    'permit_no':wp_obj.other_data['wp_seqno'],
                    'permit_name':'General Work Permit',
                    'vendor_name':vendor_name}
                html = render_to_string(
                    'work_order_management/workpermit_approver_action.html', context=cxt)
                msg.body = html
                # msg.attach_file(workpermit_attachment,mimetype='application/pdf')
                msg.content_subtype = 'html'
                #msg.attach_file(workpermit_attachment, mimetype='application/pdf')
                msg.send()
                dlog.info(f"email sent to {p['email'] = }")
                jsonresp['story'] += f"email sent to {p['email'] = }"
        jsonresp['story'] += f"A Workpermit email sent of pk: {womid}"
    except Exception as e:
        dlog.critical(
            "something went wron while running send_email_notification_for_wp", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp



@shared_task(bind=True, name="Create Workpermit email notification for vendor and security")
def send_email_notification_for_vendor_and_security(self,wom_id,sitename,workpermit_status):
    jsonresp = {'story':"", 'traceback':""}
    try:
        from apps.work_order_management.models import Wom,WomDetails
        from django.template.loader import render_to_string
        wom = Wom.objects.filter(parent_id=wom_id)
        wom_detail = wom[4].id
        wom_detail_email_section = WomDetails.objects.filter(wom_id=wom_detail)
        wp_details = Wom.objects.get_wp_answers(wom_id)
        dlog.info(f"WP Details: ",wp_details)
        for email in wom_detail_email_section:
            dlog.info(f"email: {email.answer}")
            msg = EmailMessage()
            msg.subject = f"General Work Permit #{wp_details[0]}"
            msg.to = [email.answer]
            msg.from_email = settings.EMAIL_HOST_USER
            cxt = {'sections': wp_details[1],"HOST": settings.HOST, "workpermitid": wom_id,'permit_name':'General Work Permit','sitename':sitename,'permit_no':wp_details[0],'status':workpermit_status}
            html = render_to_string(
                'work_order_management/workpermit_vendor.html', context=cxt)
            msg.body = html
            msg.content_subtype = 'html'
            #msg.attach_file(workpermit_attachment, mimetype='application/pdf')
            msg.send()
            dlog.info(f"email sent to {email.answer}")
    except Exception as e:
        dlog.critical("something went wrong while sending email to vendor and security", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp

@shared_task(bind=True, name="Create SLA email notification for vendor")
def send_email_notification_for_sla_vendor(self,wom_id,report_attachment,sitename):
    jsonresp = {'story':"", 'traceback':""}
    try:
        from apps.work_order_management.models import Wom,WomDetails
        from apps.work_order_management.models import Vendor
        from django.template.loader import render_to_string
        wom = Wom.objects.filter(uuid=wom_id)
        vendor_email = Vendor.objects.get(id=wom[0].vendor_id)
        msg = EmailMessage()
        sla_seqno = wom[0].other_data['wp_seqno']
        msg.subject = f" {sitename} Vendor Performance #{sla_seqno}"
        msg.to = [vendor_email.email]
        msg.from_email = settings.EMAIL_HOST_USER
        cxt = {
            'sla_report_no':sla_seqno,
            'sitename':sitename,
            'report_name':'Vendor Performance Report',
        }
        html = render_to_string(
            'work_order_management/sla_vendor.html', context=cxt)
        msg.body = html
        msg.content_subtype = 'html'
        msg.attach_file(report_attachment, mimetype='application/pdf')
        msg.send()
        dlog.info(f"email sent to {vendor_email.email}")
    except Exception as e:
        dlog.critical("something went wrong while sending email to vendor and security", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp

@shared_task(name="upload-old-files-to-cloud-storage")
def move_media_to_cloud_storage():
    resp = {}
    try:
        dlog.info("move_media_to_cloud_storage execution started [+]")
        directory_path = f'{settings.MEDIA_ROOT}/transactions/'
        path_list = get_files(directory_path)
        move_files_to_GCS(path_list, settings.BUCKET)
        del_empty_dir(directory_path)
        pass
    except Exception as exc:
        dlog.critical(
            "something went wron while running create_report_history()", exc_info=True)
        resp['traceback'] = tb.format_exc() 
    else:
        resp['msg'] = "Completed without any errors"
    return resp

@shared_task(name='create_reports_bg')
def create_scheduled_reports():
    state_map = {'not_generated':0, 'skipped':0, 'generated':0, 'processed':0}

    resp = dict()
    try:
        data = get_scheduled_reports_fromdb()
        dlog.info(f"Found {len(data)} for reports for generation in background")
        if data:
            for record in data:
                state_map = generate_scheduled_report(record, state_map)
        resp['msg'] = f'Total {len(data)} report/reports processed at {timezone.now()}'
    except Exception as e:
        resp['traceback'] = tb.format_exc()
        dlog.critical("Error while creating report:", exc_info=True)
    state_map['processed'] = len(data)
    resp['state_map'] = state_map
    return resp





@shared_task(name="send_generated_report_onmail")
def send_generated_report_on_mail():
    story = {
        'start_time': timezone.now(),
        'files_processed': 0,
        'emails_sent': 0,
        'errors': [],
    }

    try:
        for file in walk_directory(settings.TEMP_REPORTS_GENERATED):
           
            story['files_processed'] += 1
            sendmail, filename_without_extension = check_time_of_report(file)
            if sendmail:
                if record := get_report_record(filename_without_extension):
                    utils.send_email(
                    subject='Test Subject',
                        body='Test Body',
                        to=record.to_addr,
                        cc=record.cc,
                        atts=[file]
                    )
                    story['emails_sent'] += 1
                    #file deletion
                    story = remove_reportfile(file, story)
                else:
                    dlog.info(f"No record found for file {os.path.basename(file)}")
            else:
                dlog.info("No files to send at this moment")
    except Exception as e:
       story['errors'].append(handle_error(e))
       dlog.critical("something went wrong", exc_info=True)
    story['end_time'] = timezone.now()
    return story

@shared_task(bind=True, name="send_generated_report_onfly_email")
def send_generated_report_onfly_email(self, filepath, fromemail, to, cc, ctzoffset):
    story = {'msg':['send_generated_report_onfly_email [started]']}
    try:
        story['msg'].append(f'{filepath = } {fromemail = } {to = } {cc =}')
        currenttime = timezone.now() + timedelta(minutes=int(ctzoffset))
        msg = EmailMessage(
            f"Your Requested report! on {currenttime.strftime('%d-%b-%Y %H:%M:%S')}",
            from_email=fromemail,
            to=to,
            cc=cc
        )
        msg.attach_file(filepath)
        msg.send()
        story['msg'].append('Email Sent')
        remove_reportfile(filepath, story)
        story['msg'].append('send_generated_report_onfly_email [ended]')
    except Exception  as e:
        dlog.critical("something went wrong in bg task send_generated_report_onfly_email", exc_info=True)
    return story
        
@app.task(bind=True, default_retry_delay=300, max_retries=5, name="process_graphql_mutation_async")
def process_graphql_mutation_async(self, payload):
    """
    Process the incoming payload containing a GraphQL mutation and file data.

    Args:
        payload (str): The JSON-encoded payload containing the mutation query and variables.

    Returns:
        str: The JSON-encoded response containing the mutation result or errors.
    """
    from apps.service.utils import execute_graphql_mutations
    try:
        post_data = json.loads(payload)
        query = post_data.get('mutation')
        variables = post_data.get('variables', {})

        if query and variables:
            resp = execute_graphql_mutations(query, variables)
        else:
            mqlog.warning("Invalid records or query in the payload.")
            resp = json.dumps({'errors': ['No file data found']})
    except Exception as e:
        mqlog.error(f"Error processing payload: {e}", exc_info=True)
        resp = json.dumps({'errors': [str(e)]})
        raise e
    return resp
    
    
@app.task(bind=True, name="say_hi")
def say_hi(self, name):
    return f"Hi {name}"


@app.task(bind=True, name="insert_json_records_bulk")
def insert_json_records_async(self, records, tablename):
    from apps.service.utils import get_model_or_form
    from apps.service.validators import clean_record
    if model := get_model_or_form(tablename):
        tlog.info("processing bulk json records for insert/update")
        for record in records:
            record = json.loads(record)
            record = json.loads(record)
            record = clean_record(record)
            tlog.info(f"processing record {pformat(record)}")
            if model.objects.filter(uuid=record['uuid']).exists():
                model.objects.filter(uuid=record['uuid']).update(**record)
                tlog.info("record is already exist so updating it now..")
            else:
                tlog.info("record is not exist so creating new one..")
                model.objects.create(**record)
        return "Records inserted/updated successfully"
    
    
    
@app.task(bind=True, name="create_save_report_async")
def create_save_report_async(self, formdata, client_id, user_email, user_id):
    try:
        returnfile = formdata.get('export_type') == 'SEND'
        report_essentials = rutils.ReportEssentials(report_name=formdata['report_name'])
        dlog.info(f"report essentials: {report_essentials}")
        ReportFormat = report_essentials.get_report_export_object()
        report = ReportFormat(filename=formdata['report_name'], client_id=client_id,
                                formdata=formdata,  returnfile=True)
        dlog.info(f"Report Format initialized, {report}")
        
        if response := report.execute():
            if returnfile:
                rutils.process_sendingreport_on_email(response, formdata, user_email)
                return {"status": 201, "message": "Report generated successfully and email sent", 'alert':'alert-success'}
            filepath = save_report_to_tmp_folder(formdata['report_name'], ext=formdata['format'], report_output=response, dir=f'{settings.ONDEMAND_REPORTS_GENERATED}/{user_id}')
            dlog.info(f"Report saved at tmeporary location: {filepath}")
            return {"filepath":filepath, 'filename':f'{formdata["report_name"]}.{formdata["format"]}', 'status':200, "message": "Report generated successfully", 'alert':'alert-success'}
        else:
            return {"status": 404, "message": "No data found matching your report criteria.\
        Please check your entries and try generating the report again", 'alert':'alert-warning'}
    except Exception as e:
        dlog.error(f"Error generating report: {e}")
        return {"status": 500, "message": "Internal Server Error", "alert":"alert-danger"}
        
            
@app.task(bind=True, name="cleanup_reports_which_are_12hrs_old")
def cleanup_reports_which_are_12hrs_old(self, dir_path,hours_old=12):
    for root, dirs, files in os.walk(dir_path):
        for filename in files:
            file_path = os.path.join(root, filename)
            threshold = datetime.now() - timedelta(hours=hours_old)
            try:
                if os.path.isfile(file_path):
                    file_stats = os.stat(file_path)
                    last_modified = datetime.fromtimestamp(file_stats.st_mtime)
                    if last_modified < threshold:
                        os.remove(file_path)
                        dlog.info(f"Deleted file: {file_path} as it was older than {hours_old} hours")
            except Exception as e:
                dlog.error(f"Error deleting file {file_path}: {e}")
        

@app.task(bind=True, default_retry_delay=300, max_retries=5, name="process_graphql_download_async")
def process_graphql_download_async(self, payload):
    """
    Process the incoming payload containing a GraphQL download and file data.

    Args:
        payload (str): The JSON-encoded payload containing the mutation query and variables.

    Returns:
        str: The JSON-encoded response containing the mutation result or errors.
    """
    from apps.service.utils import execute_graphql_mutations
    try:
        post_data = json.loads(payload)
        query = post_data.get('query')

        if query:
            resp = execute_graphql_mutations(query, download=True)
        else:
            mqlog.warning("Invalid records or query in the payload.")
            resp = json.dumps({'errors': ['No file data found']})
    except Exception as e:
        mqlog.error(f"Error processing payload: {e}", exc_info=True)
        resp = json.dumps({'errors': [str(e)]})
        raise e
    return resp


@shared_task(bind=True, name="send_email_notification_for_sla_report")
def send_email_notification_for_sla_report(self,slaid,sitename):
    jsonresp = {'story': "", "traceback": ""}
    try:
        from django.apps import apps
        from django.template.loader import render_to_string
        from apps.reports.report_designs.service_level_agreement import ServiceLevelAgreement
        from apps.work_order_management.models import Vendor
        from dateutil.relativedelta import relativedelta
        from datetime import datetime
        Wom = apps.get_model('work_order_management', 'Wom')
        People = apps.get_model('peoples', 'People')
        sla_details,rounded_overall_score,question_ans,all_average_score,remarks = Wom.objects.get_sla_answers(slaid)
        sla_record = Wom.objects.filter(id=slaid)[0]
        approvers = sla_record.approvers 
        status = sla_record.workpermit
        jsonresp['story'] += f"\n{sla_details}"
        report_no = sla_record.other_data['wp_seqno']
        uuid = sla_record.uuid
        month = (datetime.now() - relativedelta(months=1)).strftime('%B')
        current_year = datetime.now().year
        sla_report_obj = ServiceLevelAgreement(filename='Service Level Agreement', formdata={'id':slaid,'bu__buname':sitename,'submit_button_flow':'true','filename':'Service Level Agreement','workpermit':sla_record.workpermit})
        attachment = sla_report_obj.execute()
        vendor_id = sla_record.vendor_id
        vendor_name = Vendor.objects.get(id=vendor_id).name
        if sla_details:
            qset = People.objects.filter(peoplecode__in = approvers)
            dlog.info("Qset: ",qset)
            for p in qset.values('email', 'id'):
                dlog.info(f"sending email to {p['email'] = }")
                jsonresp['story'] += f"sending email to {p['email'] = }"
                msg = EmailMessage()
                msg.subject = f"{sitename} Vendor Performance {vendor_name} of {month}-{current_year}"
                msg.to = [p['email']]
                msg.from_email = settings.EMAIL_HOST_USER
                cxt = {'sections': sla_details, 'peopleid':p['id'],
                    "HOST": settings.HOST, "slaid": slaid,'sitename':sitename,'rounded_overall_score':rounded_overall_score,
                    'peopleid':p['id'],'reportid':uuid,'report_name':'Vendor Performance','report_no':report_no,'status':status,
                    'vendorname':vendor_name
                    }
                html = render_to_string(
                    'work_order_management/sla_report_approver_action.html', context=cxt)
                msg.body = html
                msg.content_subtype = 'html'
                msg.attach_file(attachment, mimetype='application/pdf')
                msg.send()
                dlog.info(f"email sent to {p['email'] = }")
                jsonresp['story'] += f"email sent to {p['email'] = }"
            jsonresp['story'] += f"A Workpermit email sent of pk: {slaid}"
    except Exception as e:
        dlog.critical("something went wrong while runing sending email to approvers", exc_info=True)
        jsonresp['traceback'] += tb.format_exc()
    return jsonresp
