from django.db import models
from django.utils.translation import gettext as _
from django.db.models.functions import Concat, Cast
from django.db.models import CharField, Value as V, Subquery, OuterRef, Exists
from django.db.models import Q, F, Count, Case, When, Func
from django.contrib.gis.db.models.functions import  AsWKT, AsGeoJSON
from datetime import datetime, timedelta, timezone
from django.core.paginator import Paginator
from pyparsing import identbodychars
from apps.core import utils
from itertools import chain
import apps.peoples.models as pm
import logging
import json
logger = logging.getLogger('__main__')
from django.conf import settings
log = logger

class QuestionSetManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'cuser_id', 'muser_id', 'ctzoffset', 'bu_id', 'client_id', 'cdtz', 'mdtz',
              'parent_id', 'qsetname', 'enable', 'assetincludes', 'show_to_all_sites',
              'buincludes', 'seqno', 'url', 'type' , 'tenant_id', 'site_grp_includes',
              'site_type_includes']
    related = ['cuser', 'muser', 'client', 'bu', 'parent', 'asset', 'type']

    def get_template_list(self, bulist):
        bulist = bulist.split(',') if isinstance(bulist, str) else bulist
        if bulist:
            if qset := self.select_related(
                *self.related).filter(buincludes__contains = bulist).values_list('id', flat = True):
                return tuple(qset)
        return ""

    def get_qset_modified_after(self, mdtz, buid, clientid, peopleid):
        user = pm.People.objects.get(id = peopleid)
        qset = self.select_related(*self.related).filter(
            Q(id=1) |
            ((Q(client_id=clientid) & Q(enable=True)) &
            ((Q(mdtz__gte=mdtz) & Q(bu_id=buid)) |
            Q(show_to_all_sites=True) |
            Q(site_grp_includes__contains=user.people_extras['assignsitegroup']) |
            Q(id__in = user.people_extras['tempincludes'])))
            ).values(*self.fields).order_by('-mdtz')
        qset = self.clean_fields(qset)
        return qset or None

    def get_configured_sitereporttemplates(self, request, related, fields, type):
        S = request.session
        qset = self.select_related(
            *related).filter(enable = True, type=type, client_id = S['client_id'], bu_id = S['bu_id'], parent_id=1).values(*fields)
        qset = self.clean_fields(qset)
        return qset or self.none()
    
    def clean_fields(self, qset):
        for obj in qset:
            if(obj.get('assetincludes') or obj.get('buincludes') or obj.get('site_grp_includes') or obj.get('site_type_includes')):
                obj['assetincludes'] = str(obj['assetincludes']).replace('[', '').replace(']', '').replace("'", "")
                obj['site_grp_includes'] = str(obj['site_grp_includes']).replace('[', '').replace(']', '').replace("'", "")
                obj['site_type_includes'] = str(obj['site_type_includes']).replace('[', '').replace(']', '').replace("'", "")
                obj['buincludes'] = str(obj['buincludes']).replace('[', '').replace(']', '').replace("'", "")
        return qset 
    
    def get_qset_with_questionscount(self, parentid):
        qset = self.annotate(qcount=Count('questionsetbelonging')).filter(
            parent_id=parentid, enable=True
        ).values('id', 'qsetname', 'qcount', 'seqno')
        return qset or self.none()
    
    def handle_qsetpostdata(self, request):
        R, S = request.POST, request.session
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
            Q(type='RPCHECKLIST') & Q(bu_id__in = S['assignedsites'])
            |
            Q( Q(parent_id__isnull=True) | Q(parent_id=1), ~Q(qsetname='NONE'),
            Q(bu_id = S['bu_id']),
            Q(client_id = S['client_id']), 
            )
            
        ).select_related(*related).values(*fields)
        return qset or self.none()
    
    def get_proper_checklist_for_scheduling(self,request, types):
        S = request.session
        
        qset = self.filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            type__in = types,
            enable=True
        ).select_related('bu' ,'client', 'parent').exclude(
            questionsetbelonging=None,
        )
        return qset or self.none()
    
    def filter_for_dd_qset_field(self, request, type, choices=False, sitewise=False):
        from apps.activity.models import QuestionSetBelonging
        has_questions = QuestionSetBelonging.objects.filter(qset=OuterRef('pk')).values('pk')
        S = request.session
        qset = self.annotate(
            has_questions=Exists(has_questions)
        ).filter(
            enable=True,
            client_id=S['client_id'],
            bu_id__in=S['assignedsites'],
            type__in=type,
            has_questions=True
        ).order_by('qsetname')
        if sitewise: qset = qset.filter(bu_id = S['bu_id'])
        if choices: qset = qset.values_list('id', 'qsetname')
        return qset or self.none()
    
    def get_qsets_for_tour(self, request):
        R, S = request.GET, request.session
        search_term = R.get('search')
        qset = self.filter(
            Q(Q(client_id = S['client_id']), Q(bu_id = S['bu_id']), Q(enable=True), Q(type=self.model.Type.CHECKLIST)) |
            Q(id=1))
        qset = qset.filter(qsetname = search_term) if search_term else qset
        qset = qset.annotate(
                text = F('qsetname')).values(
                    'id', 'text')
        return qset or self.none()
    
    def qset_choices_for_report(self, request):
        S = request.session
        qset = self.filter(
            bu_id = S['bu_id'],
            client_id = S['client_id']
        ).values_list('id','qsetname')
        return qset or self.none()
        
    
        
class QuestionManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'quesname', 'options', 'min', 'max', 'alerton', 'answertype', 'muser_id', 'cdtz', 'mdtz',
            'client_id', 'isworkflow', 'enable', 'category_id', 'cuser_id', 'unit_id' , 'tenant_id', 'ctzoffset']
    related = ['client', 'muser', 'cuser', 'category', 'unit']
    
    
    def hrd(self): #hrd: human readable data 
        # Create a list of When conditions for each AnswerType choice
        conditions = [
            When(answertype=db_value, then=V(display_value))
            for db_value, display_value in self.model.AnswerType.choices
        ]
        
        return self.get_queryset().annotate(
            answertype_human_readable=Case(
                *conditions,
                default=V('Undefined'),
                output_field=CharField()
            )
        )
    
    def get_questions_modified_after(self, mdtz, clientid):
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        qset = self.select_related(*self.related).filter(
             mdtz__gte = mdtzinput, enable=True, client_id=clientid).values(*self.fields).order_by('-mdtz')
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

    def get_task_list_jobneed(self, related, fields, request, id=None):
        annotations = {'assignedto':Case(
                When(Q(pgroup_id=1) | Q(pgroup_id__isnull =  True), then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(Q(people_id=1) | Q(people_id__isnull =  True), then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
                )}
        if id:
            return self.filter(id = id).annotate(**annotations).select_related(*related).values(*fields) or self.none()
        
        R, S = request.GET, request.session
        P = json.loads(R.get('params'))
        qobjs = self.select_related(*related).annotate(
            **annotations
            ).filter(
            bu_id = S['bu_id'],
            client_id = S['client_id'],
            plandatetime__date__gte = P['from'],
            plandatetime__date__lte = P['to'],
            identifier = 'TASK'
        ).exclude(parent__jobdesc = 'NONE', jobdesc = 'NONE').values(*fields).order_by('-plandatetime')
        if P.get('jobstatus') and P['jobstatus'] != 'TOTALSCHEDULED':
            qobjs = qobjs.filter(jobstatus = P['jobstatus'])
        if P.get('alerts') and P.get('alerts') == 'TASK':
            qobjs = qobjs.filter(alerts=True)
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
        from apps.activity.models import Attachment, QuestionSet
        R = request.GET
        P = json.loads(R['params'])
        sites = Pgbelonging.objects.get_assigned_sites_to_people(request.user.id)
        buids = sites
        qset = self.annotate(
            buname = Case(
                When(Q(Q(othersite__isnull=True) | Q(othersite = "") | Q(othersite = 'NONE')), then=F('bu__buname')),
                default= F('othersite')
            ),
            gps = AsGeoJSON('gpslocation'),
            uuidtext = Cast('uuid', output_field=models.CharField())
        ).filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            plandatetime__date__gte =P['from'], plandatetime__date__lte = P['to'], identifier = QuestionSet.Type.INCIDENTREPORTTEMPLATE, bu_id__in = buids).values(
            'id', 'plandatetime', 'jobdesc', 'bu_id', 'buname', 'gps', 'jobstatus', 'performedby__peoplename', 'uuidtext', 'remarks', 'geojson__gpslocation',
            'identifier', 'parent_id'
        )
        atts = Attachment.objects.filter(
            owner__in = qset.values_list('uuidtext', flat=True)
        ).values('filepath', 'filename')
        return qset, atts or self.none() 
        

    def get_internaltourlist_jobneed(self, request, related, fields):
        R, S = request.GET, request.session
        P = json.loads(R.get('params'))
        assignedto = {'assignedto' : Case(
                When(Q(pgroup_id=1) | Q(pgroup_id__isnull =  True), then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(Q(people_id=1) | Q(people_id__isnull =  True), then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
                )}
        if P.get('dynamic'):
            conditional_filters = {'other_info__isdynamic':True}
        else:
            conditional_filters = {'plandatetime__date__gte':P['from'], 'plandatetime__date__lte':P['to']}
        qobjs = self.annotate(
            **assignedto,client_name=F('client__buname'),site_name=F('bu__buname'),
            no_of_checkpoints=Count('jobneed', distinct=True),
            completed=Count('jobneed', filter=Q(jobneed__jobstatus='COMPLETED'), distinct=True),
            missed=Count('jobneed', filter=Q(jobneed__jobstatus__in=['ASSIGNED', 'AUTOCLOSED']), distinct=True)
            ).select_related(
                *related).filter(
                    Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
                    bu_id__in = S['assignedsites'],
                    client_id = S['client_id'],
                    identifier='INTERNALTOUR',
                    **conditional_filters
            ).exclude(
            id=1
            ).values(*fields).order_by('-plandatetime')
        if P.get('jobstatus') and P['jobstatus'] != 'TOTALSCHEDULED':
            qobjs = qobjs.filter(jobstatus = P['jobstatus'])
        
        if P.get('alerts') and P.get('alerts') == 'TOUR':
            qobjs = qobjs.filter(
            alerts=True,
        ).values(*fields)
        return qobjs or self.none()
    
    
    def get_externaltourlist_jobneed(self, request, related, fields):
        fields = ['id', 'plandatetime', 'expirydatetime', 'performedby__peoplename', 'jobstatus','gps',
                  'jobdesc', 'people__peoplename', 'pgroup__groupname', 'gracetime', 'ctzoffset', 'assignedto']
        R, S = request.GET, request.session
        P = json.loads(R['params'])
        assignedto = {
            'assignedto' : Case(
                When(Q(pgroup_id=1) | Q(pgroup_id__isnull =  True), then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(Q(people_id=1) | Q(people_id__isnull =  True), then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
                ),
            'gps':AsGeoJSON('gpslocation')
                }
        qset = self.annotate(
            **assignedto
            ).select_related(
                *related).filter(
                    Q(bu_id__in = S['assignedsites']) | Q(sgroup_id__in = S['assignedsitegroups']),
                    parent_id=1,
                    plandatetime__date__gte = P['from'],
                    plandatetime__date__lte =  P['to'],
                    jobtype="SCHEDULE",
                    identifier='EXTERNALTOUR',
                    job__enable=True
                        ).exclude(
                        id=1
                        ).values(*fields).order_by('-cdtz') 
        if P.get('jobstatus') and P['jobstatus'] != 'TOTALSCHEDULED':
            qset = qset.filter(jobstatus = P['jobstatus'])
        if P.get('alerts') and P.get('alerts') == 'ROUTEPLAN':
            alert_qset = self.filter(
                Q(bu_id__in = S['assignedsites']) | Q(sgroup_id__in = S['assignedsitegroups']),
                plandatetime__date__gte = P['from'],
                plandatetime__date__lte = P['to'],
                client_id = S['client_id'],
                alerts=True,
                identifier="EXTERNALTOUR"
            ).select_related(*related)
            alert_qset_parents = list(set(alert_qset.values_list('parent_id', flat=True)))
            qset = self.filter(
                id__in = alert_qset_parents).annotate(**assignedto).values(*fields)
        return qset or self.none()

    def get_tourdetails(self, R):
        qset = self.select_related(
            'parent', 'asset', 'qset').filter(parent_id = R['parent_id']).values(
                'asset__assetname', 'asset__id', 'qset__id', 'ctzoffset',
                'qset__qsetname', 'plandatetime', 'expirydatetime',
                'gracetime', 'seqno', 'jobstatus', 'id','attachmentcount'
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
        fields += ['distance', 'duration','bu__gpslocation', 'performedtime', 'alerts','attachmentcount','gps']
        qset  = self.annotate(
            distance=F('other_info__distance'),
            performedtime = F("starttime"),
            gps = AsGeoJSON('gpslocation'),
            bu__gpslocation = AsGeoJSON('bu__gpslocation'),
            duration = V(None, output_field=models.CharField(null=True))).select_related(*related).filter(
            parent_id = request.GET['parent_id'],
            identifier = 'EXTERNALTOUR',
            job__enable=True
        ).order_by('seqno').values(*fields)
        ic("checkpoints", qset)
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
        from apps.activity.models import QuestionSet
        R, S = request.GET, request.session
        pd1 = R.get('from', datetime.now().date())
        pd2 = R.get('upto', datetime.now().date())
        return self.select_related('bu', 'parent').filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in = S['assignedsites'],
            identifier = QuestionSet.Type.INCIDENTREPORTTEMPLATE,
            plandatetime__date__gte = pd1,
            plandatetime__date__lte = pd2,
            client_id = S['client_id'],
        ).count() or 0
    
    def get_schdroutes_count_forcard(self, request):
        R, S = request.GET, request.session
        pd1 = R.get('from', datetime.now().date())
        pd2 = R.get('upto', datetime.now().date())
        return self.select_related('bu', 'parent').filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            Q(bu_id__in = S['assignedsites']) | Q(sgroup_id__in = S['assignedsitegroups']),
            client_id = S['client_id'],
            plandatetime__date__gte = pd1,
            plandatetime__date__lte = pd2,
            identifier='EXTERNALTOUR'
        ).count() or 0
    
    def get_ppm_listview(self, request, fields, related):
        S, R = request.session, request.GET
        P = json.loads(R.get('params'))

        qobjs = self.select_related('people','bu', 'pgroup', 'client').annotate(
            assignedto = Case(
                When(pgroup_id=1, then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(people_id=1, then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
            )).filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in = S['assignedsites'],
            identifier = 'PPM',
            plandatetime__date__gte = P['from'],
            plandatetime__date__lte = P['to'],
            client_id = S['client_id']
            ).select_related(*related).values(*fields)
        if P.get('jobstatus') and P['jobstatus'] not in ['TOTALSCHEDULED', 'NONE']:
            qobjs = qobjs.filter(jobstatus = P['jobstatus'])
        if P.get('alerts') and P.get('alerts') == 'PPM':
            qobjs = qobjs.filter(alerts=True)
        return qobjs or self.none()
    

    
    def get_taskchart_data(self, request):
        S, R = request.session, request.GET
        total_schd = self.select_related('bu', 'parent').filter(
            Q(Q(parent_id__in=[1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in=S['assignedsites'],
            identifier='TASK',
            plandatetime__date__gte=R['from'],
            plandatetime__date__lte=R['upto'],
            client_id=S['client_id']
        ).values()
        return [
            total_schd.filter(jobstatus='ASSIGNED').count(),
            total_schd.filter(jobstatus='COMPLETED').count(),
            total_schd.filter(jobstatus='AUTOCLOSED').count(),
            total_schd.count(),
        ]
    
    
    def get_tourchart_data(self, request):
        S, R = request.session, request.GET
        total_schd = self.select_related('parent', 'bu').filter(
            Q(Q(parent_id__in=[1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in=S['assignedsites'],
            identifier='INTERNALTOUR',
            plandatetime__date__gte=R['from'],
            plandatetime__date__lte=R['upto'],
            client_id=S['client_id']
        ).values()
        return [
            total_schd.filter(jobstatus='COMPLETED').count(),
            total_schd.filter(jobstatus='INPROGRESS').count(),
            total_schd.filter(jobstatus='PARTIALLYCOMPLETED').count(),
            total_schd.count(),
        ]
    
    def get_alertchart_data(self, request):
        S, R = request.session, request.GET
        qset = self.select_related('bu', 'parent').filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in = S['assignedsites'],
            plandatetime__date__gte = R['from'],
            plandatetime__date__lte = R['upto'],
            client_id = S['client_id'],
            alerts=True
        )
        
        task_alerts = qset.filter( Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)), identifier='TASK').count()
        tour_alerts = qset.filter(identifier='INTERNALTOUR').count()
        route_alerts = self.filter(
            id__in = qset.values_list('parent_id', flat=True)).count()
        ppm_alerts = qset.filter(identifier='PPM').count()
        chart_arr =  [task_alerts, ppm_alerts, tour_alerts, route_alerts ]
        return chart_arr, sum(chart_arr)
    
    def get_expired_jobs(self, id=None):
        annotation = { 'assignedto' : Case(
                    When(pgroup_id=1, then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                    When(people_id=1, then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
                )    }
        related_fields = ['bu', 'client', 'people', 'qset', 'pgroup', 'sgroup',
                'performedby', 'asset', 'ticketcategory', 'job', 'parent']
        if not id:
            qset = self.select_related(
                *related_fields
            ).annotate(
               **annotation
            ).filter(
                ~Q(id=1),
                ~Q(jobstatus__in = ['COMPLETED', 'PARTIALLYCOMPLETED']),
                ~Q(other_info__autoclosed_by_server = True),
                ~Q(other_info__isdynamic = True),
                ~Q(Q(jobstatus = 'AUTOCLOSED') & Q(other_info__email_sent = True))|
                ~Q(Q(jobstatus = 'AUTOCLOSED') & Q(other_info__ticket_generated = True)),
                Q(parent_id = 1), Q(identifier__in = ['TASK', 'INTERNALTOUR', 'PPM', 'EXTERNALTOUR', "SITEREPORT"]),
                expirydatetime__gte=datetime.now(timezone.utc) - timedelta(days=1),
                expirydatetime__lte=datetime.now(timezone.utc),            
            )
        else:
            qset = self.filter(id=id).annotate(**annotation).select_related(*related_fields)
        qset = qset.values(
            'assignedto', 'bu__buname', 'pgroup__groupname', 'cuser__peoplename', 'asset_id',
            'people__peoplename', 'expirydatetime', 'plandatetime', 'pgroup_id', 'people_id',
            'cuser_id', 'muser_id', 'priority', 'identifier', 'ticketcategory__tacode', 'id', 'qset_id',
            'job_id', 'jobdesc', 'ctzoffset', 'client_id', 'bu_id', 'ticketcategory_id', 'ticketcategory__taname'
        )
        return qset or self.none()
    
    def get_ppmchart_data(self, request):
        S, R = request.session, request.GET
        total_schd = self.select_related('bu', 'parent').filter(
            Q(Q(parent_id__in = [1, -1]) | Q(parent_id__isnull=True)),
            bu_id__in = S['assignedsites'],
            identifier = 'PPM',
            plandatetime__date__gte = R['from'],
            plandatetime__date__lte = R['upto'],    
            client_id = S['client_id']
        ).values()
        ic(total_schd.filter(jobstatus='ASSIGNED').count(),
            total_schd.filter(jobstatus='COMPLETED').count(),
            total_schd.filter(jobstatus='AUTOCLOSED').count(),
            total_schd.count())
        return [
            total_schd.filter(jobstatus='ASSIGNED').count(),
            total_schd.filter(jobstatus='COMPLETED').count(),
            total_schd.filter(jobstatus='AUTOCLOSED').count(),
            total_schd.count(),
        ]
        
        
    def get_schedule_for_adhoc(self, qsetid, peopleid, assetid, buid, starttime, endtime):
        qset =  self.filter(
            ~Q(jobtype='ADHOC'),
            qset_id = qsetid, 
            people_id = peopleid,
            asset_id = assetid,
            bu_id = buid,
            plandatetime__lte = starttime,
            expirydatetime__gte = endtime,
            identifier = 'TASK'
        ).values().order_by('-mdtz').first()
        return qset or self.none()
        

    def get_task_summary(self, request, params):
        results = []
        fromdate = datetime.strptime(params['from_date'], "%Y-%m-%d") #xxxx-xx-xx
        uptodate = datetime.strptime(params['upto_date'], "%Y-%m-%d") #xxxx-xx-xx
        current_date = fromdate
        while(current_date <= uptodate):
            qset = self.filter(
                    bu_id = params['bu_id'],
                    plandatetime__date = current_date,
                    identifier = 'TASK'
                ).select_related('bu')
            tot_completed = qset.filter(jobtype = 'SCHEDULE', jobstatus = 'COMPLETED').count()
            tot_scheduled = qset.filter(jobtype = 'SCHEDULE').count()
            record = {
                'total_jobs'     : qset.count(),
                'total_scheduled': tot_scheduled,
                'adhoc_jobs'     : qset.filter(jobtype='ADHOC').count(),
                'completed_jobs' : tot_completed,
                'closed_jobs'    : qset.filter(jobtype = 'SCHEDULE', jobstatus = 'AUTOCLOSED').count(),
                'closed_jobs'    : qset.filter(jobtype = 'SCHEDULE', jobstatus = 'ASSIGNED').count(),
                'percentage'     : round((tot_completed/tot_scheduled) * 100, ndigits=2)
            }
            results.append(record)
            current_date = current_date + timedelta(days=1)
        return results
    

    def get_events_for_calendar(self,request):
        R, S = request.GET, request.session
        d = {'Tasks':'TASK', 'PPM':"PPM", 'Tours':'INTERNALTOUR', 'Route Plan':'EXTERNALTOUR'}
        start_date = datetime.strptime(R['start'], "%Y-%m-%dT%H:%M:%S%z").date()
        end_date = datetime.strptime(R['end'], "%Y-%m-%dT%H:%M:%S%z").date()
    
        qset = self.annotate(
            start=Cast(F('plandatetime'), output_field=CharField()),
            end=Cast(F('expirydatetime'), output_field=CharField()),
            title = F('jobdesc'),
            color = Case(
                When(jobstatus__exact =  'AUTOCLOSED', then = V('#ff6161')),
                When(jobstatus__exact = 'COMPLETED', then= V( '#779f6f')),
                When(jobstatus__exact = 'PARTIALLYCOMPLETED', then= V( '#009C94')),
                When(jobstatus__exact = 'INPROGRESS', then= V( '#ffcc27')),
                When(jobstatus__exact = 'ASSIGNED', then=V('#0080FF')),
                output_field=CharField()
            )
        ).filter(
            identifier = d.get(R['eventType']),
            plandatetime__date__gte = start_date,
            plandatetime__date__lte = end_date,
            client_id = S['client_id'],
            bu_id = S['bu_id']
        ).values('id','start', 'end', 'title', 'color')
        return qset or self.none()
    
    def get_event_details(self, request):
        R,S = request.GET, request.session
        from django.apps import apps
        d = {'Tasks':'TASK', 'PPM':"PPM", 'Tours':'INTERNALTOUR', 'Route Plan':'EXTERNALTOUR'}
        
        qset = self.annotate(
            assignto = Case(
                    When(pgroup_id=1, then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                    When(people_id=1, then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
                ),
            performedby_name = F('performedby__peoplename'),
            place = AsGeoJSON('gpslocation'),
            site = F('bu__buname'),
            assetname = F('asset__assetname'),
            qsetname = F('qset__qsetname'),
            location = F('asset__location__locname'),
            location_id = F('asset__location__id'),
            desc = F('jobdesc')
        ).filter(id = R['id']).values(
            'assignto', 'performedby_name','place', 'performedby__peopleimg','bu_id',
            'site', 'assetname', 'qsetname', 'location', 'desc', 'qset_id', 'asset_id',
            'location_id', 'performedby_id').first()
        
        return qset
    
    def get_latlng_of_checkpoints(self, jobneed_id):
        
        qset = self.filter(parent_id=jobneed_id).annotate(
            gps = AsGeoJSON('gpslocation')
        ).values('gps', 'seqno', 'starttime', 'endtime', 'jobdesc', 'qset__qsetname', 'ctzoffset', 'jobstatus')
        checkpoints, info = [], []
        for q in qset:
            gps = json.loads(q['gps'])
            checkpoints.append([[gps['coordinates'][1], gps['coordinates'][0]], q['seqno']])
            info.append(
                {
                    "starttime": self.formatted_datetime(q['starttime'], q['ctzoffset']),
                    "endtime":self.formatted_datetime(q['endtime'], q['ctzoffset']),
                    "jobdesc": q['jobdesc'],
                    "qsetname": q['qset__qsetname'],
                    "seqno":q['seqno'],
                    'jobstatus':q['jobstatus']
                })
        path = self.get_path_of_checkpoints(jobneed_id)
        latest_loc = self.get_latest_location_of_rider(jobneed_id)
        return checkpoints, info, path, latest_loc
    
    def get_path_of_checkpoints(self, jobneed_id):
        site_tour_parent = self.annotate(path=AsGeoJSON('journeypath')).filter(id=jobneed_id).first()
        if site_tour_parent.jobstatus in  (self.model.JobStatus.COMPLETED , self.model.JobStatus.PARTIALLYCOMPLETED) and site_tour_parent.path:
            geodict = json.loads(site_tour_parent.path)
            return [[lat,lng] for lng, lat in geodict['coordinates']]
            
        elif site_tour_parent.jobstatus ==  self.model.JobStatus.INPROGRESS:
            from apps.attendance.models import Tracking
            between_latlngs = Tracking.objects.filter(reference = site_tour_parent.uuid).order_by('receiveddate')
            return [[obj.gpslocation.y , obj.gpslocation.x] for obj in between_latlngs]
        else:
            return None
        
    def get_latest_location_of_rider(self, jobneed_id):
        site_tour = self.filter(id=jobneed_id).first()
        from apps.activity.models import DeviceEventlog
        from apps.attendance.models import Tracking
        
        if site_tour.performedby and site_tour.performedby_id != 1:
            people = site_tour.performedby
        elif site_tour.people and site_tour.people_id != 1:
            people = site_tour.people
        else:
            people = site_tour.sgroup.grouplead
        devl = DeviceEventlog.objects.filter(people_id=people.id).order_by('-receivedon').first()
        trac = Tracking.objects.filter(people_id=people.id).order_by('-receiveddate').first()
        # Choose the most recent event based on timestamp
        if not devl and not trac:
            return None

        if not trac or (devl and devl.receivedon > trac.receiveddate):
            event = devl
            time_key = 'receivedon'
        else:
            event = trac
            time_key = 'receiveddate'
        
        return {
            'peoplename': people.peoplename,
            'mobno': people.mobno,
            'email': people.email,
            'time': self.formatted_datetime(getattr(event, time_key), site_tour.ctzoffset),
            'gps': [event.gpslocation.y, event.gpslocation.x]
        }

    def formatted_datetime(self, dtime, ctzoffset):
        if not dtime: return "--"
        dtz = dtime + timedelta(minutes=int(ctzoffset))
        return dtz.strftime('%d-%b-%Y %H:%M:%S')
    
    def get_job_needs(self, people_id, bu_id, client_id):
        fields = [
            'id', 'jobdesc', 'plandatetime', 'expirydatetime', 'gracetime', 
            'receivedonserver', 'starttime', 'endtime', 'gpslocation', 
            'remarks', 'cdtz', 'mdtz', 'pgroup_id','asset_id', 'cuser_id', 'frequency', 
            'job_id', 'jobstatus', 'jobtype', 'muser_id', 'performedby_id', 
            'priority', 'qset_id', 'scantype', 'people_id', 'attachmentcount', 'identifier', 'parent_id',  
            'bu_id', 'client_id', 'seqno', 'ticketcategory_id', 'ctzoffset', 'multifactor',
            'uuid', 'istimebound', 'ticket_id','remarkstype_id', 'isdynamic'
        ]
        # Retrieve group IDs from Pgbelonging
        group_ids = pm.Pgbelonging.objects.filter(
            people_id=people_id
        ).exclude(
            pgroup_id=-1
        ).values_list('pgroup_id', flat=True)

        # Construct the filter conditions for the job needs
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)

        job_needs_filter = (
            Q(bu_id=bu_id) &
            Q(client_id=client_id) &
            ~Q(identifier__in=['TICKET', 'EXTERNALTOUR']) &
            (Q(people_id=people_id) | Q(cuser_id=people_id) | Q(muser_id=people_id) | Q(pgroup_id__in=group_ids)) &
            (Q(plandatetime__date__range=[today, tomorrow]) | (Q(plandatetime__lte=datetime.now()) & Q(expirydatetime__gte=datetime.now()))) |
            (Q(other_info__isdynamic=True) & Q(mdtz__date__range=[today, tomorrow])) & Q(client_id=client_id) & Q(bu_id=bu_id)
        )

        # Query for job needs with the constructed filters
        job_needs = self.annotate(
            istimebound = F('other_info__istimebound'),
            isdynamic=F('other_info__isdynamic')).filter(job_needs_filter).values(*fields)
        return job_needs

    def get_external_tour_job_needs(self, people_id, bu_id, client_id):
        fields = [
            'id', 'jobdesc', 'plandatetime', 'expirydatetime', 'gracetime', 'receivedonserver',
            'starttime', 'endtime', 'gpslocation', 'remarks', 'cdtz', 'mdtz', 'pgroup_id', 
            'asset_id', 'cuser_id', 'frequency', 'job_id', 'jobstatus', 'jobtype',
            'muser_id', 'performedby_id', 'priority', 'qset_id','scantype', 'people_id',
            'attachmentcount', 'identifier', 'parent_id', 'bu_id', 'client_id','seqno',
            'ticketcategory_id', 'ctzoffset', 'uuid', 'multifactor'
        ]
        
        # Retrieve group IDs from Pgbelonging
        group_ids = pm.Pgbelonging.objects.filter(
            people_id=people_id
        ).exclude(
            pgroup_id=-1
        ).values_list('pgroup_id', flat=True)
        # Construct the filter conditions for the job needs
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        parentqset = self.filter(
            (Q(plandatetime__date__range=[today, tomorrow]) | (Q(plandatetime__gte=datetime.now()) & Q(expirydatetime__lte=datetime.now()))) &
            (Q(people_id=people_id) | Q(cuser_id=people_id) | Q(muser_id=people_id) | Q(pgroup_id__in=group_ids)),
            parent_id=1,
            client_id=client_id,
            identifier='EXTERNALTOUR'
        )
        parent_jobneed_ids = parentqset.values_list('id', flat=True)
        child_checkpoints = self.filter(parent_id__in=parent_jobneed_ids)
        totalqset = parentqset | child_checkpoints
        totalqset = totalqset.values(*fields)
        return totalqset
        
        

    def get_dynamic_tour_count(self, request):
        S = request.session
        jobneeds = self.filter(
            other_info__isdynamic=True,
            parent_id__in = [1,-1,None],
            identifier='INTERNALTOUR',
            client_id = S['client_id'],
            bu_id__in = S['assignedsites']
        ).count()
        return jobneeds or 0

            

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

    def get_att_given_owner(self, owneruuid, request=None):
        "return attachments of given jobneed uuid"
        qset = self.filter(
            attachmenttype__in = ['ATTACHMENT', 'SIGN'], owner = owneruuid).order_by('cdtz').values(
                'id', 'filepath', 'filename', 'size', 'cdtz', 'cuser__peoplename'
            )
        return qset or self.none()
    
    
    def create_att_record(self, request, filename, filepath):
        R, S = request.POST, request.session
        from apps.onboarding.models import TypeAssist
        ta = TypeAssist.objects.filter(taname = R['ownername']).first()
        size = request.FILES.get('img').size if request.FILES.get('img') else 0
        PostData = {'filepath':filepath, 'filename':filename, 'owner':R['ownerid'], 'bu_id':S['bu_id'],
                'attachmenttype':R['attachmenttype'], 'ownername_id':ta.id,
                'cuser':request.user, 'muser':request.user, 'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']), 'size':size}
        try:
            qset = self.create(**PostData)
            count = self.filter(owner = R['ownerid']).count()
        except Exception:
            log.critical("Attachment record creation failed...", exc_info=True)
            return {'error':'Upload attachment Failed'}
        return {'filepath':qset.filepath, 'filename':qset.filename.name, 'id':qset.id, 'ownername':qset.ownername.tacode, 'attcount': count} if qset else self.none()

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
    

    def get_attachements_for_mob(self, ownerid):
        qset = self.get_att_given_owner(ownerid)
        qset = qset.annotate(
            file = Concat(V(settings.MEDIA_URL), F('filepath'), Cast('filename', output_field=models.CharField()) )
        ).values_list('file', flat=True)
        return qset or self.none()

    
        

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
    
    def asset_type_choices_for_report(self, request):
        S = request.session
        qset = self.filter(
            bu_id = S['bu_id'],
            client_id = S['client_id']
        ).select_related('type').values_list(
            'type_id', 'type__taname'
        ).distinct('type_id').order_by('type_id')
        return qset or self.none()
    
    def asset_category_choices_for_report(self, request):
        S = request.session
        qset = self.filter(
            bu_id = S['bu_id'],
            client_id = S['client_id']
        ).select_related('category').values_list(
            'category_id', 'category__taname'
        ).distinct('category_id').order_by('category_id')
        return qset or self.none()
    
    def asset_choices_for_report(self,request):
        S = request.session
        qset = self.filter(
            bu_id = S['bu_id'],
            client_id = S['client_id']
        ).values_list('id','assetname')
        return qset or self.none()


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
        P = request.GET.get('params')
        qset = self.annotate(
            gps = AsWKT('gpslocation')
        ).select_related(*related)

        if id:
            qset = qset.filter(identifier='CHECKPOINT',id=id).values(*fields)[0]
        else:
            qset = qset.filter(identifier='CHECKPOINT', bu_id=S['bu_id'], client_id = S['client_id']).values(*fields)
        if(P not in ['null', None]):
            P = json.loads(P)
            qset = qset.filter(runningstatus = P['status'])
        
        return qset or self.none()
    
    def get_smartplacelistview(self, request, related, fields, id=None):
        S = request.session
        P = request.GET['params']
        qset = self.annotate(
            gps = AsWKT('gpslocation')
        ).select_related(*related)

        if id:
            qset = qset.filter(enable=True, identifier='SMARTPLACE',id=id).values(*fields)[0]
        else:
            qset = qset.filter(enable=True, identifier='SMARTPLACE', bu_id = S['bu_id'], client_id = S['client_id']).values(*fields)
        return qset or self.none()
    
    def get_assetlistview(self, related, fields, request):
        
        S = request.session
        P = request.GET['params']
        qset = self.annotate(gps = AsGeoJSON('gpslocation')).filter(
            ~Q(assetcode='NONE'),
            bu_id = S['bu_id'],
            client_id = S['client_id'],
            identifier='ASSET'
        ).select_related(*related).values(*fields)
        if(P not in ['null', None]):
            P = json.loads(P)
            qset = qset.filter(runningstatus = P['status'])
        return qset or self.none()
    
    
    
    
    def get_assetchart_data(self, request):
        S = request.session
        from apps.activity.models import Location
        
        working = [
            self.select_related('bu', 'client').filter(
                runningstatus = 'WORKING', bu_id = S['bu_id'],
                identifier = 'ASSET', client_id=S['client_id']).values('id').order_by(
                    'assetcode').distinct('assetcode').count(),
            
            self.select_related(
                'bu', 'client').filter(
                    runningstatus = 'WORKING', bu_id = S['bu_id'],
                    identifier = 'CHECKPOINT', client_id=S['client_id']
                    ).values('id').order_by('assetcode').distinct(
                        'assetcode').count(),
            Location.objects.select_related(
                'bu', 'client').filter(
                    locstatus = 'WORKING', bu_id = S['bu_id'],
                    client_id=S['client_id']).values('id').order_by(
                        'loccode').distinct('loccode').count()
        ]
        
        
        mnt = [
            self.select_related(
                'bu', 'client').filter(
                    runningstatus = 'MAINTENANCE', bu_id = S['bu_id'],
                    identifier = 'ASSET', client_id=S['client_id']
                    ).values('id').order_by('assetcode').distinct(
                        'assetcode').count(),
            self.select_related(
                'bu', 'client').filter(
                    runningstatus = 'MAINTENANCE', bu_id = S['bu_id'],
                    identifier = 'CHECKPOINT', client_id=S['client_id']
                    ).values('id').order_by('assetcode').distinct(
                        'assetcode').count(),
            Location.objects.select_related(
                'bu', 'client').filter(
                    locstatus = 'MAINTENANCE', bu_id = S['bu_id'],
                    client_id=S['client_id']).values('id').order_by(
                        'loccode').distinct('loccode').count()
        ]
        stb = [
            self.select_related(
                'bu', 'client').filter(
                    runningstatus = 'STANDBY', bu_id = S['bu_id'],
                    identifier = 'ASSET', client_id=S['client_id']
                    ).values('id').order_by('assetcode').distinct(
                        'assetcode').count(),
            self.select_related(
                'bu', 'client').filter(
                    runningstatus = 'STANDBY', bu_id = S['bu_id'],
                    identifier = 'CHECKPOINT', client_id=S['client_id']
                    ).values('id').order_by('assetcode').distinct(
                        'assetcode').count(),
            
            Location.objects.select_related(
                'bu', 'client').filter(
                    locstatus = 'STANDBY', bu_id = S['bu_id'],
                    client_id=S['client_id']).values(
                        'id').order_by('loccode').distinct('loccode').count()
        ]
        scp = [
            self.select_related(
                'bu', 'client').filter(
                    runningstatus = 'SCRAPPED', bu_id = S['bu_id'],
                    identifier = 'ASSET', client_id=S['client_id']
                    ).values('id').order_by('assetcode').distinct(
                        'assetcode').count(),
            self.select_related(
                'bu', 'client').filter(
                    runningstatus = 'SCRAPPED', bu_id = S['bu_id'],
                    identifier = 'CHECKPOINT', client_id=S['client_id']
                    ).values('id').order_by('assetcode').distinct('assetcode').count(),
            0
        ]
        
        series = [
            {'name':'Working', 'data':working},     
            {'name':'Maintenance', 'data':mnt},
            {'name':'Standby', 'data':stb},
            {'name':'Scrapped', 'data':scp},
        ]
        
        return series, sum(list(map(sum, zip(*[working, mnt, stb, scp]))))
    
    def filter_for_dd_asset_field(self, request, identifiers, choices=False, sitewise=False):
        client_id = request.session.get('client_id')
        assigned_sites = request.session.get('assignedsites')
        bu_id = request.session.get('bu_id')

        base_filters = {
            "enable": True,
            "client_id": client_id,
            "bu_id__in": assigned_sites,
            "identifier__in": identifiers,
            
        }
        if sitewise and bu_id:
            base_filters["bu_id"] = bu_id

        qset = self.filter(~Q(runningstatus='SCRAPPED'), **base_filters).order_by('assetname')

        if choices:
            qset = (
                qset.annotate(
                    text=Concat(
                        F('assetname'), V(' ('), F('assetcode'), V(')')
                    )
                )
                .values_list('id', 'text')
            )

        return qset or self.none()

    
    def get_period_of_assetstatus(self, assetid, status):
        from apps.core.raw_queries import get_query
        query = get_query("asset_status_period")
        qset = utils.runrawsql(
            query, [status, status, assetid]
        )
        if not qset: return f"The Asset has not yet undergone any {status.lower()} period."
        if qset and  qset[0]['total_duration']:
            return utils.format_timedelta(qset[0]['total_duration'])
        
    
    def get_asset_checkpoints_for_tour(self, request):
        R, S = request.GET, request.session
        search_term = R.get('search')
        qset = self.filter(client_id = S['client_id'], bu_id = S['bu_id'], enable=True)
        qset = qset.filter(assetname = search_term) if search_term else qset
        qset = qset.annotate(
                text = F('assetname')).values(
                    'id', 'text')
        return qset or self.none()
    

class JobneedDetailsManager(models.Manager):
    use_in_migrations = True
    related = ['question', 'jobneed', 'cuser', 'muser']
    fields = ['id', 'uuid', 'seqno', 'answertype', 'answer', 'isavpt', 'options', 'ctzoffset', 'ismandatory',
              'cdtz', 'mdtz', 'avpttype',           
              'min', 'max', 'alerton', 'question_id', 'jobneed_id', 'alerts', 'cuser_id', 'muser_id', 'tenant_id']

    def get_jndmodifiedafter(self, jobneedid):
        if jobneedid:
            jobneedids = jobneedid.split(',')
            ic(jobneedids)
            qset = self.select_related(
                *self.related).filter(
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
            'question__quesname', 'answertype', 'min', 'max', 'id', 'ctzoffset',
            'options', 'alerton', 'ismandatory', 'seqno','answer', 'alerts'
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
            'options', 'alerton', 'ismandatory', 'seqno','answer', 'alerts','attachmentcount').order_by('seqno')
        return qset or self.none()
    
    def get_ppm_details(self, request):
        return self.get_task_details(request.GET.get('taskid'))

    def get_asset_comparision(self, request, formData):
        S = request.session
        qset = self.filter(
            jobneed__identifier='TASK',
            jobneed__jobstatus='COMPLETED',
            jobneed__plandatetime__date__gte=formData.get('fromdate'),
            jobneed__plandatetime__date__lte=formData.get('uptodate'),
            jobneed__bu_id=S['bu_id'],
            answertype='NUMERIC',
            question_id=formData.get('question'),
            jobneed__client_id=S['client_id']            
        ).annotate(
            plandatetime = F('jobneed__plandatetime'),
            starttime = F('jobneed__starttime'),
            jobdesc = F('jobneed__jobdesc'),
            asset_id = F('jobneed__asset_id'),
            assetcode = F('jobneed__asset__assetcode'),
            assetname = F('jobneed__asset__assetname'),
            questionname = F('question__quesname'),
            bu_id=F('jobneed__bu_id'),
            buname=F('jobneed__bu__buname'),
            answer_as_float=Cast('answer', models.FloatField())
        ).select_related('jobneed').values(
            "plandatetime", 'starttime', 'jobdesc',
            'asset_id', 'assetcode', 'questionname',
            'bu_id', 'buname', 'answer_as_float')
        
        ic(str(qset.query))
        
        series = []
        from django.apps import apps
        Asset = apps.get_model('activity', 'Asset')
        for asset_id in formData.getlist('asset'):
            series.append(
                {
                    'name':Asset.objects.get(id=asset_id).assetname,
                    'data':list(qset.filter(jobneed__asset_id=asset_id).values_list('starttime', 'answer_as_float'))
                }
            )
        ic(series)
        return series
        
    def get_parameter_comparision(self, request, formData):
        S = request.session
        qset = self.filter(
            jobneed__identifier='TASK',
            jobneed__jobstatus='COMPLETED',
            jobneed__plandatetime__date__gte=formData.get('fromdate'),
            jobneed__plandatetime__date__lte=formData.get('uptodate'),
            jobneed__bu_id=S['bu_id'],
            answertype='NUMERIC',
            jobneed__asset_id=formData.get('asset'),
            jobneed__client_id=S['client_id']            
        ).annotate(
            plandatetime = F('jobneed__plandatetime'),
            starttime = F('jobneed__starttime'),
            jobdesc = F('jobneed__jobdesc'),
            asset_id = F('jobneed__asset_id'),
            assetcode = F('jobneed__asset__assetcode'),
            assetname = F('jobneed__asset__assetname'),
            questionname = F('question__quesname'),
            bu_id=F('jobneed__bu_id'),
            buname=F('jobneed__bu__buname'),
            answer_as_float=Cast('answer', models.FloatField())
        ).select_related('jobneed').values(
            "plandatetime", 'starttime', 'jobdesc',
            'asset_id', 'assetcode', 'questionname',
            'bu_id', 'buname', 'answer_as_float')
        
        ic(str(qset.query))
        
        series = []
        from django.apps import apps
        Question = apps.get_model('activity', 'Question')
        for question_id in formData.getlist('question'):
            series.append(
                {
                    'name':Question.objects.get(id=question_id).quesname,
                    'data':list(qset.filter(question_id=question_id).values_list('starttime', 'answer_as_float'))
                }
            )
        ic(series)
        return series
        pass


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
        r['ismandatory'] = R.get('ismandatory', False) == 'true'
        r['isavpt'] = R.get('isavpt', False) == 'true'
        r['options'] = R['options'].replace('"', '').replace('[', '').replace(']', '')
        r['min'] = 0.0 if R['min'] == "" else R['min']
        r['max'] = 0.0 if R['max'] == "" else R['max']

        if R['answertype'] in ['DROPDOWN', 'CHECKBOX']:
            r['alerton'] = R['alerton'].replace('"', '').replace('[', '').replace(']', '')

        elif R['answertype'] == 'NUMERIC' and (R['alertbelow'] or R['alertabove']):
            r['alerton'] = f"<{R['alertbelow']}, >{R['alertabove']}"

        PostData = {'qset_id':R['parent_id'], 'answertype':R['answertype'], 'min':r.get('min', '0.0'), 'max':r.get('max', '0.0'),
                'alerton':r.get('alerton'), 'ismandatory':r['ismandatory'], 'question_id': R['question_id'],
                'isavpt':r['isavpt'], 'avpttype':R['avpttype'],
                'options':r.get('options'), 'seqno':R['seqno'], 'client_id':S['client_id'], 'bu_id':S['bu_id'],
                'cuser':request.user, 'muser':request.user, 'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset'])}
        if R['action'] == 'create':
            if self.filter(
                qset_id = PostData['qset_id'], question_id = PostData['question_id'],
                client_id = PostData['client_id'], bu_id = PostData['bu_id']).exists():
                return {'data':list(self.none()), 'error':'Warning: You are trying to add the same question again!'}
            ID = self.create(**PostData).id

        elif R['action'] == 'edit':
            PostData.pop('cuser')
            PostData.pop('cdtz')
            if updated := self.filter(pk=R['pk']).update(**PostData):
                ID = R['pk']
        else:
            self.filter(pk=R['pk']).delete()
            return {'data':list(self.none())}

        qset =  self.filter(id=ID).annotate(quesname=F('question__quesname')
        ).values('pk', 'seqno', 'quesname', 'answertype', 'min', 'question_id', 'ctzoffset',
                 'max', 'options', 'alerton', 'ismandatory', 'isavpt', 'avpttype') or self.none()
        return {'data':list(qset)}
        
    
    def get_questions_of_qset(self, R):
        if R['qset_id'] in ['None', None, ""]: return self.none()
        qset = self.annotate(quesname = F('question__quesname')).filter(
            qset_id = R['qset_id']).select_related('question').values(
                'pk', 'quesname', 'answertype', 'min', 'max','question_id',
                'options', 'alerton', 'ismandatory', 'seqno', 'ctzoffset', 'isavpt', 'avpttype')
        return qset or self.none()
    

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
            'expirytime', 'planduration','jobname', 'id', 'ctzoffset'
        ).order_by('-mdtz')
        ic(utils.printsql(qset))
        return qset or self.none()

    def get_sitecheckpoints_exttour(self, job, child_jobid = None):
        fields = ['id',
            'breaktime', 'distance', 'starttime', 'expirytime',
            'qsetid', 'jobid', 'assetid', 'seqno', 'jobdesc',
            'bu__buname', 'buid', 'bu__gpslocation', 'endtime', 'duration',
            'qsetname', 'solid']
        qset = self.annotate(
            qsetid = F('qset_id'), assetid = F('asset_id'),
            jobid = F('id'), bu__gpslocation = AsGeoJSON('bu__gpslocation'),
            buid = F('bu_id'),
            breaktime = F('other_info__breaktime'),
            distance=F('other_info__distance'),
            duration = V(None, output_field=models.CharField(null=True)),
            solid = F('bu__solid'),
            qsetname=F('qset__qsetname')
            
        ).filter(parent_id=job['id']).select_related('asset', 'qset',).values(*fields).order_by('seqno')
        if child_jobid: 
            return qset.filter(jobid = child_jobid).values(*fields).order_by('seqno') or self.none()
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
        qset = self.annotate(
            assignedto = Case(
                When(pgroup_id=1, then=Concat(F('people__peoplename'), V(' [PEOPLE]'))),
                When(people_id=1, then=Concat(F('pgroup__groupname'), V(' [GROUP]'))),
            )).filter(
            client_id = S['client_id'],
            bu_id = S['bu_id'],
            identifier = 'PPM',
            enable=True
        ).values('id', 'jobname', 'asset__assetname', 'qset__qsetname', 'assignedto', 'bu__bucode',
                 'uptodate', 'planduration', 'gracetime', 'expirytime', 'fromdate', 'bu__buname')
        ic(qset)
        return qset or self.none()
    
    def handle_save_checkpoint_guardtour(self, request):
        R, S = request.POST, request.session
        """handle post data submitted from geofence add people form"""
        from apps.schedhuler import utils as sutils
        parent_job = self.filter(id = R['parentid']).values().first()
        cdtz = datetime.now(tz = timezone.utc)
        mdtz = datetime.now(tz = timezone.utc)
        checkpoint = {
            'expirytime' : R['expirytime'],
            'qsetid': R['qset_id'],
            'assetid':R['asset_id'],
            'seqno':R['seqno'],
            'qsetname':R['qsetname']
        }
        ic(R)
        if not  R['action'] == 'remove':
            child_job = sutils.job_fields(parent_job, checkpoint)
        try:
            if R['action'] == 'create':
                if self.filter(
                    qset_id = checkpoint['qsetid'], asset_id = checkpoint['assetid'],
                    parent_id = parent_job['id']).exists():
                    return {'data':list(self.none()), 'error':'Warning: Record already added!'}
                ic("creating checkpoint with following data:", child_job)
                ID = self.create(**child_job, cuser = request.user, muser = request.user,
                                 cdtz = cdtz, mdtz = mdtz).id
            elif R['action'] == 'edit':
                if updated := self.filter(pk=R['pk']).update(**child_job, muser = request.user, mdtz = mdtz):
                    ID = R['pk']
                    self.filter(pk=R['parentid']).update(mdtz=datetime.utcnow())
            else:
                self.filter(pk = R['pk']).delete()
                return {'data':list(self.none()),}
            qset = self.filter(pk = ID).values('seqno', 'qset__qsetname', 'asset__assetname', 'expirytime', 'pk', 'asset_id', 'qset_id')
            return {'data':list(qset)}
        except Exception  as e:
            log.critical("something went wrong", exc_info=True)
            return {'data':[], 'error':"Somthing went Wrong!"}
    
    def handle_save_checkpoint_sitetour(self, request):
        R, S = request.POST, request.session
        """handle post data submitted from route plan edit adgn checkpoint form"""
        try:
            mdtz = datetime.now(tz = timezone.utc)
            if R['action'] == 'edit':
                child_job_post_data = {'seqno':R['seqno'], 'qset_id':R['qset_id']}
                if updated := self.filter(id=R['jobid']).update(**child_job_post_data, muser = request.user, mdtz = mdtz):
                    ID = R['jobid']
                    qset = self.get_sitecheckpoints_exttour({'id':R['parent_id']}, ID)
                    return {'data':list(qset)}
                return {'data':[]}
        except Exception  as e:
            log.critical("something went wrong", exc_info=True)
            return {'data':[], 'error':"Somthing went Wrong!"}
    




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
            

    
class LocationManager(models.Manager):
    use_in_migrations = True
    
    def get_locationlistview(self, related, fields, request):
        S = request.session
        P = request.GET['params']
        qset = self.filter(
            ~Q(loccode='NONE'),
            bu_id = S['bu_id'],
            client_id = S['client_id'],
        ).select_related(*related).values(*fields)
        if(P not in ['null', None]):
            P = json.loads(P)
            qset = qset.filter(locstatus = P['status'])
        return qset or self.none()
    
    def get_locations_modified_after(self, mdtz, buid, ctzoffset):
        related = ['client', 'cuser', 'muser', 'parent',  'tenant', 'type', 'bu']
        fields = ['id', 'cdtz', 'mdtz', 'ctzoffset', 'loccode', 'locname', 'enable', 'iscritical', 
               'client_id', 'cuser_id', 'muser_id', 'parent_id',  'tenant_id', 'type_id', 'uuid',
               'gpslocation', 'locstatus',  'bu_id',]
        
        if not isinstance(mdtz, datetime):
            mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        qset = self.select_related(*related).filter(
            Q(mdtz__gte = mdtz) & Q(bu_id__in=[buid])  & Q(enable=True)
            ).values(*fields)
        return qset or self.none()
    
    def filter_for_dd_location_field(self, request, choices=False, sitewise=False):
        S = request.session
        qset = self.filter(
            enable=True,
            client_id = S['client_id'],
            bu_id__in = S['assignedsites'],
        ).order_by('locname')
        if sitewise: qset = qset.filter(bu_id = S['bu_id'])
        if choices: qset = qset.annotate(
            text = Concat(F('locname'), V(' ('), F('loccode'), V(')'))).values_list(
                'id', 'text'
            )
        return qset or self.none()
    
    def get_assets_of_location(self, request):
        R,S = request.GET, request.session
        obj = self.filter(id = R['locationid']).first()
        qset = obj.asset_set.annotate(
            text = Concat(F('assetname'), V(' ('), F('assetcode'), V(')'), output_field=CharField())
        ).filter(bu_id = S['bu_id']).values('id', 'text')
        return qset or self.none()
    
    
class AssetLogManager(models.Manager):
    use_in_migrations = True
    
    def get_asset_logs(self, request):
        R, S = request.GET, request.session

        from apps.core.raw_queries import get_query
        from django.db import connection
        query = get_query('all_asset_status_duration')


        with connection.cursor() as cursor:


            # Fetch the subset of records
            cursor.execute(query % (S['client_id'], S['bu_id']))
            rows = cursor.fetchall()


        data = [
            {
                'assetname': row[1],
                'newstatus': row[2],
                'duration_seconds': row[3],
                'duration_interval':row[4]
                # add more fields as needed
            }
            for row in rows
        ]
        return {
            'data': data,
        }
        