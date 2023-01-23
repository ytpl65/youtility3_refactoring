from django.db import models
from django.db.models.functions import Concat, Cast
from django.db.models import CharField, Value as V, Subquery, OuterRef
from django.db.models import Q, F, Count, Case, When
from django.contrib.gis.db.models.functions import  AsWKT, AsGeoJSON
from datetime import datetime, timedelta, timezone
from pyparsing import identbodychars
from apps.core import utils
from itertools import chain
import apps.peoples.models as pm
import logging
logger = logging.getLogger('__main__')
from django.conf import settings
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
        qset = self.select_related(*self.related).filter(Q(id = 1) | Q(mdtz__gte = mdtz) &  Q(bu_id = buid) & Q(enable=True)).values(*self.fields).order_by('-mdtz')
        qset = self.clean_fields(qset)
        return qset or None

    def get_configured_sitereporttemplates(self, request, related, fields, type):
        S = request.session
        qset = self.select_related(
            *related).filter(enable = True, type=type, client_id = S['client_id'], bu_id__in = S['assignedsites'], parent_id=1).values(*fields)
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
    
    def questionset_listview(self, request, fields, related):
        R, S = request.GET, request.session
        
        qset = self.filter(
            ~Q(qsetname='NONE'),
            type='QUESTIONSET',
            bu_id__in = S['assignedsites'],
            client_id = S['client_id']
        ).select_related(*related).values(*fields)
        return qset or self.none()

    def checklist_listview(self, request, fields, related):
        R, S = request.GET, request.session
        
        qset = self.filter(
            ~Q(qsetname='NONE'),
            type='CHECKLIST',
            bu_id__in = S['assignedsites'],
            client_id = S['client_id']
        ).select_related(*related).values(*fields)
        return qset or self.none()
    
    def get_proper_checklist_for_scheduling(self,request, types):
        S = request.session
        
        qset = self.filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            type__in = types,
        ).select_related('bu' ,'client', 'parent').exclude(
            questionsetbelonging=None
        )
        return qset or self.none()
        
    
    

    
    

    

class QuestionManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'quesname', 'options', 'min', 'max', 'alerton', 'answertype', 'muser_id', 'cdtz', 'mdtz',
            'client_id', 'isworkflow', 'enable', 'category_id', 'cuser_id', 'unit_id' , 'tenant_id', 'ctzoffset']
    related = ['client', 'muser', 'cuser', 'category', 'unit']

    def get_questions_modified_after(self, mdtz):
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        qset = self.select_related(*self.related).filter( mdtz__gte = mdtzinput, enable=True).values(*self.fields).order_by('-mdtz')
        return qset or None

    def questions_of_client(self, request, RGet):
        search_term = RGet.get('search')
        qset = self.filter(client_id = request.session['client_id'])
        qset = qset.filter(quesname__icontains = search_term) if search_term else qset
        qset = qset.annotate(
                text = Concat(F('quesname'), V(" | "), F('answertype'))).values(
                    'id', 'text', 'answertype')
        return qset or self.none()
    
    def questions_listview(self, request, fields, related):
        S = request.session
        qset = self.select_related(
                *related).filter(
                enable = True,
                client_id = S['client_id'],
            ).values(*fields)
        return qset or self.none()
    
    def get_questiondetails(self, questionid):
        qset = self.filter(pk = questionid).values(
            'id',  'answertype', 'isavpt', 'options', 'min',
             'max', 'alerton', 'avpttype')
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
        qobjs = self.select_related(*related).annotate(
            assignedto = Case(
                When(Q(pgroup_id=1) | Q(pgroup_id__isnull =  True), then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(Q(people_id=1) | Q(people_id__isnull =  True), then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
                ),
            ).filter(
            bu_id__in = request.session['assignedsites'],
            plandatetime__date__gte = R['pd1'],
            plandatetime__date__lte = R['pd2'],
            identifier = 'TASK'
        ).exclude(parent__jobdesc = 'NONE', jobdesc = 'NONE').values(*fields).order_by('-plandatetime')
        return qobjs or self.none()

    def get_assetmaintainance_list(self, request, related, fields):
        S = request.session
        dt  = datetime.now(tz = timezone.utc) - timedelta(days = 90) #3months
        qset = self.filter(identifier='ASSETMAINTENANCE',
                           plandatetime__gte = dt,
                           bu_id__in = S['assignedsites'],
                           client_id = S['client_id']).select_related(
            *related).values(*fields)
        return qset or self.none()
    
    def get_adhoctour_listview(self, R):
        return self.get_adhoctasks_listview(R, task = False)

    def get_sitereportlist(self, request):
        "Transaction List View"
        from apps.peoples.models import Pgbelonging
        from apps.activity.models import Attachment
        from django.contrib.gis.db.models.functions import Distance

        qset, R = self.none(), request.GET
        S = request.session
        pbs = Pgbelonging.objects.get_assigned_sites_to_people(request.user.id)
        
        #att count subquery
        attachment_count = Subquery(
            Attachment.objects.filter(
                owner = Cast(OuterRef('uuid'), output_field=models.CharField())
            ).annotate(
                att=Count('owner')
            ).values('att')[:1]
        )
        
        #outer query
        qset = self.filter(
                    parent_id = 1,
                    plandatetime__date__gte=R['pd1'],
                    plandatetime__date__lte=R['pd2'],
                    identifier='SITEREPORT',
                    bu_id__in = S['assignedsites'],
                    client_id = S['client_id']
                ).annotate(
                    buname=Case(
                        When(
                            Q(Q(othersite__isnull=True) | Q(othersite = "") | Q(othersite = 'NONE')),
                            then=F('bu__buname')
                        ),
                        default=Concat(
                            V('other location ['),
                            F('othersite'),
                            V(']')
                        )
                    ),
                    gps = AsGeoJSON('gpslocation'),
                    distance = Distance('gpslocation', 'bu__gpslocation')
                ).values('id', 'plandatetime', 'jobdesc', 'people__peoplename', 'starttime', 'endtime', 
                         'buname', 'jobstatus', 'gps', 'distance', 'remarks').order_by('-plandatetime').distinct()
        return qset

        
        
    
    def get_incidentreportlist(self, request):
        "Transaction List View"
        from apps.peoples.models import Pgbelonging
        from apps.activity.models import Attachment
        R = request.GET
        sites = Pgbelonging.objects.get_assigned_sites_to_people(request.user.id)
        buids = sites.values_list('buid', flat=True)
        qset = self.annotate(
            buname = Case(
                When(Q(Q(othersite__isnull=True) | Q(othersite = "") | Q(othersite = 'NONE')), then=F('bu__buname')),
                default= F('othersite')
            ),
            gps = AsGeoJSON('gpslocation'),
            uuidtext = Cast('uuid', output_field=models.CharField())
        ).filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            plandatetime__date__gte = R['pd1'], plandatetime__date__lte = R['pd2'], identifier='INCIDENTREPORT', bu_id__in = buids).values(
            'id', 'plandatetime', 'jobdesc', 'bu_id', 'buname', 'gps', 'jobstatus', 'performedby__peoplename', 'uuidtext', 'remarks', 'geojson__gpslocation',
            'identifier', 'parent_id'
        )
        atts = Attachment.objects.filter(
            owner__in = qset.values_list('uuidtext', flat=True)
        ).values('filepath', 'filename')
        return qset, atts or self.none()        

    def get_internaltourlist_jobneed(self, request, related, fields):
        R = request.GET
        qset = self.annotate(
            assignedto = Case(
                When(Q(pgroup_id=1) | Q(pgroup_id__isnull =  True), then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(Q(people_id=1) | Q(people_id__isnull =  True), then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
                ),
            ).select_related(
                            *related).filter(
                                bu_id__in = request.session['assignedsites'],
                                client_id = request.session['client_id'],
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
        fields = ['id', 'plandatetime', 'expirydatetime', 'performedby__peoplename', 'jobstatus',
                  'jobdesc', 'people__peoplename', 'pgroup__groupname', 'gracetime', 'ctzoffset', 'assignedto']
        R = request.GET
        qset = self.annotate(
            assignedto = Case(
                When(Q(pgroup_id=1) | Q(pgroup_id__isnull =  True), then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(Q(people_id=1) | Q(people_id__isnull =  True), then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
                ),
            ).select_related(
                            *related).filter(
                                bu_id__in = request.session['assignedsites'],
                                parent_id=1,
                                plandatetime__date__gte = R['pd1'],
                                plandatetime__date__lte = R['pd2'],
                                jobtype="SCHEDULE",
                                identifier='EXTERNALTOUR',
                                job__enable=True
                        ).exclude(
                        id=1
                        ).values(*fields).order_by('-cdtz') 
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
        

    
    def get_ext_checkpoints_jobneed(self, request, related, fields):
        fields+=['distance', 'duration', 'bu__gpslocation']
        ic(fields)
        qset  = self.annotate(distance=F('other_info__distance'),
                              bu__gpslocation = AsGeoJSON('bu__gpslocation'),
            duration = V(None, output_field=models.CharField(null=True))).select_related(*related).filter(
            parent_id = request.GET['parent_id'],
            identifier = 'EXTERNALTOUR',
            job__enable=True
        ).order_by('seqno').values(*fields)
        return qset or self.none()
    
    def getAttachmentJobneed(self, id):
        if qset := self.filter(id=id).values('uuid'):
            if atts := self.get_atts(qset[0]['uuid']):
                return atts or self.none()
        return self.none()

    
    def get_atts(self, uuid):
        from apps.activity.models import Attachment
        if atts := Attachment.objects.annotate(
            file = Concat(V(settings.MEDIA_URL, output_field=models.CharField()),
                          F('filepath'),
                          V('/'), Cast('filename', output_field=models.CharField())),
            location = AsGeoJSON('gpslocation')
            ).filter(owner = uuid).values(
            'filepath', 'filename', 'attachmenttype', 'datetime', 'location', 'id', 'file'
            ):return atts
        return self.none()

    def get_ir_count_forcard(self, request):
        R, S = request.GET, request.session
        pd1 = R.get('from', datetime.now().date())
        pd2 = R.get('upto', datetime.now().date())
        return self.filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in = S['assignedsites'],
            identifier = 'INCIDENTREPORT',
            plandatetime__date__gte = pd1,
            plandatetime__date__lte = pd2,
            client_id = S['client_id'],
        ).count() or 0
    
    def get_schdroutes_count_forcard(self, request):
        R, S = request.GET, request.session
        pd1 = R.get('from', datetime.now().date())
        pd2 = R.get('upto', datetime.now().date())
        return self.filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            plandatetime__date__gte = pd1,
            plandatetime__date__lte = pd2,
            identifier='EXTERNALTOUR'
        ).count() or 0
    
    def get_ppm_listview(self, request, fields, related):
        S, R = request.session, request.GET
        pd1 = R.get('pd1', datetime.now() - timedelta(days=7))
        pd2 = R.get('pd2', datetime.now())
        qset = self.annotate(
            assignedto = Case(
                When(pgroup_id=1, then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(people_id=1, then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
            )).filter(
                ~Q(id=1),
                identifier='PPM',
                client_id = S['client_id'],
                plandatetime__date__gte = pd1,
                plandatetime__date__lte = pd2
            ).select_related(*related).values(*fields)
        return qset or self.none()
    

    
    def get_taskchart_data(self, request):
        S, R = request.session, request.GET
        total_schd = self.filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in = S['assignedsites'],
            identifier = 'TASK',
            plandatetime__date__gte = R['from'],
            plandatetime__date__lte = R['upto'],
            client_id = S['client_id']
        ).values()
        return [
            total_schd.filter(jobstatus='ASSIGNED').count(),
            total_schd.filter(jobstatus='COMPLETED').count(),
            total_schd.filter(jobstatus='AUTOCLOSED').count(),
            total_schd.count(),
        ]
    
    
    def get_tourchart_data(self, request):
        S, R = request.session, request.GET
        total_schd = self.filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in = S['assignedsites'],
            identifier = 'INTERNALTOUR',
            plandatetime__date__gte = R['from'],
            plandatetime__date__lte = R['upto'],
            client_id = S['client_id']
        ).values()
        return [
            total_schd.filter(jobstatus='COMPLETED').count(),
            total_schd.filter(jobstatus='INPROGRESS').count(),
            total_schd.filter(jobstatus='PARTIALLYCOMPLETED').count(),
            total_schd.count(),
        ]
    
    
        

class AttachmentManager(models.Manager):
    use_in_migrations = True

    def get_people_pic(self,  ownerid, db):
        qset =  self.filter(
                attachmenttype = 'ATTACHMENT',
                owner = ownerid
                ).annotate(
            people_event_pic = Concat(V(settings.MEDIA_ROOT), V('/'),  F('filepath'),  F('filename'),
                                    output_field = CharField())).order_by('-mdtz').using(db)
        return qset[0] or self.none()

    def get_attachment_record(self, uuid, db):
        qset =  self.filter(
            ~Q(filename__endswith = '.csv'),
            ~Q(filename__endswith = '.mp4'),
            ~Q(filename__endswith = '.txt'),
            ~Q(filename__endswith = '.3gp'),
            ownername__tacode = 'PEOPLEEVENTLOG',
            attachmenttype = 'ATTACHMENT', 
            owner = uuid
            ).using(db).values('ownername_id', 'ownername__tacode')
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
        from apps.onboarding.models import TypeAssist
        ta = TypeAssist.objects.filter(taname = R['ownername'])
        PostData = {'filepath':filepath, 'filename':filename, 'owner':R['ownerid'], 'bu_id':S['bu_id'],
                'attachmenttype':R['attachmenttype'], 'ownername_id':ta[0].id,
                'cuser':request.user, 'muser':request.user, 'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset'])}
        try:
            qset = self.create(**PostData)
        except Exception:
            log.error("Attachment record creation failed...", exc_info=True)
            return {'error':'Upload attachment Failed'}
        return {'filepath':qset.filepath, 'filename':qset.filename.name, 'id':qset.id} if qset else self.none()

    def get_attforuuids(self, uuids):
        return self.filter(owner__in = uuids) or self.none()
    
    def get_fr_status(self,attduuid):
        from apps.attendance.models import PeopleEventlog
        from apps.peoples.models import People

        #get attachments of IN and OUT of attendance
        attqset = self.filter(owner = attduuid, attachmenttype = 'ATTACHMENT', ownername__tacode='PEOPLEEVENTLOG').values('id', 'filename', 'filepath', 'cdtz', 'cuser__peoplename').order_by('cdtz') or self.none()
        log.info(attqset)

        #get eventlog of IN and OUT of attendance
        eventlogqset = PeopleEventlog.objects.filter(
            uuid = attduuid, peventtype__tacode__in = ['SELF', 'MARK']).annotate(
                eventtype = F('peventtype__tacode'),
                createdby = F('cuser__peoplename'),
                site = F('bu__buname'),
                startgps = AsGeoJSON('startlocation'),
                endgps = AsGeoJSON('endlocation'),).values(
                    'peventlogextras', 'startgps', 'endgps','createdby', 'datefor', 'site', 'people_id', 'people__uuid').order_by('cdtz') or PeopleEventlog.objects.none()
        log.info(eventlogqset)
        #default image of people
        defaultimgqset = People.objects.filter(
            id=eventlogqset[0]['people_id']).values(
                'id', 'peopleimg', 'cdtz', 'cuser__peoplename', 'mdtz', 'muser__peoplename', 'ctzoffset') if eventlogqset else self.none()
        log.info(defaultimgqset)

        return {'attd_in_out': list(attqset), 'eventlog_in_out': list(eventlogqset), 'default_img_path': list(defaultimgqset)}

    
        

class AssetManager(models.Manager):
    use_in_migrations = True
    related = ['category', 'client', 'cuser', 'muser', 'parent', 'subcategory', 'tenant', 'type', 'unit', 'brand', 'bu', 'serv_prov']
    fields = ['id', 'cdtz', 'mdtz', 'ctzoffset', 'assetcode', 'assetname', 'enable', 'iscritical', 'gpslocation', 'identifier', 'runningstatus', 'capacity', 'brand_id', 'bu_id',
              'category_id', 'client_id', 'cuser_id', 'muser_id', 'parent_id', 'servprov_id', 'subcategory_id', 'tenant_id', 'type_id', 'unit_id']

    def get_assetdetails(self, mdtz, site_id):
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        return self.filter(
            Q(id=1) | 
            ~Q(identifier = 'NEA'),
            ~Q(runningstatus = 'SCRAPPED'),
            Q(mdtz__gte = mdtzinput),
            Q(bu_id= site_id),
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
    
    def get_checkpointlistview(self, request, related, fields, id=None):
        S = request.session
        qset = self.annotate(
            gps = AsWKT('gpslocation')
        ).select_related(*related)

        if id:
            qset = qset.filter(enable=True, identifier='CHECKPOINT',id=id).values(*fields)[0]
        else:
            qset = qset.filter(enable=True, identifier='CHECKPOINT', bu_id__in = S['assignedsites'], client_id = S['client_id']).values(*fields)
        
        return qset or self.none()
    
    def get_smartplacelistview(self, request, related, fields, id=None):
        S = request.session
        qset = self.annotate(
            gps = AsWKT('gpslocation')
        ).select_related(*related)

        if id:
            qset = qset.filter(enable=True, identifier='SMARTPLACE',id=id).values(*fields)[0]
        else:
            qset = qset.filter(enable=True, identifier='SMARTPLACE', bu_id__in = S['assignedsites'], client_id = S['client_id']).values(*fields)
        return qset or self.none()
    
    def get_assetlistview(self, related, fields, request):
        
        S = request.session
        qset = self.annotate(gps = AsGeoJSON('gpslocation')).filter(
            ~Q(assetcode='NONE'),
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            identifier='ASSET'
        ).select_related(*related).values(*fields)
        return qset or self.none()
    
    
    
    
    def get_assetchart_data(self, request):
        S = request.session
        from apps.activity.models import Location
        
        working = [
        self.filter(runningstatus = 'WORKING', bu_id__in = S['assignedsites'], identifier = 'ASSET').values('id').order_by('assetcode').distinct('assetcode').count(),
        self.filter(runningstatus = 'WORKING', bu_id__in = S['assignedsites'], identifier = 'CHECKPOINT').values('id').order_by('assetcode').distinct('assetcode').count(),
        Location.objects.filter(locstatus = 'WORKING', bu_id__in = S['assignedsites']).values('id').order_by('loccode').distinct('loccode').count()]
        mnt = [
        self.filter(runningstatus = 'MAINTENANCE', bu_id__in = S['assignedsites'], identifier = 'ASSET').values('id').order_by('assetcode').distinct('assetcode').count(),
        self.filter(runningstatus = 'MAINTENANCE', bu_id__in = S['assignedsites'], identifier = 'CHECKPOINT').values('id').order_by('assetcode').distinct('assetcode').count(),
        Location.objects.filter(locstatus = 'MAINTENANCE', bu_id__in = S['assignedsites']).values('id').order_by('loccode').distinct('loccode').count()
        ]
        stb = [
        self.filter(runningstatus = 'STANDBY', bu_id__in = S['assignedsites'], identifier = 'ASSET').values('id').order_by('assetcode').distinct('assetcode').count(),
        self.filter(runningstatus = 'STANDBY', bu_id__in = S['assignedsites'], identifier = 'CHECKPOINT').values('id').order_by('assetcode').distinct('assetcode').count(),
        Location.objects.filter(locstatus = 'STANDBY', bu_id__in = S['assignedsites']).values('id').order_by('loccode').distinct('loccode').count()
        ]
        scp = [
        self.filter(runningstatus = 'SCRAPPED', bu_id__in = S['assignedsites'], identifier = 'ASSET').values('id').order_by('assetcode').distinct('assetcode').count(),
        self.filter(runningstatus = 'SCRAPPED', bu_id__in = S['assignedsites'], identifier = 'CHECKPOINT').values('id').order_by('assetcode').distinct('assetcode').count(),
        #Location.objects.filter(locstatus = 'SCRAPPED', bu_id__in = S['assignedsites']).values('id').order_by('loccode').distinct('loccode').count()
        ]
        
        series = [
            {'name':'Working', 'data':working},     
            {'name':'Maintainence', 'data':mnt},
            {'name':'Standby', 'data':stb},
            {'name':'Scrapped', 'data':scp},
        ]
        
        return series, sum(list(map(sum, zip(*[working, mnt, stb, scp]))))
    
    


class JobneedDetailsManager(models.Manager):
    use_in_migrations = True
    related = ['question', 'jobneed', 'cuser', 'muser']
    fields = ['id', 'uuid', 'seqno', 'answertype', 'answer', 'isavpt', 'options', 'ctzoffset', 'ismandatory',
              'cdtz', 'mdtz', 'avpttype',           
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

    def get_e_tour_checklist_details(self, jobneedid):
        qset = self.filter(jobneed_id=jobneedid).select_related('question').values(
            'question__quesname', 'answertype', 'min', 'max', 'id',
            'options', 'alerton', 'ismandatory', 'seqno','answer'
        ).order_by('seqno')
        return qset or self.none()

    def getAttachmentJND(self, id):
        if qset := self.filter(id=id).values('uuid'):
            if atts := self.get_atts(qset[0]['uuid']):
                return atts or self.none()
        return self.none()
    
    def get_atts(self, uuid):
        from apps.activity.models import Attachment
        if atts := Attachment.objects.annotate(
            file = Concat(V(settings.MEDIA_URL, output_field=models.CharField()), F('filepath'),
                          V('/'), Cast('filename', output_field=models.CharField()))
            ).filter(owner = uuid).values(
            'filepath', 'filename', 'attachmenttype', 'datetime',  'id', 'file'
            ):return atts
        return self.none()
    
    def get_task_details(self, taskid):
        qset = self.filter(
            jobneed_id = taskid
        ).select_related('question').values('question__quesname', 'answertype', 'min', 'max', 'id',
            'options', 'alerton', 'ismandatory', 'seqno','answer').order_by('seqno')
        return qset or self.none()
        


class QsetBlngManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'seqno', 'answertype',  'isavpt', 'options', 'ctzoffset', 'ismandatory',
              'min', 'max', 'alerton', 'client_id', 'bu_id',  'question_id', 'isavpt', 'avpttype',
              'qset_id', 'cuser_id', 'muser_id', 'cdtz', 'mdtz', 'alertmails_sendto', 'tenant_id']
    related = ['client', 'bu',  'question', 
              'qset', 'cuser', 'muser']

    def get_modified_after(self ,mdtz, buid):
        qset = self.select_related(
            *self.related).filter(
                 mdtz__gte = mdtz, bu_id = buid).values(
                    *self.fields
                )
        return qset or self.none()
    
    def handle_questionpostdata(self, request):
        R, S, Id, r = request.POST, request.session, None, {}
        ic(R)
        r['ismandatory'] = R.get('ismandatory', False) == 'true'
        r['isavpt'] = R.get('isavpt', False) == 'true'
        r['options'] = R['options'].replace('"', '').replace('[', '').replace(']', '')
        r['min'] = 0.0 if R['min'] == "" else R['min']
        r['max'] = 0.0 if R['max'] == "" else R['max']
        
        if R['answertype'] in ['DROPDOWN', 'CHECKBOX']:
            r['alerton'] = R['alerton'].replace('"', '').replace('[', '').replace(']', '')
        
        elif R['answertype'] == 'NUMERIC':
            r['alerton'] = f"<{R['alertbelow']}, >{R['alertabove']}"
        
        PostData = {'qset_id':R['parent_id'], 'answertype':R['answertype'], 'min':r.get('min', '0.0'), 'max':r.get('max', '0.0'),
                'alerton':r.get('alerton'), 'ismandatory':r['ismandatory'], 'question_id': R['question_id'],
                'isavpt':r['isavpt'], 'avpttype':R['avpttype'],
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
                 'max', 'options', 'alerton', 'ismandatory', 'isavpt', 'avpttype') or self.none()
        
    
    def get_questions_of_qset(self, R):
        qset = self.annotate(quesname = F('question__quesname')).filter(
            qset_id = R['qset_id']).select_related('question').values(
                'pk', 'quesname', 'answertype', 'min', 'max','question_id',
                'options', 'alerton', 'ismandatory', 'seqno', 'ctzoffset', 'isavpt', 'avpttype')
        return qset or self.none()
    

    
    
    
class TicketManager(models.Manager):
    use_in_migrations = True
   
    def send_ticket_mail(self, ticketid):
        ticketmail = self.raw('''SELECT ticket.id, ticket.ticketlog,  ticket.comments, ticket.ticketdesc, ticket.cdtz,ticket.status, ticket.ticketno, ticket.level, bt.buname,
                ( ticket.cdtz + interval'1 minutes' ) createdon, ( ticket.mdtz + interval '1 minutes' ) modifiedon,  modifier.peoplename as  modifiername,                                       
                    people.peoplename, people.email as peopleemail, creator.id as creatorid, creator.email as creatoremail,
                    modifier.id as modifierid, modifier.email as modifiermail,pgroup.id as pgroupid, pgroup.groupname ,
                    ticket.assignedtogroup_id,  ticket.priority,
                    ticket.assignedtopeople_id, ticket.escalationtemplate as tescalationtemplate,                                                
                ( SELECT emnext.frequencyvalue || ' ' || emnext.frequency FROM escalationmatrix AS emnext                         
                WHERE  ticket.bu_id= emnext.bu_id AND ticket.escalationtemplate=emnext.escalationtemplate AND emnext.level=ticket.level + 1   
                ORDER BY cdtz LIMIT 1 ) AS next_escalation,
                (select array_to_string(ARRAY(select email from people where id in(select people_id from pgbelonging where pgroup_id=pgroup.id )),',') ) as pgroupemail                                                                     
                FROM ticket                                                                                                          
                LEFT  JOIN people modifier    ON ticket.muser_id=modifier.id                                                      
                LEFT JOIN people              ON ticket.assignedtopeople_id=people.id 
                LEFT JOIN pgroup              ON ticket.assignedtogroup_id=pgroup.id
                LEFT JOIN people creator      ON ticket.cuser_id =creator.id
                LEFT JOIN bt                  ON ticket.bu_id =bt.id
                WHERE ticket.id in (%s)''', [ticketid])
        return ticketmail or self.none() 


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

    def get_scheduled_internal_tours(self, request, related, fields):
        S = request.session
        qset = self.select_related(*related).annotate(
                assignedto = Case(
                When(Q(pgroup_id=1) | Q(pgroup_id__isnull =  True), then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(Q(people_id=1) | Q(people_id__isnull =  True), then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
                ),
            ).filter(
            Q(parent__jobname = 'NONE') | Q(parent_id = 1),
            ~Q(jobname='NONE') | ~Q(id=1),
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            identifier__exact='INTERNALTOUR',
            enable=True
        ).values(*fields).order_by('-cdtz')
        return qset or self.none()

    def get_checkpoints_for_externaltour(self, job):
        qset = self.select_related(
            'identifier', 'butype', 'parent').annotate(bu__buname = F('buname')).filter(
                parent_id = job.bu_id).values(
                'buname', 'id', 'bucode', 'gpslocation',
            )
        return qset or self.none()

    
    def get_scheduled_tasks(self, request, related, fields):
        S = request.session
        qset = self.annotate(
            assignedto = Case(
                When(Q(pgroup_id=1) | Q(pgroup_id__isnull =  True), then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(Q(people_id=1) | Q(people_id__isnull =  True), then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
            )
            ).filter(
            ~Q(jobname='NONE') | ~Q(id=1),
            Q(parent__jobname = 'NONE') | Q(parent_id = 1),
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            identifier = 'TASK',
        ).select_related(*related).values(*fields)
        return qset or self.none()
    
    def get_listview_objs_schdexttour(self, request):
        S = request.session
        qset = self.annotate(
            assignedto = Case(
                When(Q(pgroup_id=1) | Q(pgroup_id__isnull =  True), then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(Q(people_id=1) | Q(people_id__isnull =  True), then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
            ),
            sitegrpname = F('sgroup__groupname'),
            israndomized = F('other_info__is_randomized'),
            tourfrequency = F('other_info__tour_frequency'),
            breaktime = F('other_info__breaktime'),
            deviation = F('other_info__deviation')
        ).filter(
            ~Q(jobname='NONE'), parent_id=1, identifier='EXTERNALTOUR', bu_id__in = S['assignedsites'], enable=True,client_id = S['client_id']
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
            jobid = F('id'), bu__gpslocation = AsGeoJSON('bu__gpslocation'),
            buid = F('bu_id'),
            breaktime = F('other_info__breaktime'),
            distance=F('other_info__distance'),
            duration = V(None, output_field=models.CharField(null=True)),
            solid = F('bu__solid'),
            qsetname=F('qset__qsetname')
            
        ).filter(parent_id=job['id']).select_related('asset', 'qset',).values(
            'id',
            'breaktime', 'distance', 'starttime', 'expirytime',
            'qsetid', 'jobid', 'assetid', 'seqno', 'jobdesc',
            'bu__buname', 'buid', 'bu__gpslocation', 'endtime', 'duration',
            'qsetname', 'solid'
        ).order_by('seqno')
        return qset or self.none()
    
    def get_people_assigned_to_geofence(self, geofenceid):
        if geofenceid in [None, "None"]:return self.none()
        objs = self.filter(
            identifier='GEOFENCE', enable=True, geofence_id = geofenceid
        ).values('people_id', 'people__peoplename','people__peoplecode', 'fromdate', 'uptodate', 'starttime', 'endtime', 'pk')
        return objs or self.none()
    

    def handle_geofencepostdata(self, request):
        """handle post data submitted from geofence add people form"""
        R, S = request.GET, request.session
        fromdate = datetime.strptime(R['fromdate'], '%d-%b-%Y').date()
        uptodate = datetime.strptime(R['uptodate'], '%d-%b-%Y').date()
        starttime = datetime.strptime(R['starttime'], '%H:%M').time()
        endtime = datetime.strptime(R['endtime'], '%H:%M').time()
        cdtz = datetime.now(tz = timezone.utc)
        mdtz = datetime.now(tz = timezone.utc)

        PostData = {
            'jobname':f"{R['gfcode']}-{R['people__peoplename']}", 'identifier':'GEOFENCE',
            'jobdesc':f"{R['gfcode']}-{R['gfname']}-{R['people__peoplename']}",
            'fromdate':fromdate, 'uptodate':uptodate, 'starttime':starttime,
            'endtime':endtime, 'cdtz':cdtz, 'mdtz':mdtz, 'enable':True, 'bu_id':R['bu_id'],
            'client_id':S['client_id'], 'people_id':R['people_id'], 'geofence_id':R['geofence_id'],
            'seqno':-1, 'parent_id':1, 'pgroup_id':1, 'sgroup_id':1, 'asset_id':1, 'qset_id':1,
            'planduration':0, 'gracetime':0, 'expirytime':0, 'cuser':request.user, 'muser':request.user
        }
        if R['action'] == 'create':
            if self.filter(
                jobname = PostData['jobname'], asset_id = PostData['asset_id'],
                qset_id = PostData['qset_id'], parent_id = PostData['parent_id'],
                identifier='GEOFENCE').exists():
                return {'data':list(self.none()), 'error':'Warning: Record already added!'}
            ID = self.create(**PostData).id
        elif R['action'] == 'edit':
            PostData.pop('cdtz')
            PostData.pop('cuser')
            if updated := self.filter(pk=R['pk']).update(**PostData):
                ID = R['pk']
        else:
            self.filter(pk = R['pk']).delete()
            return {'data':list(self.none()),}
        qset = self.filter(pk = ID).values('people__peoplename', 'people_id', 'fromdate', 'uptodate',
                                            'starttime', 'endtime', 'people__peoplecode', 'pk')
        return {'data':list(qset)}
    
    def get_jobppm_listview(self, request):
        R, S = request.GET, request.session
        fromdt = R.get('from', datetime.now() - timedelta(days=7))
        uptpdt = R.get('upto', datetime.now())
        qset = self.annotate(
            assignedto = Case(
                When(pgroup_id=1, then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(people_id=1, then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
            )).filter(
            fromdate__date__gte = fromdt,
            uptodate__date__lte = uptpdt,
            client_id = S['client_id'],
            identifier = 'PPM'
        ).values('id', 'jobname', 'asset__assetname', 'qset__qsetname', 'assignedto',
                 'uptodate', 'planduration', 'gracetime', 'expirytime', 'fromdate')
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
    
    
class ESCManager(models.Manager):
    use_in_migrations=True
    
    def get_reminder_config_forppm(self, job_id, fields):
        qset = self.filter(
            escalationtemplate="JOB",
            job_id = job_id
        ).values(*fields) 
        return qset or self.none()
    
    
    def handle_reminder_config_postdata(self,request):
        
        P, S = request.POST, request.session
        ic(P)
        cdtz = datetime.now(tz = timezone.utc)
        mdtz = datetime.now(tz = timezone.utc)
        PostData = {
            'cdtz':cdtz, 'mdtz':mdtz, 'cuser':request.user, 'muser':request.user,
            'level':1, 'job_id':P['jobid'], 'frequency':P['frequency'], 'frequencyvalue':P['frequencyvalue'],
            'notify':P['notify'], 'assignedperson_id':P['peopleid'], 'assignedgroup_id':P['groupid'], 
            'bu_id':S['bu_id'], 'escalationtemplate':P['esctemplate'], 'client_id':S['client_id'], 
            'ctzoffset':P['ctzoffset']
        }
        if P['action'] == 'create':
            if self.filter(
                frequency = PostData['frequency'], frequencyvalue = PostData['frequencyvalue'], 
                ).exists():
                return {'data':list(self.none()), 'error':'Warning: Record already added!'}
            ID = self.create(**PostData).id
        
        elif P['action'] == 'edit':
            PostData.pop('cdtz')
            PostData.pop('cuser')
            if updated := self.filter(pk=P['pk']).update(**PostData):
                ID = P['pk']
        else:
            self.filter(pk = P['pk']).delete()
            return {'data':list(self.none()),}
        ic(ID)
        qset = self.filter(pk = ID).values('notify', 'frequency', 'frequencyvalue', 'id')
        ic(qset)
        return {'data':list(qset)}
    

class LocationManager(models.Manager):
    use_in_migrations = True
    
    def get_locationlistview(self, related, fields, request):
        S = request.session
        qset = self.filter(
            ~Q(loccode='NONE'),
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
        ).select_related(*related).values(*fields)
        return qset or self.none()
    
    def get_locations_modified_after(self, mdtz, buid, ctzoffset):
        related = ['client', 'cuser', 'muser', 'parent',  'tenant', 'type', 'bu']
        fields = ['id', 'cdtz', 'mdtz', 'ctzoffset', 'loccode', 'locname', 'enable', 'iscritical', 'gpslocation', 'locstatus',  'bu_id',
               'client_id', 'cuser_id', 'muser_id', 'parent_id',  'tenant_id', 'type_id']
        
        if not isinstance(mdtz, datetime):
            mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        qset = self.select_related(*related).filter(
            Q(mdtz__gte = mdtz) & Q(bu_id__in=[buid])  & Q(enable=True)
            ).values(*fields)
        return qset or self.none()