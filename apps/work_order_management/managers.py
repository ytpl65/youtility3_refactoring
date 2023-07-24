from django.db import models
from django.db.models.functions import Concat, Cast
from django.db.models import CharField, Value as V
from django.db.models import Q, F, Count, Case, When
from datetime import datetime, timedelta
import logging
import json
from django.apps import apps
logger = logging.getLogger('__main__')


class VendorManager(models.Manager):
    use_in_migrations = True
    
    def get_vendor_list(self, request, fields, related):
        R , S = request.GET, request.session
        if R.get('params'): P = json.loads(R.get('params', {}))
        
        qobjs =  self.select_related(*related).filter(
            #bu_id = S['bu_id'],
            client_id = S['client_id'],
            enable=True
        ).values(*fields)
        return qobjs or self.none()
    
    def get_vendors_for_mobile(self, request, clientid, mdtz, buid, ctzoffset):
        if not isinstance(mdtz, datetime):
            mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        mdtz = mdtz - timedelta(minutes=ctzoffset)
            
        qset = self.filter(
            Q(bu_id = buid) | Q(show_to_all_sites = True),
            mdtz__gte = mdtz,
            client_id = clientid, 
            
        ).values()
        
        return qset or self.none()
    
class ApproverManager(models.Manager):
    use_in_migrations = True
    
    def get_approver_list(self, request, fields, related):
        R,S  = request.GET, request.session
        qobjs =  self.select_related(*related).filter(
            bu_id = S['bu_id'],
            
        ).values(*fields)
        return qobjs or self.none()
    
    def get_approver_options_wp(self, request):
        S = request.session
        qset = self.annotate(
            text = F('people__peoplename'),
        ).filter(approverfor__contains = ['WORKPERMIT'], bu_id = S['bu_id']).values('id', 'text')
        return qset or self.none()


