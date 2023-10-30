from datetime import timedelta, datetime, date
from django.db import models
from django.contrib.gis.db.models.functions import AsGeoJSON, AsWKT
from apps.core import utils
from apps.activity.models import Attachment, Jobneed
from apps.peoples.models import Pgbelonging
from django.db.models import Case, When, Value as V, CharField, F
from django.db.models.functions import Cast
from itertools import chain
from django.utils.dateparse import parse_date
from django.utils.dateparse import parse_date
import json
import logging
log = logging.getLogger('__main__')

Q = models.Q
class PELManager(models.Manager):
    use_in_migrations = True

    def get_current_month_sitevisitorlog(self, peopleid):
        qset = self.select_related('bu', 'peventtype').filter(
            ~Q(people_id = -1), peventtype__tacode = 'AUDIT',
            people_id = peopleid, datefor__gte = datetime.date() - timedelta(days = 7))
        return qset or self.none()

    def get_people_attachment(self, pelogid, db = None):
        return self.raw(
            """
            SELECT peopleeventlog.people_id, peopleeventlog.id, peopleeventlog.uuid
            FROM peopleeventlog
            INNER JOIN typeassist ON typeassist.id= peopleeventlog.peventtype_id AND typeassist.tacode IN ('MARK', 'SELF', 'TAKE', 'AUDIT')
            LEFT JOIN attachment ON attachment.owner= peopleeventlog.uuid::text
            WHERE 1 = 1
                AND attachment.filename NOT iLIKE '%%.csv' AND attachment.filename NOT iLIKE '%%.txt'
                AND attachment.filename NOT iLIKE '%%.mp4' AND attachment.filename NOT iLIKE '%%.3gp'
                AND peopleeventlog.uuid= %s
            """,params=[pelogid]
        )[0] or self.none()

    def update_fr_results(self, result, uuid, peopleid, db):
        log.info('update_fr_results started results:%s'
                 , result)
        if obj := self.filter(uuid=uuid).using(db):
            log.info('retrived obj punchintime: %s and punchoutime: %s', obj[0].punchintime, obj[0].punchouttime)
            extras = obj[0].peventlogextras
            if obj[0].punchintime and extras['distance_in'] is None:
                extras['verified_in'] = result['verified']
                extras['distance_in'] = result['distance']
            elif obj[0].punchouttime and extras['distance_out'] is None:
                log.info('no punchintime found')
                extras['verified_out'] = result['verified']
                extras['distance_out'] = result['distance']

            obj[0].peventlogextras = extras
            obj[0].facerecognitionin = extras['verified_in']
            obj[0].facerecognitionout = extras['verified_out']
            obj[0].save()
            return True
        return False
    
    def get_fr_status(self, R):
        "return fr images and status"
        qset = self.filter(id=R['id']).values('uuid', 'peventlogextras')
        if atts := Attachment.objects.filter(
            owner=qset[0]['uuid']).values(
                'filepath', 'filename', 'attachmenttype', 'datetime', 'gpslocation'):
            return list(chain(qset, atts))
        return list(self.none())
    
    def get_peopleevents_listview(self, related,fields,request):
        R, S = request.GET, request.session
        P = json.loads(R.get('params'))
        qset = self.select_related(*related).annotate(
            sL = AsGeoJSON('startlocation'), eL = AsGeoJSON('endlocation')
            ).filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            datefor__gte = P['from'],
            datefor__lte =P['to'],
            peventtype__tacode__in = ['SELF', 'SELFATTENDANCE', 'MARK', 'MRKATTENDANCE']
        ).exclude(id=1).values(*fields).order_by('-datefor')
        return qset or self.none()

    def get_lastmonth_conveyance(self, request, fields, related):
        R, S = request.GET, request.session
        P = json.loads(R['params'])
        qset = self.select_related('bu', 'people').annotate(
            start = AsGeoJSON('startlocation'),
            end = AsGeoJSON('endlocation')
            ).filter(  
                peventtype__tacode = 'CONVEYANCE',
                punchintime__date__gte = P['from'],
                punchintime__date__lte = P['to'],
                client_id = S["client_id"]
            ).exclude(endlocation__isnull = True).select_related(*related).values(*fields).order_by('-punchintime')
        return qset or self.none()

    def getjourneycoords(self, id):
        import json
        qset = self.annotate(
            path = AsGeoJSON('journeypath')).filter(
                id = id).values('path', 'punchintime', 'punchouttime', 'deviceid', 'expamt', 'accuracy',
                    'people__peoplename', 'people__peoplecode', 'distance', 'duration', 'transportmodes')
        for obj in qset:
            if(obj['path']):
                ic(obj['path']) 
                geodict = json.loads(obj['path'])
                coords = [{'lat':lat, 'lng':lng} for lng, lat in geodict['coordinates']]
                waypoints = utils.orderedRandom(coords[1:-1], k=25)
                obj['path'] = coords
                obj['waypoints'] = waypoints
                coords, waypoints = [], []
            else: return self.none()
        return qset or self.none()
    
    
    def get_geofencetracking(self, request):
        "List View"
        qobjs, dir,  fields, length, start = utils.get_qobjs_dir_fields_start_length(request.GET)
        last8days = date.today() - timedelta(days=8)
        qset = self.annotate(
            slocation = AsWKT('startlocation'),
            elocation = AsWKT('endlocation'),
            ).filter(
            peventtype__tacode = 'GEOFENCE',
            datefor__gte = last8days,
            bu_id = request.session['bu_id']
        ).select_related(
            'people', 'peventtype', 'geofence').values(*fields).order_by(dir)
        total = qset.count()
        if qobjs:
            filteredqset = qset.filter(qobjs)
            fcount = filteredqset.count()
            filteredqset = filteredqset[start:start+length]
            return total, fcount, filteredqset
        qset = qset[start:start+length]
        return total, total, qset
    
    
    def get_sos_count_forcard(self, request):
        R, S = request.GET, request.session
        pd1 = R.get('from', datetime.now().date())
        pd2 = R.get('upto', datetime.now().date())
        return self.filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            peventtype__tacode='SOS',
            datefor__gte = pd1,
            datefor__lte = pd2
        ).count() or 0

    def get_frfail_count_forcard(self, request):
        R, S = request.GET, request.session
        pd1 = R.get('from', datetime.now().date())
        pd2 = R.get('upto', datetime.now().date())
        return self.filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            datefor__gte = pd1,
            datefor__lte = pd2,
            peventtype__tacode__in = ['SELF', 'SELFATTENDANCE', 'MARKATTENDANCE', "MARK"]
        ).exclude(id=1).count() or 0
    
    def get_peopleeventlog_history(self, fromdate, todate, people_id, bu_id, client_id, ctzoffset, peventtypeid):
        qset = self.filter(
            datefor__gte = fromdate,
            datefor__lte = todate,
            people_id = people_id,
            bu_id = bu_id,
            client_id = client_id,
            peventtype_id__in = [peventtypeid]
        ).select_related('people', 'bu', 'client', 'verifiedby', 'peventtype', 'geofence', 'shift').order_by('-datefor').values(
            'uuid', 'people_id', 'client_id', 'bu_id','shift_id', 'verifiedby_id', 'geofence_id', 'id',
            'peventtype_id', 'transportmodes', 'punchintime', 'punchouttime', 'datefor', 'distance',
            'duration', 'expamt', 'accuracy', 'deviceid', 'startlocation', 'endlocation', 'ctzoffset',
            'remarks', 'facerecognitionin', 'facerecognitionout', 'otherlocation', 'reference'
        )
        return qset or self.none()
    
    def get_sos_listview(self, request):
        R, S = request.GET, request.session
        P = json.loads(R['params'])
        qset = self.filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            peventtype__tacode='SOS',
            datefor__gte = P['from'],
            datefor__lte = P['to']
        ).select_related('people', 'bu', 'peventtype').values(
            'id', 'ctzoffset', 'people__peoplename', 'cdtz', 'uuid',
            'people__peoplecode', 'people__mobno', 'people__email',
            'bu__buname'
        )
        uuids = qset.annotate(owner_uuid = Cast('uuid', output_field=models.CharField())).values_list(
            'owner_uuid', flat=True
        )
        from apps.activity.models import Attachment
        att_qset = Attachment.objects.get_attforuuids(uuids).values('filepath', 'filename')
        merged_qset = [{**obj1, **obj2} for obj1, obj2 in zip(qset, att_qset)]
        return merged_qset or self.none()
    
    def get_people_event_log_punch_ins(self, datefor, buid):
        given_date = parse_date(datefor)
        previous_date = given_date - timedelta(days=1) 
        qset = self.filter(
            datefor__range = (previous_date, given_date),
            punchouttime__isnull = True,
            bu_id = buid,
            peventtype__tacode__in = ['MARK', 'MARKATTENDANCE']
        ).select_related(
            'client', 'bu', 'shift', 'verifiedby',
            'geofence', 'peventtype'
            ).values(
            'uuid', 'people_id', 'client_id', 'bu_id','shift_id', 'verifiedby_id', 'geofence_id', 'id',
            'peventtype_id', 'transportmodes', 'punchintime', 'punchouttime', 'datefor', 'distance',
            'cuser_id', 'muser_id', 'cdtz', 'mdtz', 'ctzoffset',
            'duration', 'expamt', 'accuracy', 'deviceid', 'startlocation', 'endlocation', 
            'remarks', 'facerecognitionin', 'facerecognitionout', 'otherlocation', 'reference', 'tenant_id'
        ).order_by('punchintime')
        if qset:
             for entry in qset:
                entry['transportmodes'] = 'NONE'
        return qset or []
    
    def get_diversion_countorlist(self, request, count=False):
        R,S = request.GET, request.session
        pd1 = R.get('from', datetime.now().date())
        pd2 = R.get('upto', datetime.now().date())
        fields = [
            'people__peoplename', 'start_gps', 'end_gps','reference',
            'datefor' ,'punchintime', 'punchouttime', 'ctzoffset',
            'id']
        qset = self.select_related('people').filter(
            Q(startlocation__isnull=False),
            peventtype__tacode='DIVERSION',
            datefor__gte = pd1,
            datefor__lte = pd2,
            bu_id__in = S['assignedsites']
        ).annotate(
        start_gps = AsGeoJSON('startlocation'),
        end_gps = AsGeoJSON('endlocation')).values(*fields)
        return list(qset) or []

    def get_sitecrisis_types(self):
        from apps.onboarding.models import TypeAssist
        qset =  TypeAssist.objects.filter(
            tatype__tacode = 'SITECRISIS'
        ).select_related('tatype').values_list('tacode', flat=True)
        return qset or []
    
    def get_sitecrisis_countorlist(self, request, count=False):
        R,S = request.GET, request.session
        pd1 = R.get('from', datetime.now().date())
        pd2 = R.get('upto', datetime.now().date())
        
        pel_qset = self.select_related('people', 'bu').filter(
            Q(startlocation__isnull=False),
            peventtype__tacode__in=self.get_sitecrisis_types(),
            datefor__gte = pd1,
            datefor__lte = pd2,
            bu_id__in = S['assignedsites']
        ).annotate(
        gps = AsGeoJSON('startlocation'),
        )
        
        fields = [
            'people__peoplename','people__peoplecode', 'gps', 'reference',
            'cdtz' ,'bu__buname', 'bu__bucode', 'ctzoffset', 'people__mobno',
            'people__email', 'uuid',
            'id']
        pel_qset = pel_qset.values(*fields)
        uuids = pel_qset.annotate(owner_uuid = Cast('uuid', output_field=models.CharField())).values_list(
            'owner_uuid', flat=True
        )
        ic(pel_qset)
        from apps.activity.models import Attachment
        att_qset = Attachment.objects.get_attforuuids(uuids).values('filepath', 'filename')
        merged_qset = [{**obj1, **obj2} for obj1, obj2 in zip(pel_qset, att_qset)]
        if count: return len(pel_qset) or 0
        return merged_qset or []
