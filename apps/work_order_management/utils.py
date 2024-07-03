from apps.core.utils import get_email_addresses, send_email
from .models import Wom
from celery.utils.log import get_task_logger
from datetime import timedelta
log = get_task_logger('mobile_service_log')
from django.template.loader import render_to_string 
from django.conf import settings
from apps.peoples.models import People

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
        
        
        
def check_all_approved(womuuid, usercode):
    w = Wom.objects.filter(uuid = womuuid).first()
    all_approved = True
    for approver in w.other_data['wp_approvers']:
        if approver['name'] == usercode:
            approver['status'] = 'APPROVED'
        if approver['status'] != 'APPROVED':
            all_approved = False
    w.save()
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