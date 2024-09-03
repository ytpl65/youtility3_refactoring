from apps.core.utils import get_email_addresses, send_email
from .models import Wom
from celery.utils.log import get_task_logger
from datetime import timedelta
log = get_task_logger('mobile_service_log')
from django.template.loader import render_to_string 
from django.conf import settings
from apps.peoples.models import People
from django.http import QueryDict
from apps.peoples import utils as putils
from apps.activity.models import QuestionSetBelonging,QuestionSet
from apps.work_order_management.models import WomDetails
from django.http import response as rp
from background_tasks.tasks import send_email_notification_for_sla_report
import logging
import getpass
logger = logging.getLogger('__main__')
log = logger
import os
from apps.reports.report_designs.workpermit import GeneralWorkPermit
def check_attachments_if_any(wo):
    from apps.activity.models import Attachment
    return Attachment.objects.get_att_given_owner(wo.uuid)

def notify_wo_creation(id):
    '''
    function notifies vendor and creator about the new 
    work order has been created
    '''
    if wo := Wom.objects.filter(id=id).first():
        peopleids = [wo.cuser_id, wo.muser_id]
        
        emails = get_email_addresses(people_ids=peopleids)
        emails += [wo.vendor.email]
        log.info(f'Email Addresses of recipents are {emails=}')
        subject = f'New work order #{wo.id} from {wo.client.buname}'
        context = {
            'workorderid'   : id,
            'description'   : wo.description,
            'priority'      : wo.priority,
            'vendorname'    : wo.vendor.name,
            'plandatetime'  : wo.plandatetime + timedelta(minutes=wo.ctzoffset),
            'expirydatetime': wo.expirydatetime + timedelta(minutes=wo.ctzoffset),
            'asset'         : wo.asset.assetname if wo.asset_id not in [1, None] else None,
            'cuseremail'    : wo.cuser.email,
            'cusername'     : wo.cuser.peoplename,
            'cdtz'          : wo.cdtz + timedelta(minutes=wo.ctzoffset),
            'token'         : wo.other_data['token'],
            'HOST'          : settings.HOST 
        }
        if atts := check_attachments_if_any(wo):
            attachments = [f"{settings.MEDIA_ROOT}/{att['filepath']}{att['filename']}" for att in atts]
        
        html_message = render_to_string('work_order_management/work_order_email.html', context=context)
        send_email(
            subject=subject, body=html_message, to=emails, atts= attachments if atts else None
        )
        wo.ismailsent = True
        wo.save()
        return wo
    else:
        log.info('object not found')
        
def check_all_verified(womuuid,usercode):
    w = Wom.objects.filter(uuid = womuuid).first()
    all_verified = True
    log.info(f"{usercode}, {womuuid}")
    for verifier in w.other_data['wp_verifiers']:
        log.info(f"Approver {verifier}")
        if verifier['name'] == usercode:
            verifier['status'] = 'APPROVED'
            log.info(f"verifier {usercode} has approved with status code {verifier['status']}")
        if verifier['status'] != 'APPROVED':
            all_verified = False
    w.save()
    log.info(f"all approved status is {all_verified}")
    return all_verified
        
def check_all_approved(womuuid, usercode):
    w = Wom.objects.filter(uuid = womuuid).first()
    all_approved = True
    log.info(f"{usercode}, {womuuid}")
    for approver in w.other_data['wp_approvers']:
        log.info(f"Approver {approver}")
        if approver['name'] == usercode:
            approver['status'] = 'APPROVED'
            log.info(f"approver {usercode} has approved with status code {approver['status']}")
        if approver['status'] != 'APPROVED':
            all_approved = False
    w.save()
    log.info(f"all approved status is {all_approved}")
    return all_approved
    
def reject_workpermit(womuuid, usercode):
    w = Wom.objects.filter(uuid = womuuid).first()
    for approver in w.other_data['wp_approvers']:
        if approver['name'] == usercode:
            approver['status'] = 'REJECTED'
    w.save()
    
def save_approvers_injson(wp):
    log.info("saving approvers started")
    wp_approvers = [
        {'name': approver, 'status': 'PENDING'} for approver in wp.approvers
    ]
    wp.other_data['wp_approvers'] = wp_approvers
    wp.save()
    log.info("saving approvers ended")
    return wp

def save_verifiers_injson(wp):
    log.info("saving verifiers started")
    wp_verifiers = [
        {'name': verifier, 'status':'PENDING'} for verifier in wp.verifiers
    ]
    wp.other_data['wp_verifiers'] = wp_verifiers
    wp.save()
    log.info("saving verifiers ended")
    return wp

def save_workpermit_name_injson(wp,permit_name):
    wp.other_data['wp_name'] = permit_name
    wp.save()
    return wp

def get_approvers(approver_codes):
    approvers = []
    for code in approver_codes:
        try:
            people = People.objects.get(peoplecode = code)
            approvers.append({'peoplename': people.peoplename})
        except People.DoesNotExist:
            approvers.append({'peoplecode': code, 'peoplename': code})
    return approvers


def extract_data(wp_answers):
        for section in wp_answers:
            for question in section['questions']:
                if question['question__quesname'] == 'Permit Authorized by':
                    return question['answer']
                


