from datetime import timedelta, datetime, date
from django.db import models
from django.contrib.gis.db.models.functions import AsGeoJSON, AsWKT
from apps.core import utils
from apps.activity.models import Attachment
from apps.peoples.models import Pgbelonging
from itertools import chain
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
        log.info('update_fr_results started results:%s', result)
        if obj := self.filter(uuid=uuid).using(db):
            log.info('retrived obj punchintime: %s and punchoutime: %s', obj[0].punchintime, obj[0].punchouttime)
            extras = obj[0].peventlogextras
            if obj[0].punchouttime:
                log.info('no punchintime found')
                extras['verified_out'] = result['verified']
                extras['distance_out'] = result['distance']
            else:
                extras['verified_in'] = result['verified']
                extras['distance_in'] = result['distance']
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
        return list(self.none)
    
    def get_peopleevents_listview(self, related,fields,request):
        R, S = request.GET, request.session
        P = json.loads(R['params'])
        ic(P)
        qset = self.select_related(*related).filter(
            bu_id__in = S['assignedsites'],
            client_id = S['client_id'],
            datefor__gte = P['from'],
            datefor__lte =P['to'],
            peventtype__tacode__in = ['SELF', 'SELFATTENDANCE', 'MARK', 'MRKATTENDANCE']
        ).exclude(id=1).values(*fields).order_by('-datefor')
        return qset or self.none()
    
    

    def get_lastmonth_conveyance(self, R):
        now = datetime.now()
        qset = self.select_related('bu', 'people').filter(  
                peventtype__tacode = 'CONVEYANCE',
                punchintime__date__gte = (now - timedelta(days = 30)).date()
            ).exclude(endlocation__isnull = True).values(*R.getlist('fields[]')).order_by('-punchintime')
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
            bu_id = S['bu_id'],
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
            bu_id = S['bu_id'],
            client_id = S['client_id'],
            datefor__gte = pd1,
            datefor__lte = pd2,
            peventtype__tacode__in = ['SELF', 'SELFATTENDANCE']
        ).count() or 0
    
    def get_attendance_history(self, mdtz, people_id, bu_id, client_id, ctzoffset):
        if not isinstance(mdtz, datetime):
            mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        qset = self.filter(
            datefor__gte = mdtz,
            people_id = people_id,
            bu_id = bu_id,
            client_id = client_id,
            peventtype__tacode__in = ['SELF', 'MARK']
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
        ).select_related('people', 'bu').values(
            'id', 'ctzoffset', 'people__peoplename', 'cdtz',
            'people__peoplecode', 'people__mobno', 'people__email',
            'bu__buname'
        )
        return qset or self.none()