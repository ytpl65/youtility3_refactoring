from celery.utils.log import get_task_logger
import traceback as tb
log = get_task_logger('django')

def get_email_recipents_for_ticket(ticket):
    from apps.y_helpdesk.models import Ticket
    from apps.peoples.models import Pgbelonging
    emails = []
    group_emails = Pgbelonging.objects.select_related('pgroup', 'people').filter(
        pgroup_id = ticket.assignedtogroup_id
    ).exclude(people_id=1).values('people__email')
    log.debug(f"group emails:{group_emails}")


    temails = Ticket.objects.select_related('people', 'pgroup', 'cuser', 'muser').filter(
        id = ticket.id
    ).values(
        'assignedtopeople__email', 'cuser__email', 'muser__email'
    ).first()
    log.debug(f"ticket emails: {temails}")
    emails+= [temails['assignedtopeople__email'], temails['cuser__email'], temails['muser__email']]
    emails.extend(email['people__email'] for email in group_emails)
    return list(set(emails))

def send_ticket_email(ticket=None, id=None):
    from django.core.mail import  EmailMessage
    from apps.y_helpdesk.models import Ticket
    from django.conf import settings
    from django.template.loader import render_to_string
    try:
        if not ticket and id:
            ticket = Ticket.objects.get(id=id)
        if ticket:
            log.info(f"ticket found with ticket id: {ticket.id}")
            log.info("ticket email sending start ")
            resp = {}
            emails = get_email_recipents_for_ticket(ticket)
            log.info(f"email addresses of recipents: {emails}")
            updated_or_created = "Created" if ticket.cdtz == ticket.mdtz else "Updated"
            context = {
                'subject'   : f"Ticket {updated_or_created}: Ticket Number - {ticket.id} Site Name: {ticket.bu.buname}",
                'desc'      : ticket.ticketdesc,
                'template'  : ticket.ticketcategory.taname,
                'status'    : ticket.status,
                'createdon' : ticket.cdtz.strftime("%Y-%m-%d %H:%M:%S"),
                'modifiedon': ticket.mdtz.strftime("%Y-%m-%d %H:%M:%S"),
                'modifiedby': ticket.muser.peoplename,
                'assignedto': ticket.assignedtogroup.groupname if ticket.assignedtopeople_id in [None, 1] else ticket.assignedtopeople.peoplename,
                'comments'  : ticket.comments,
                "priority"  : ticket.priority,
            }
            log.info(f'context for email template: {context}')
            html_message = render_to_string('ticket_email.html', context)
            msg = EmailMessage()
            msg.body = html_message
            msg.to = emails
            msg.subject = context['subject']
            msg.from_email = settings.EMAIL_HOST_USER
            msg.content_subtype = 'html'
            msg.send()
            log.info("ticket email sent")
        else: log.info('ticket not found no emails will send')
    except Exception as e:
        log.error("Error while sending reminder email")
        resp['traceback'] = tb.format_exc()
    return resp