from datetime import timedelta, datetime, date
from django.db import models
from django.contrib.gis.db.models.functions import AsGeoJSON, AsWKT
from apps.core import utils
from apps.activity.models import Attachment
from itertools import chain

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
        if obj := self.filter(uuid=uuid).using(db):
            extras = obj[0].peventlogextras
            if obj[0].punchintime:
                extras['verified_in'] = result['verified']
                extras['distance_in'] = result['distance']
            if obj[0].punchouttime:
                extras['verified_out'] = result['verified']
                extras['distance_out'] = result['distance']
            obj[0]['peventlogextras'] = extras
            obj[0].facerecognitionin = extras['verified_in']
            obj[0].facerecognitionout = extras['verified_out']
            obj[0].people_id = peopleid
            obj[0].save()
            return True
        return False
    
    def get_fr_status(self, R):
        "return fr images and status"
        qset = self.filter(id=R['id']).values('uuid', 'peventlogextras')
        atts = Attachment.objects.filter(
            owner=qset[0]['uuid']).values(
                'filepath', 'filename', 'attachmenttype', 'datetime', 'gpslocation')
        if atts:
            fr_data = list(chain(qset, atts))
            return fr_data
        return list(self.none)
        
    
    

    def get_lastmonth_conveyance(self, R):
        now = datetime.now()
        qset = self.select_related('bu', 'people').filter(
                peventtype__tacode = 'CONVEYANCE',
                punchintime__date__gte = (now - timedelta(days = 30)).date()
            ).exclude(endlocation__isnull = True).values(*R.getlist('fields[]'))
        return qset or self.none()

    def getjourneycoords(self, id):
        import json
        qset = self.annotate(
            path = AsGeoJSON('journeypath')).filter(
                id = id).values('path', 'punchintime', 'punchouttime', 'deviceid', 'expamt', 'accuracy',
                    'people__peoplename', 'people__peoplecode', 'distance', 'duration', 'transportmodes')
        for obj in qset:
            ic(obj['path'])
            geodict = json.loads(obj['path'])
            coords = [{'lat':lat, 'lng':lng} for lng, lat in geodict['coordinates']]
            obj['path'] = coords
            coords = []
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
    
    
    
        

