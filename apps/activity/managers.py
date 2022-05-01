from mmap import MADV_RANDOM
import re
from django.db import models
from django.db.models.functions import Concat
from django.db.models import CharField, Value as V
from django.db.models import Q, F
from datetime import date, datetime, timedelta

from apps.peoples.models import People
class QuestionSetManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'cuser_id', 'muser_id', 'ctzoffset', 'bu_id', 'client_id', 'cdtz', 'mdtz',
              'parent_id', 'asset_id', 'qsetname', 'enable', 'assetincludes',
              'buincludes', 'seqno', 'url', 'type' , 'tenant_id']
    related = ['cuser', 'muser', 'client', 'bu', 'parent', 'asset', 'type']
    
    def get_template_list(self, bulist):
        if bulist:
            if qset := self.select_related(
                *self.related).filter(bu_id__in=bulist).values_list(*self.fields, flat=True):
                return ','.join(list(qset))
        return ""
    
    def get_qset_modified_after(self, mdtz, buid):
        qset = self.select_related(*self.related).filter(~Q(id=1), mdtz__gte = mdtz, bu_id = buid).values(*self.fields)
        return qset or None
        
        
class QuestionManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'quesname', 'options', 'min', 'max', 'alerton', 'answertype', 'muser_id', 'cdtz', 'mdtz',
            'client_id', 'isworkflow', 'enable', 'category_id', 'cuser_id', 'unit_id' , 'tenant_id', 'ctzoffset']
    related = ['client', 'muser', 'cuser', 'category', 'unit']
    
    def get_questions_modified_after(self, mdtz):
        
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        qset = self.select_related(*self.related).filter(~Q(id=1), mdtz__gte = mdtzinput).values(*self.fields)
        return qset or None
    
    
class JobneedManager(models.Manager):
    use_in_migrations = True
    
    def insert_report_parent(self, qsetid, record):
        return self.create(qset_id = qsetid, **record)
    
    def get_schedule_for_adhoc(self, pdt, peopleid, assetid, qsetid, buid):
        return self.raw(f"select * FROM get_schedule_for_adhoc({pdt}, {buid}, {peopleid}, {assetid}, {qsetid})")

    def get_jobneedmodifiedafter(self, mdtz, peopleid, siteid):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        return self.raw(f"select * from fn_getjobneedmodifiedafter('{mdtzinput}', {peopleid}, {siteid}) as id") or self.none()
        
    
    

class AttachmentManager(models.Manager):
    use_in_migrations = True
    
    def get_people_pic(self, ownernameid, ownerid):
        
        qset =  self.filter(
                ownername_id = ownernameid,
                attachmenttype = 'ATTACHMENT',
                owner = ownerid
                ).annotate(
            default_img_path=Concat(F('filepath'), V('/'), F('filename'),
                                    output_field=CharField())).order_by('-cdtz')
        return qset or self.none()
            
        
    def get_attachment_record(self, id):
        return self.filter(
            ~Q(filename__endswith = '.csv'),
            ~Q(filename__endswith = '.mp4'),
            ~Q(filename__endswith = '.txt'),
            ~Q(filename__endswith = '.3gp'),
            ownername__tacode = 'PEOPLEEVENTLOG',
            attachmenttype = 'ATTACHMENT', 
            id = id
            )[0] or self.none()
    
    
class AssetManager(models.Manager):
    use_in_migrations = True
    related = ['category', 'client', 'cuser', 'muser', 'parent', 'subcategory', 'tenant', 'type', 'unit', 'brand', 'bu', 'serv_prov']
    fields = ['id','cdtz','mdtz','ctzoffset','assetcode','assetname','enable','iscritical','gpslocation','identifier','runningstatus','capacity','brand_id','bu_id',
              'category_id','client_id','cuser_id','muser_id','parent_id','serv_prov_id','subcategory_id','tenant_id','type_id','unit_id']
    
    def get_assetdetails(self, mdtz, site_id):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        return self.filter(
            ~Q(id=1),
            ~Q(identifier = 'NEA'),
            ~Q(runningstatus = 'SCRAPPED'),
            mdtz__gte = mdtzinput,
            bu_id= site_id,
        ).select_related(
            *self.related
        ).values(*self.fields) or self.none()
    
    def get_asset_vs_qset(self):
        pass
    
    
class JobneedDetailsManager(models.Manager):
    use_in_migrations=True
    related = ['question', 'jobneed', 'cuser', 'muser']
    fields = ['id', 'uuid', 'seqno', 'answertype', 'answer', 'isavpt', 'options', 'ctzoffset', 'ismandatory',
              'cdtz', 'mdtz',           
              'min', 'max', 'alerton', 'question_id', 'jobneed_id', 'alerts', 'cuser_id', 'muser_id', 'tenant_id']
    
    def get_jndmodifiedafter(self, mdtz,jobneedid):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        if jobneedid:
            jobneedids = jobneedid.split(', ')
            ic(jobneedids)
            qset = self.select_related(
                *self.related).filter(
                ~Q(id=1), Q(mdtz = None) | Q( mdtz__gte = mdtzinput),
                jobneed_id__in = jobneedids,
               ).values(
                    *self.fields)
            return qset or self.none()
        return self.none()
    
    def update_ans_muser(self, answer, peopleid, mdtz, jnid):
        _mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        return self.filter(jobneed_id=jnid).update(muser_id=peopleid, answer=answer, mdtz=_mdtz)


class QsetBlngManager(models.Manager):
    use_in_migrations=True
    fields = ['id', 'seqno', 'answertype',  'isavpt', 'options', 'ctzoffset','ismandatory',
              'min', 'max', 'alerton', 'client_id', 'bu_id',  'question_id', 
              'qset_id', 'cuser_id', 'muser_id', 'cdtz', 'mdtz', 'alertmails_sendto', 'tenant_id']
    related = [ 'client', 'bu',  'question', 
              'qset', 'cuser', 'muser', ]
    
    
    def get_modified_after(self ,mdtz, buid):
        qset = self.select_related(
            *self.related).filter(
                ~Q(id=1), mdtz__gte = mdtz, bu_id = buid).values(
                    *self.fields
                )
        return qset or self.none()
    
    
class TicketManager(models.Manager):
    use_in_migrations = True
   
