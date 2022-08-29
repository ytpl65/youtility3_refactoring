from django.db import models
from django.db.models.functions import Concat, Cast
from django.db.models import CharField, Value as V
from django.db.models import Q, F, Count, Case, When, 
from django.contrib.gis.db.models.functions import Distance 
from django.contrib.gis.db.models.functions import  AsWKT, AsGeoJSON
from datetime import datetime, timedelta, timezone
from apps.core import utils
import logging
logger = logging.getLogger('__main__')
log = logger

class QuestionSetManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'cuser_id', 'muser_id', 'ctzoffset', 'bu_id', 'client_id', 'cdtz', 'mdtz',
              'parent_id', 'qsetname', 'enable', 'assetincludes',
              'buincludes', 'seqno', 'url', 'type' , 'tenant_id']
    related = ['cuser', 'muser', 'client', 'bu', 'parent', 'asset', 'type']

    def get_template_list(self, bulist):
        bulist = bulist.split(',') if isinstance(bulist, str) else bulist
        ic(bulist)
        if bulist:
            if qset := self.select_related(
                *self.related).filter(buincludes__contains = bulist).values_list('id', flat = True):
                return tuple(qset)
                return ','.join(map(str, list(qset))).replace("'", '')
        return ""

    def get_qset_modified_after(self, mdtz, buid):
        qset = self.select_related(*self.related).filter(~Q(id = 1), mdtz__gte = mdtz, bu_id = buid, enable=True).values(*self.fields).order_by('-mdtz')
        qset = self.clean_fields(qset)
        return qset or None

    def get_configured_sitereporttemplates(self, related, fields, type):
        qset = self.select_related(
            *related).filter(enable = True, type=type, parent_id=1).values(*fields)
        qset = self.clean_fields(qset)
        return qset or self.none()
    
    def clean_fields(self, qset):
        for obj in qset:
            if(obj.get('assetincludes') or obj.get('buincludes')):
                obj['assetincludes'] = str(obj['assetincludes']).replace('[', '').replace(']', '').replace("'", "")
                obj['buincludes'] = str(obj['buincludes']).replace('[', '').replace(']', '').replace("'", "")
        return qset
    
    def get_qset_with_questionscount(self, parentid):
        qset = self.annotate(qcount=Count('questionsetbelonging')).filter(
            parent_id=parentid, enable=True
        ).values('id', 'qsetname', 'qcount', 'seqno')
        return qset or self.none()
    
    def handle_qsetpostdata(self, request):
        R, S = request.POST, request.session
        ic(R)
        postdata = {'parent_id':R['parent_id'], 'ctzoffset':R['ctzoffset'], 'seqno':R['seqno'],
                    'qsetname':R['qsetname'], 'cuser':request.user, 'muser':request.user,
                    'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                    'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                    'type':R['type'], 'client_id':S['client_id'], 'bu_id':S['bu_id']}
        if R['action'] == 'create':
            ID = self.create(**postdata).id
        
        elif R['action'] == 'edit':
            postdata.pop('cuser')
            postdata.pop('cdtz')
            updated = self.filter(pk=R['pk']).update(**postdata)
            if updated: ID = R['pk']
        
        else:
            self.filter(pk=R['pk']).update(enable=False)
            return self.none()
        
        return self.filter(pk=ID).annotate(
            qcount=Count('questionsetbelonging')).values(
                'id', 'qsetname', 'qcount', 'seqno') or self.none()
    
    def load_checklist(self):
        "Load Checklist for editor dropdown" 
        qset = self.annotate(
            text = F('qsetname')).filter(
                enable=True, type='CHECKLIST').values(
                    'id', 'text')
        if qset:
            for idx, q in enumerate(qset):
                q.update({'slno':idx+1})
        return qset or self.none()
    
    

    
    

    

class QuestionManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'quesname', 'options', 'min', 'max', 'alerton', 'answertype', 'muser_id', 'cdtz', 'mdtz',
            'client_id', 'isworkflow', 'enable', 'category_id', 'cuser_id', 'unit_id' , 'tenant_id', 'ctzoffset']
    related = ['client', 'muser', 'cuser', 'category', 'unit']

    def get_questions_modified_after(self, mdtz):
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        qset = self.select_related(*self.related).filter(~Q(id = 1), mdtz__gte = mdtzinput, enable=True).values(*self.fields).order_by('-mdtz')
        return qset or None

    def questions_of_client(self, request, RGet):
        search_term = RGet.get('search')
        qset = self.filter(client_id = request.session['client_id'])
        qset = qset.filter(quesname__icontains = search_term) if search_term else qset
        qset = qset.annotate(
                text = Concat(F('quesname'), V(" | "), F('answertype'))).values(
                    'id', 'text', 'answertype')
        return qset or self.none()

class JobneedManager(models.Manager):
    use_in_migrations = True

    def insert_report_parent(self, qsetid, record):
        return self.create(qset_id = qsetid, **record)

    def get_schedule_for_adhoc(self, pdt, peopleid, assetid, qsetid, buid):
        return self.raw("select * FROM get_schedule_for_adhoc(%s, %s, %s, %s, %s)", params=[pdt, buid, peopleid, assetid, qsetid])

    def get_jobneedmodifiedafter(self, mdtz, peopleid, siteid):
        mdtzinput = mdtz if (isinstance(mdtz, datetime)) else datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        return self.raw("select * from fn_getjobneedmodifiedafter('%s', %s, %s) as id", [mdtzinput, peopleid, siteid]) or self.none()

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
                WHERE jn.alerts = TRUE AND jn.id= %s
            )jn
            """, [pk])
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
            array_to_string(ARRAY(select email from people where people_id in (select unnest(string_to_array(qsb.alertmails_sendto, ', '))::bigint )), ', ') as alerttomails
            FROM nodes_cte as jobneed
        LEFT JOIN jobneeddetails as jnd ON jnd.jobneed_id = jobneedid
        LEFT JOIN question q ON jnd.question_id = q.id
        LEFT JOIN questionsetbelonging qsb ON qsb.question_id = q.id
        WHERE jobneed.parent_id <> -1  ORDER BY pseqno asc, jobdesc asc, pseqno, cseqno asc""", [pk])
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
            LEFT JOIN asset  ON jobneed.asset_id = asset.id
            LEFT JOIN people ON jobneed.performedby_id= people.id
            WHERE jobneed.other_info -> 'deviation' = true AND jobneed.parent_id != -1 AND jobneed.id = %s
            """, [pk]
        )
        return qset or self.none()

    def get_adhoctasks_listview(self, R, task = True):
        idf = 'TASK' if task else ('INTERNALTOUR', 'EXTERNALTOUR')
        qobjs, dir,  fields, length, start = utils.get_qobjs_dir_fields_start_length(R)
        qset = self.select_related(
                 'performedby', 'qset', 'asset').filter(
                    identifier__in = idf, jobtype='ADHOC', plandatetime__date__gte = R['pd1'],
                     plandatetime__date__lte = R['pd2']
             ).values(*fields).order_by(dir)
        total = qset.count()
        if qobjs:
            filteredqset = qset.filter(qobjs)
            fcount = filteredqset.count()
            filteredqset = filteredqset[start:start+length]
            return total, fcount, filteredqset
        qset = qset[start:start+length]
        return total, total, qset

    def get_last10days_jobneedtasks(self, related, fields, request):
        R = request.GET
        qobjs = self.select_related(*related).filter(
            bu_id = request.session['bu_id'],
            plandatetime__date__gte = R['pd1'],
            plandatetime__date__lte = R['pd2'],
            identifier = 'TASK'
        ).exclude(parent__jobdesc = 'NONE', jobdesc = 'NONE').values(*fields).order_by('-plandatetime')
        return qobjs or self.none()

    def get_assetmaintainance_list(self, request, related, fields):
        dt  = datetime.now(tz = timezone.utc) - timedelta(days = 90) #3months
        qset = self.filter(identifier='ASSETMAINTENANCE', plandatetime__gte = dt).select_related(
            *related).values(*fields)
        return qset or self.none()
    
    def get_adhoctour_listview(self, R):
        return self.get_adhoctasks_listview(R, task = False)

    def get_sitereportlist(self, request):
        "Transaction List View"
        from apps.onboarding.models import Bt
        # from apps.activity.models import QuestionSet, Attachment
        # from apps.activity.models import Attachment

        qset, R = self.none(), request.GET
        pbs = Bt.objects.get_people_bu_list(request.user)
        # tl = QuestionSet.objects.get_template_list(pbs)
        # if pbs and tl:
        #     qset  = self.annotate(
        #         buname = Case(When(~Q(othersite="") | ~Q(othersite='NONE'), then=Concat(V('otherlocation[ '), F('othersite'), V(']'))), default=Value('bu__buname')),
        #         distance = Distance('gpslocation', 'bu__gpslocation'),
        #         gps = AsWKT('gpslocation'),
        #         uuc = Cast('uuid', output_field=models.CharField())
        #     ).filter(plandatetime__gte = R['pd1'], plandatetime__lte = R['pd2'], bu_id__in = pbs, identifier = 'SITEREPORT', parent_id=1).values_list('uuc', flat=True)
        #     attobjs = Attachment.objects.get_attforuuids(qset.uuc)
        #     values(
        #         'id','plandatetime', 'jobdesc', 'people__peoplename', 'jobstatus', 'gps',
        #         'distance', 'remarks', 'buname', 'distance'
        #     )
        from apps.core.raw_queries import query
        qset = self.raw(query['sitereportlist'], params=[pbs, R['pd1'], R['pd2']])
        return qset

    def get_internaltourlist_jobneed(self, request, related, fields):
        R = request.GET
        qset = self.select_related(
                            *related).filter(
                                bu_id = request.session.get('bu_id', 1),
                                parent_id=1,
                                plandatetime__date__gte = R['pd1'],
                                plandatetime__date__lte = R['pd2'],
                                jobtype="SCHEDULE",
                                identifier='INTERNALTOUR'
                        ).exclude(
                        id=1
                        ).values(*fields).order_by('-plandatetime') 
        return qset or self.none()
    
    
    def get_externaltourlist_jobneed(self, request, related, fields):
        R = request.GET
        qset = self.select_related(
                            *related).filter(
                                bu_id = request.session.get('bu_id', 1),
                                parent_id=1,
                                plandatetime__date__gte = R['pd1'],
                                plandatetime__date__lte = R['pd2'],
                                jobtype="SCHEDULE",
                                identifier='EXTERNALTOUR'
                        ).exclude(
                        id=1
                        ).values(*fields).order_by('-plandatetime') 
        return qset or self.none()

    def get_tourdetails(self, R):
        qset = self.select_related(
            'parent', 'asset', 'qset').filter(parent_id = R['parent_id']).values(
                'asset__assetname', 'asset__id', 'qset__id',
                'qset__qsetname', 'plandatetime', 'expirydatetime',
                'gracetime', 'seqno', 'jobstatus', 'id'
            ).order_by('seqno')

        return qset or self.none()

    def handle_jobneedpostdata(self, request):
        S, R = request.session, request.GET
        pdt = datetime.strptime(R['plandatetime'], '%d-%b-%Y %H:%M')
        edt = datetime.strptime(R['expirydatetime'], '%d-%b-%Y %H:%M')
        postdata = {'parent_id':R['parent_id'], 'ctzoffset':R['ctzoffset'], 'seqno':R['seqno'],
                    'plandatetime':utils.getawaredatetime(pdt, R['ctzoffset']),
                    'expirydatetime':utils.getawaredatetime(edt, R['ctzoffset']),
                    'qset_id':R['qset_id'],  'asset_id':R['asset_id'], 'gracetime':R['gracetime'],
                    'cuser':request.user, 'muser':request.user,
                    'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                    'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                    'type':R['type'], 'client_id':S['client_id'], 'bu_id':S['bu_id']}
        
    
    
        

class AttachmentManager(models.Manager):
    use_in_migrations = True

    def get_people_pic(self, ownernameid, ownerid, db):
        ic(ownernameid, 'ATTACHMENT', ownerid)
        qset =  self.filter(
                ownername_id = ownernameid,
                attachmenttype = 'ATTACHMENT',
                owner = ownerid
                ).annotate(
            default_img_path = Concat(F('filepath'), V('/'), F('filename'),
                                    output_field = CharField())).order_by('-mdtz').using(db)
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
            owner = id
            ).using(db)
        return qset or self.none()

    def get_att_given_owner(self, owneruuid):
        "return attachments of given jobneed uuid"
        qset = self.filter(
            attachmenttype__in = ['ATTACHMENT', 'SIGN'], owner = owneruuid).order_by('filepath').values(
                'id', 'filepath', 'filename'
            )
        return qset or self.none()
    
    
    def create_att_record(self, request, filepath, filename):
        R, S = request.POST, request.session
        ic(R)
        from apps.onboarding.models import TypeAssist
        ta = TypeAssist.objects.filter(taname = R['ownername'])
        PostData = {'filepath':filepath, 'filename':filename, 'owner':R['ownerid'], 'bu_id':S['bu_id'],
                'attachmenttype':R['attachmenttype'], 'ownername_id':ta[0].id,
                'cuser':request.user, 'muser':request.user, 'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset'])}
        try:
            ic("creating record")
            qset = self.create(**PostData)
            ic(dir(qset.filename))
            ic(qset.id)
        except Exception:
            log.error("Attachment record creation failed...", exc_info=True)
            return {'error':'Upload attachment Failed'}
        return {'filepath':qset.filepath, 'filename':qset.filename.name, 'id':qset.id} if qset else self.none()

    def get_attforuuids(self, uuids):
        return self.filter(owner__in = uuids) or self.none()
        
        

class AssetManager(models.Manager):
    use_in_migrations = True
    related = ['category', 'client', 'cuser', 'muser', 'parent', 'subcategory', 'tenant', 'type', 'unit', 'brand', 'bu', 'serv_prov']
    fields = ['id', 'cdtz', 'mdtz', 'ctzoffset', 'assetcode', 'assetname', 'enable', 'iscritical', 'gpslocation', 'identifier', 'runningstatus', 'capacity', 'brand_id', 'bu_id',
              'category_id', 'client_id', 'cuser_id', 'muser_id', 'parent_id', 'servprov_id', 'subcategory_id', 'tenant_id', 'type_id', 'unit_id']

    def get_assetdetails(self, mdtz, site_id):
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        return self.filter(
            ~Q(id = 1),
            ~Q(identifier = 'NEA'),
            ~Q(runningstatus = 'SCRAPPED'),
            mdtz__gte = mdtzinput,
            bu_id= site_id,
        ).select_related(
            *self.related
        ).values(*self.fields) or self.none()

    def get_schedule_task_for_adhoc(self, params):
        qset = self.raw("select * from fn_get_schedule_for_adhoc")
        
    def get_peoplenearasset(self, request):
        "List View"
        qset = self.annotate(gps = AsWKT('gpslocation')).filter(
            identifier__in = ['ASSET', 'SMARTPLACE', 'CHECKPOINT'],
            bu_id = request.session['bu_id']
        ).values('id', 'assetcode', 'assetname', 'identifier', 'gps')
        return qset or self.none()
    
    


class JobneedDetailsManager(models.Manager):
    use_in_migrations = True
    related = ['question', 'jobneed', 'cuser', 'muser']
    fields = ['id', 'uuid', 'seqno', 'answertype', 'answer', 'isavpt', 'options', 'ctzoffset', 'ismandatory',
              'cdtz', 'mdtz',           
              'min', 'max', 'alerton', 'question_id', 'jobneed_id', 'alerts', 'cuser_id', 'muser_id', 'tenant_id']

    def get_jndmodifiedafter(self, mdtz,jobneedid):
        if jobneedid:
            jobneedids = jobneedid.split(',')
            ic(jobneedids)
            qset = self.select_related(
                *self.related).filter(
                ~Q(id = 1), Q(mdtz = None) | Q( mdtz__gte = mdtz),
                jobneed_id__in = jobneedids,
               ).values(
                    *self.fields)
            return qset or self.none()
        return self.none()

    def update_ans_muser(self, answer, peopleid, mdtz, jnid):
        _mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        return self.filter(jobneed_id = jnid).update(muser_id = peopleid, answer = answer, mdtz = _mdtz)

    def get_jnd_observation(self, id):
        qset = self.select_related(
            'jobneed', 'question').filter(
                jobneed_id = id).order_by('seqno')
        return qset or self.none()

    def get_jndofjobneed(self, R):
        qset = self.filter(jobneed_id = R['jobneedid']).select_related(
            'jobneed', 'question'
        ).annotate(quesname = F('question__quesname')).values(
            'quesname', 'answertype', 'answer', 'min', 'max',
            'alerton', 'ismandatory', 'options', 'question_id','pk',
            'ctzoffset','seqno'
        )
        return qset or self.none()


class QsetBlngManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'seqno', 'answertype',  'isavpt', 'options', 'ctzoffset', 'ismandatory',
              'min', 'max', 'alerton', 'client_id', 'bu_id',  'question_id', 
              'qset_id', 'cuser_id', 'muser_id', 'cdtz', 'mdtz', 'alertmails_sendto', 'tenant_id']
    related = ['client', 'bu',  'question', 
              'qset', 'cuser', 'muser']

    def get_modified_after(self ,mdtz, buid):
        qset = self.select_related(
            *self.related).filter(
                ~Q(id = 1), mdtz__gte = mdtz, bu_id = buid).values(
                    *self.fields
                )
        return qset or self.none()
    
    def handle_questionpostdata(self, request):
        R, S, Id, r = request.POST, request.session, None, {}
        ic(R)
        r['ismandatory'] = R['ismandatory'] == '1'
        r['options'] = R['options'].replace('"', '').replace('[', '').replace(']', '')
        r['min'] = 0.0 if R['min'] == "" else R['min']
        r['max'] = 0.0 if R['max'] == "" else R['max']
        
        if R['answertype'] in ['DROPDOWN', 'CHECKBOX']:
            r['alerton'] = R['alerton'].replace('"', '').replace('[', '').replace(']', '')
        
        elif R['answertype'] == 'NUMERIC':
            r['alerton'] = f"<{R['alertbelow']}, >{R['alertabove']}"
        
        PostData = {'qset_id':R['parent_id'], 'answertype':R['answertype'], 'min':r.get('min', '0.0'), 'max':r.get('max', '0.0'),
                'alerton':r.get('alerton'), 'ismandatory':r['ismandatory'], 'question_id': R['question_id'],
                'options':r.get('options'), 'seqno':R['seqno'], 'client_id':S['client_id'], 'bu_id':S['bu_id'],
                'cuser':request.user, 'muser':request.user, 'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset'])}
        
        if R['action'] == 'create':
            ID = self.create(**PostData).id
        
        elif R['action'] == 'edit':
            PostData.pop('cuser')
            PostData.pop('mdtz')
            updated = self.filter(pk=R['pk']).update(**PostData)
            ic(updated)
            if updated: ID = R['pk']
        else:
            self.filter(pk=R['pk']).delete()
            return self.none()
        
        return self.filter(id=ID).annotate(quesname=F('question__quesname')
        ).values('pk', 'seqno', 'quesname', 'answertype', 'min', 'question_id', 'ctzoffset',
                 'max', 'options', 'alerton', 'ismandatory') or self.none()
        
    
    def get_questions_of_qset(self, R):
        qset = self.annotate(quesname = F('question__quesname')).filter(
            qset_id = R['qset_id']).select_related('question').values(
                'pk', 'quesname', 'answertype', 'min', 'max','question_id',
                'options', 'alerton', 'ismandatory', 'seqno', 'ctzoffset')
        return qset or self.none()
    
    
    

class TicketManager(models.Manager):
    use_in_migrations = True


class JobManager(models.Manager):
    use_in_migrations: True

    def getgeofence(self, peopleid, siteid):
        qset = self.filter(
            people_id = peopleid, bu_id = siteid, identifier='GEOFENCE').select_related(
                'geofence', 
            ).annotate(
                geofencejson = AsGeoJSON('geofence')).values(
                    'geofence__id', 'geofence__gfcode', 'people_id', 'fromdate',
                    'geofence__gfname', 'geofencejson', 'enable', 'uptodate', 'identifier',
                    'starttime', 'endtime', 'bu_id', 'asset_id')
        return qset or self.none()

    def get_scheduled_internal_tours(self, related, fields):
        qset = self.select_related(*related).filter(
            parent__jobname='NONE', parent_id = 1, identifier__exact='INTERNALTOUR'
        ).values(*fields).order_by('-cdtz')
        return qset or self.none()

    def get_checkpoints_for_externaltour(self, job):
        qset = self.select_related(
            'identifier', 'butype', 'parent').filter(
                parent_id = job.bu_id).values(
                'buname', 'id', 'bucode', 'gpslocation',
            )
        return qset or self.none()

    def get_scheduled_external_tours(self, related, fields):
        qset = self.select_related(*related).filter(
            parent__jobname='NONE', parent_id = 1, identifier__exact='EXTERNALTOUR'
        ).values(*fields).order_by('-cdtz')
        return qset or self.none()
    
    def get_listview_objs_schdexttour(self, request):
        qset = self.annotate(
            assignedto = Case(
                When(pgroup_id=1, then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(people_id=1, then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
            ),
            sitegrpname = F('sgroup__groupname'),
            israndomized = F('other_info__is_randomized'),
            tourfrequency = F('other_info__tour_frequency'),
            breaktime = F('other_info__breaktime'),
            deviation = F('other_info__deviation')
        ).filter(
            ~Q(jobname='NONE'), parent_id=1, identifier='EXTERNALTOUR'
        ).select_related('pgroup', 'sgroup', 'people').values(
            'assignedto', 'sitegrpname', 'israndomized', 'tourfrequency',
            'breaktime', 'deviation', 'fromdate', 'uptodate', 'gracetime',
            'expirytime', 'planduration','jobname', 'id'
        ).order_by('-mdtz')
        ic(utils.printsql(qset))
        return qset or self.none()

    def get_sitecheckpoints_exttour(self, job):
        ic(job)
        qset = self.annotate(
            qsetid = F('qset_id'), assetid = F('asset_id'),
            jobid = F('id'), gpslocation = AsGeoJSON('bu__gpslocation'),
            buid = F('bu_id'), buname=F('bu__buname'),
            breaktime = F('other_info__breaktime'),
            distance=F('other_info__distance'),
            duration = Value(None, output_field=models.CharField(null=True)),
            qsetname=F('qset__qsetname')
            
        ).filter(parent_id=job['id']).select_related('asset', 'qset',).values(
            'id',
            'breaktime', 'distance', 'starttime', 'expirytime',
            'qsetid', 'jobid', 'assetid', 'seqno', 'jobdesc',
            'buname', 'buid', 'gpslocation', 'endtime', 'duration',
            'qsetname'
        ).order_by('seqno')
        return qset or self.none()



class DELManager(models.Manager):
    use_in_migrations = True
    
    def get_mobileuserlog(self, request):
        qobjs, dir,  fields, length, start = utils.get_qobjs_dir_fields_start_length(request.GET)
        dt  = datetime.now(tz = timezone.utc) - timedelta(days = 10)
        qset = self.filter(
            bu_id = request.session['bu_id'],
            cdtz__gte = dt
        ).select_related('people', 'bu').values(*fields).order_by(dir)
        total = qset.count()
        if qobjs:
            filteredqset = qset.filter(qobjs)
            fcount = filteredqset.count()
            filteredqset = filteredqset[start:start+length]
            return total, fcount, filteredqset
        qset = qset[start:start+length]
        return total, total, qset
            
            
class WorkpermitManager(models.Manager):
    use_in_migrations = True
    
    def get_workpermitlist(self, request):
        from apps.core.raw_queries import query
        qset = self.raw(query['workpermitlist'], [request.session['bu_id']])
        return qset or self.none()