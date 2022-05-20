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
              'parent_id', 'qsetname', 'enable', 'assetincludes',
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
        
    
    def get_jobneed_observation(self, pk):
        qset = self.select_related('people', 'asset', 'bu', 'identifier').filter(
            alerts = True, id = pk
        )
        return qset or self.none()
    
    
    def get_jobneed_for_report(self,pk):
        qset = self.raw(
            """
            SELECT jn.identifier, jn.peoplecode, jn.peoplename, jn.jobdesc, jn.plandatetime,
                jn.ctzoffset, jn.buname, jn.people_id, jn.pgroup_id, jn.bu_id, jn.cuser_id, jn.muser_id,
                to_char(jn.cplandatetime, 'DD-Mon-YYYY HH24:MI:SS') AS cplandatetime
            FROM(
                SELECT ta.taname AS idenfiername, p.peoplecode, p.peoplename, jn.jobdesc, jn.plandatetime, jn.ctzoffset,
                    jn.plandatetime + INTERVAL '1 min' * jn.ctzoffset AS cplandatetime,
                    CASE WHEN (jn.othersite!='' or upper(jn.othersite)!='NONE')
                    THEN 'other location [ ' ||jn.othersite||' ]' ELSE bu.buname END AS buname,
                    jn.people_id, jn.pgroup_id, jn.bu_id, jn.cuser_id, jn.muser_id
                FROM jobneed jn
                INNER JOIN bu            ON jn.bu_id=     bu.id
                INNER JOIN people p      ON jn.people_id= p.id
                WHERE jn.alerts=TRUE AND jn.id= %s
            )jn
            """, pk)
        return qset or self.none()
    
    def get_hdata_for_report(self, pk):
        qset = self.raw("""WITH RECURSIVE nodes_cte(jobneedid, parent_id, jobdesc, people_id, qset_id, plandatetime, cdtz, depth, path, top_parent_id, pseqno, buid) AS
        (
            SELECT jobneed.id as jobneedid, jobneed.parent_id, jobdesc, people_id, qset_id, plandatetime, jobneed.cdtz, 1::INT AS depth,
                qset_id::TEXT AS path, jobneed.id as top_parent_id, seqno as pseqno, jobneed.bu_id
            FROM jobneed
            WHERE jobneed.parent_id=-1 AND jobneed.id <>-1 AND jobneed.id= '%s' AND jobneed.identifier = 'SITEREPORT'
            UNION ALL
            SELECT c.id as jobneedid, c.parent_id, c.jobdesc, c.people_id, c.qset_id, c.plandatetime, c.cdtz, p.depth + 1 AS depth,
                (p.path || '->' || c.id::TEXT) as path, c.parent_id as top_parent_id, seqno as pseqno, c.bu_id
            FROM nodes_cte AS p, jobneed AS c
            WHERE c.parent_id = p.jobneedid AND c.identifier = 'SITEREPORT'
        )SELECT DISTINCT jobneed.jobdesc, jobneed.pseqno, jnd.seqno as cseqno, jnd.question_id, jnd.answertype, jnd.min, jnd.max, jnd.options, jnd.answer, jnd.alerton,
            jnd.ismandatory, jnd.alerts, q.quesname, jnd.answertype as questiontype, qsb.alertmails_sendto,
            array_to_string(ARRAY(select email from people where people_id in (select unnest(string_to_array(qsb.alertmails_sendto, ','))::bigint )), ', ') as alerttomails
            FROM nodes_cte as jobneed
        LEFT JOIN jobneeddetails as jnd ON jnd.jobneed_id=jobneedid
        LEFT JOIN question q ON jnd.question_id=q.id
        LEFT JOIN questionsetbelonging qsb ON qsb.question_id=q.id
        WHERE jobneed.parent_id <> -1  ORDER BY pseqno asc, jobdesc asc, pseqno, cseqno asc""", pk)
        return qset or self.none()
        
    def get_deviation_jn(self, pk):
        qset = self.raw(
            """
            SELECT jobneed.jobdesc,
            to_char(jobneed.plandatetime + INTERVAL '1 minute' * jobneed.ctzoffset, 'DD-Mon-YYYY HH24:MI:SS') AS plandatetime,
            to_char(jobneed.starttime + INTERVAL '1 minute' * jobneed.ctzoffset, 'DD-Mon-YYYY HH24:MI:SS') AS starttime,
            jobneed.bu_id, jobneed.cuser_id, jobneed.muser_id, jobneed.pgroup_id,
            asset.assetname, people.id, people.peoplecode, people.peoplename, people.mobno
            FROM jobneed
            LEFT JOIN asset  ON jobneed.asset_id=asset.id
            LEFT JOIN people ON jobneed.performedby_id= people.id
            WHERE jobneed.other_info -> 'deviation' = true AND jobneed.parent_id != -1 AND jobneed.id = %s
            """, params=pk
        )
        return qset or self.none()
    
    



class AttachmentManager(models.Manager):
    use_in_migrations = True
    
    def get_people_pic(self, ownernameid, ownerid, db):
        ic(ownernameid, 'ATTACHMENT', ownerid)
        qset =  self.filter(
                ownername_id = ownernameid,
                attachmenttype = 'ATTACHMENT',
                owner = ownerid
                ).annotate(
            default_img_path=Concat(F('filepath'), V('/'), F('filename'),
                                    output_field=CharField())).order_by('-cdtz').using(db)
        ic(qset)
        return qset[0] or self.none()
            
        
    def get_attachment_record(self, id, db):
        qset =  self.filter(
            ~Q(filename__endswith = '.csv'),
            ~Q(filename__endswith = '.mp4'),
            ~Q(filename__endswith = '.txt'),
            ~Q(filename__endswith = '.3gp'),
            ownername__tacode = 'PEOPLEEVENTLOG',
            attachmenttype = 'ATTACHMENT', 
            id = id
            ).using(db)
        print("qset values@@@@@@@@@@@@@@@@", qset)
        return qset or self.none()
    
    
class AssetManager(models.Manager):
    use_in_migrations = True
    related = ['category', 'client', 'cuser', 'muser', 'parent', 'subcategory', 'tenant', 'type', 'unit', 'brand', 'bu', 'serv_prov']
    fields = ['id','cdtz','mdtz','ctzoffset','assetcode','assetname','enable','iscritical','gpslocation','identifier','runningstatus','capacity','brand_id','bu_id',
              'category_id','client_id','cuser_id','muser_id','parent_id','servprov_id','subcategory_id','tenant_id','type_id','unit_id']
    
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

    
    def get_jnd_observation(self, id):
        qset = self.select_related(
            'jobneed', 'question').filter(
                jobneed_id = id).order_by('seqno')
        return qset or self.none()


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
   