class WorkOrderManager(models.Manager):
    use_in_migrations = True
    
    def get_workorder_list(self, request, fields, related):
        from .models import Wom
        S = request.session
        P = json.loads(request.GET['params'])
        qset = self.filter(
            cdtz__date__gte = P['from'],
            cdtz__date__lte = P['to'],
            client_id = S['client_id'],
            workpermit = Wom.WorkPermitStatus.NOTNEED
        ).select_related(*related).values(
            *fields
        )
        if P.get('status'):
            qset = qset.filter(workstatus =P['status'])
        return qset or self.none()
    
    def get_workpermitlist(self, request):
        R, S = request.GET, request.session
        P = json.loads(R.get('params', "{}"))
        ic(P)
        qobjs = self.filter(
            ~Q(workpermit__in =  ['NOT_REQUIRED', 'NOTREQUIRED']),
            parent_id = 1,
            client_id = S['client_id'],
            cdtz__date__gte = P['from'],
            cdtz__date__lte = P['to'],
        ).values('cdtz', 'other_data__wp_seqno', 'qset__qsetname', 'workpermit', 'workstatus', 'id', 'cuser__peoplename')
        return qobjs or self.none()
         
    def get_workpermit_details(self, request, wp_qset_id):
        S = request.session
        QuestionSet = apps.get_model('activity', 'QuestionSet')
        wp_details = []
        sections_qset = QuestionSet.objects.filter(parent_id = wp_qset_id).order_by('seqno')
        for section in sections_qset:
            sq = {
                "section":section.qsetname,
                "sectionID":section.seqno,
                'questions':section.questionsetbelonging_set.values(
                    'question__quesname', 'answertype', 'qset_id',
                    'min', 'max', 'options', 'id', 'ismandatory').order_by('seqno')
            }
            wp_details.append(sq)
        return wp_details or self.none()
    
    def get_return_wp_details(self, request):
        S = request.session
        QuestionSet = apps.get_model('activity', 'QuestionSet')
        section_qset = QuestionSet.objects.filter(type='RETURN_WORK_PERMIT')
        rwp_details = []
        for section in section_qset:
            sq = {
                "section":section.qsetname,
                "sectionID":section.seqno,
                'questions':section.questionsetbelonging_set.values(
                    'question__quesname', 'answertype', 'qset_id',
                    'min', 'max', 'options', 'id', 'ismandatory').order_by('seqno')
            }
            rwp_details.append(sq)
        return rwp_details or self.none()
            
        
    
    def get_wp_answers(self, qsetid, womid):
        
        childwoms = self.filter(parent_id = womid).order_by('seqno')
        ic(qsetid, womid)
        QuestionSet = apps.get_model('activity', 'QuestionSet')
        wp_details = []
        sections_qset = QuestionSet.objects.filter(parent_id = qsetid).order_by('seqno')
        for childwom in childwoms:
            sq = {
                "section":childwom.description,
                "sectionID":childwom.seqno,
                'questions':childwom.qset_answers.filter(wom_id = womid).values(
                    'question__quesname', 'answertype', 'answer', 'qset_id',
                    'min', 'max', 'options', 'id', 'ismandatory').order_by('seqno')
            }
            ic(sq)
            wp_details.append(sq)
        return wp_details or self.none()
    

    def get_approver_list(self, womid):
        if womid == 'None':return []
        obj = self.filter(
            id = womid
        ).values('other_data').first()
        return obj['other_data']['wp_approvers'] or []
    
    
    def get_wom_status_chart(self, request):
        S,R = request.session, request.GET
        qset = self.filter(
            bu_id = S['bu_id'],
            client_id = S['client_id'],
            cdtz__date__gte = R['from'],
            cdtz__date__lte = R['upto'],
            workpermit = 'NOT_REQUIRED'
        )
        assigned    = qset.filter(workstatus = 'ASSIGNED').count()
        re_assigned = qset.filter(workstatus = 'RE_ASSIGNED').count()
        completed   = qset.filter(workstatus = 'COMPLETED').count()
        cancelled   = qset.filter(workstatus = 'CANCELLED').count()
        inprogress  = qset.filter(workstatus = 'INPROGRESS').count()
        closed      = qset.filter(workstatus = 'CLOSED').count()
        
        stats = [assigned, re_assigned, completed, inprogress,closed, cancelled]
        return stats, sum(stats)
    
    
    def get_events_for_calendar(self, request):
        from apps.work_order_management.models import Wom
        S,R = request.session, request.GET
        
        start_date = datetime.strptime(R['start'], "%Y-%m-%dT%H:%M:%S%z").date()
        end_date = datetime.strptime(R['end'], "%Y-%m-%dT%H:%M:%S%z").date()

        qset = self.annotate(
            start=Cast(F('plandatetime'), output_field=CharField()),
            end=Cast(F('expirydatetime'), output_field=CharField()),
            title = Case(When(workpermit = 'NOT_REQUIRED', then = F('description') ), default=F('qset__qsetname'), output_field=CharField()),
            color = Case(
                When(workstatus__exact = Wom.Workstatus.CANCELLED, then = V('#727272')),
                When(workstatus__exact = Wom.Workstatus.REASSIGNED, then= V( '#004679')),
                When(workstatus__exact = Wom.Workstatus.INPROGRESS, then= V( '#b87707')),
                When(workstatus__exact = Wom.Workstatus.CLOSED, then= V( '#13780e')),
                When(workstatus__exact = Wom.Workstatus.COMPLETED, then=V('#0d96ab')),
                When(workstatus__exact = Wom.Workstatus.ASSIGNED, then=V('#a14020')),
                output_field=CharField()
            )
        ).filter(
            cdtz__date__gte = start_date,
            cdtz__date__lte = end_date,
            bu_id = S['bu_id'],
            client_id = S['client_id']
        )
        
        if R['eventType'] == 'Work Orders':
            qset = qset.filter(workpermit = Wom.WorkPermitStatus.NOTNEED)
        else:
            qset = qset.filter(~Q(workpermit = Wom.WorkPermitStatus.NOTNEED))
        qset = qset.values('id', 'start', 'end', 'title','color')
        return qset or self.none()
        
            
            
            
        
            
    

class WOMDetailsManager(models.Manager):
    use_in_migrations = True
    def get_wo_details(self, womid):
        if womid in [None, 'None', '']: return self.none()
        qset = self.filter(
            wom_id = womid
        ).select_related('question').values('question__quesname', 'answertype', 'min', 'max', 'id',
            'options', 'alerton', 'ismandatory', 'seqno','answer', 'alerts').order_by('seqno')
        return qset or self.none()
    
    def getAttachmentJND(self, id):
        if qset := self.filter(id=id).values('uuid'):
            if atts := self.get_atts(qset[0]['uuid']):
                return atts or self.none()
        return self.none()
    
    def get_atts(self, uuid):
        from apps.activity.models import Attachment
        from django.conf import settings
        if atts := Attachment.objects.annotate(
            file = Concat(V(settings.MEDIA_URL, output_field=models.CharField()), F('filepath'),
                          V('/'), Cast('filename', output_field=models.CharField()))
            ).filter(owner = uuid).values(
            'filepath', 'filename', 'attachmenttype', 'datetime',  'id', 'file'
            ):return atts
        return self.none()
    
    
    