def handle_valid_form(form, R, request, create):
    S = request.session
    sla = form.save(commit=False)
    print("sla:", sla.uuid,sla.id)
    sla.uuid = request.POST.get('uuid')
    sla = putils.save_userinfo(
        sla, request.user, request.session, create = create)
    sla = save_approvers_injson(sla)
    formdata = QueryDict(request.POST['sladetails']).copy()
    print("Form data:" ,formdata )
    overall_score = get_overall_score(sla.id)
    print("Overall Score",overall_score)
    sla.other_data['overall_score'] = overall_score
    create_sla_details(request.POST, sla, request, formdata)
    sitename = S.get('sitename')
    send_email_notification_for_sla_report.delay(sla.id,sitename)
    print("sla:", sla)
    return rp.JsonResponse({'pk':sla.id})


def create_sla_details(R,wom,request,formdata):
        SECTION_WEIGHTAGE = {
            'WORK SAFETY': 0.2,
            'SERVICE QUALITY':0.2,
            'SERVICE DELIVERY':0.15,
            'LEGAL COMPLIANCE':0.2,
            'Documentation / record':0.1,
            'ORGANISATION RESPONSIVENESS':0.05,
            'TECHNOLOGY / DESIGN':0.05,
            'CPI':0.05
        }
        log.info(f'creating sla_details started {R}')
        S = request.session
        overall_score = 0
        for k,v in formdata.items():
            log.debug(f'form name, value {k}, {v}')
            if k not in ['ctzoffset', 'wom_id', 'action', 'csrfmiddlewaretoken'] and '_' in k:
                ids = k.split('_')
                qsb_id = ids[0]
                qset_id = ids[1]

                qsb_obj = QuestionSetBelonging.objects.filter(id=qsb_id).first()

                if qsb_obj.answertype in  ['NUMERIC'] and qsb_obj.alerton and len(qsb_obj.alerton) > 0:
                    alerton = qsb_obj.alerton.replace('>', '').replace('<', '').split(',')
                    if len(alerton) > 1:
                        _min, _max = alerton[0], alerton[1]
                        alerts = float(v) < float(_min) or float(v) > float(_max)
                else:
                    alerts = False

                childwom = create_child_wom(wom,qset_id)
                lookup_args = {
                    'wom_id':childwom.id,
                    'question_id':qsb_obj.question_id,
                    'qset_id':qset_id
                }
                default_data = {
                    'seqno'       : qsb_obj.seqno,
                    'answertype'  : qsb_obj.answertype,
                    'answer'      : v,
                    'isavpt'      : qsb_obj.isavpt,
                    'options'     : qsb_obj.options,
                    'min'         : qsb_obj.min,
                    'max'         : qsb_obj.max,
                    'alerton'     : qsb_obj.alerton,
                    'ismandatory' : qsb_obj.ismandatory,
                    'alerts'      : alerts,
                    'cuser_id'    : request.user.id,
                    'muser_id'    : request.user.id,
                }
                data = lookup_args | default_data

                WomDetails.objects.create(
                    **data
                )
                log.info(f"wom detail is created for the for the child wom: {childwom.description}")


def create_child_wom(wom, qset_id):
    qset = QuestionSet.objects.get(id=qset_id)
    if childwom := Wom.objects.filter(
        parent_id = wom.id,
        qset_id = qset.id,
        seqno = qset.seqno
    ).first():
        log.info(f"wom already exist with qset_id {qset_id} so returning it")
        return childwom
    else:
        log.info(f'creating wom for qset_id {qset_id}')
        SECTION_WEIGHTAGE = {
            'WORK SAFETY': 0.2,
            'SERVICE QUALITY':0.2,
            'SERVICE DELIVERY':0.15,
            'LEGAL COMPLIANCE':0.2,
            'Documentation / record':0.1,
            'ORGANISATION RESPONSIVENESS':0.05,
            'TECHNOLOGY / DESIGN':0.05,
            'CPI':0.05
        }
        qs = QuestionSet.objects.get(id=qset_id).qsetname
        if qs in SECTION_WEIGHTAGE:
            section_weightage = SECTION_WEIGHTAGE[qs]
            wom.other_data['section_weightage'] = section_weightage
        return Wom.objects.create(
                parent_id      = wom.id,
                description    = qset.qsetname,
                plandatetime   = wom.plandatetime,
                expirydatetime = wom.expirydatetime,
                starttime      = wom.starttime,
                gpslocation    = wom.gpslocation,
                asset          = wom.asset,
                location       = wom.location,
                workstatus     = wom.workstatus,
                seqno          = qset.seqno,
                approvers      = wom.approvers,
                workpermit     = wom.workpermit,
                priority       = wom.priority,
                vendor         = wom.vendor,
                performedby    = wom.performedby,
                alerts         = wom.alerts,
                client         = wom.client,
                bu             = wom.bu,
                ticketcategory = wom.ticketcategory,
                other_data     = wom.other_data,
                qset           = qset,
                cuser          = wom.cuser,
                muser          = wom.muser,
                ctzoffset      = wom.ctzoffset
        )
    

def get_overall_score(id):
    sla_answers_data,overall_score,question_ans,all_average_score,remarks = Wom.objects.sla_data_for_report(id)
    return overall_score

def get_pdf_path():
    user_name = getpass.getuser()
    tmp_pdf_location = f'/home/{user_name}/tmp_reports'
    if not os.path.exists(tmp_pdf_location):
        os.makedirs(tmp_pdf_location)
    return tmp_pdf_location

def save_pdf_to_tmp_location(report_pdf_object,report_name,report_number):
    tmp_pdf_location = get_pdf_path()
    output_pdf = f'{report_name}-{report_number}.pdf'
    final_path = os.path.join(tmp_pdf_location,output_pdf)
    with open(final_path, 'wb') as file:
        file.write(report_pdf_object)
    return final_path