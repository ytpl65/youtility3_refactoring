from django.db import models
from django.db.models.functions import Concat, Cast
from django.db.models import CharField, Value as V
from django.db.models import Q, F, Count, Case, When
from datetime import datetime, timedelta
import logging
import json
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
        return qset or self.none()
    
    def get_workpermitlist(self, request):
        R, S = request.GET, request.session
        P = json.loads(R.get('params', "{}"))
        
        qobjs = self.filter(
            ~Q(workpermit__in =  ['NOT_REQUIRED', 'NOTREQUIRED']),
            parent_id = 1,
            client_id = S['client_id'],
            cdtz__date__gte = P['from'],
            cdtz__date__lte = P['to'],
        ).values('cdtz', 'other_data__wp_seqno', 'qset__qsetname', 'workpermit', 'workstatus', 'id')
        return qobjs or self.none()
         
            
    

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
    
    
    