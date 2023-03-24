from apps.core.utils import get_email_addresses, send_email
from .models import Wom
from celery.utils.log import get_task_logger
from datetime import timedelta
log = get_task_logger('mobile_service_log')
from django.template.loader import render_to_string 
from django.conf import settings


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
        
        html_message = render_to_string('work_order_email.html', context=context)
        send_email(
            subject=subject, body=html_message, to=emails, atts= attachments if atts else None
        )
        
        
        
        