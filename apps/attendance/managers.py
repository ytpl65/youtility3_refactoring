from datetime import timedelta
from django.db import models
Q = models.Q
class PELManager(models.Manager):
    use_in_migrations = True

    def get_current_month_sitevisitorlog(self, peopleid):
        from datetime import datetime
        qset = self.select_related('bu', 'peventtype').filter(
            ~Q(people_id = -1), peventtype__tacode = 'AUDIT',
            people_id = peopleid, datefor__gte = datetime.date() - timedelta(days = 7))
        return qset or self.none()

    def get_people_attachment(self, pelogid, db = None):
        return self.raw(
            """
            SELECT peopleeventlog.people_id, peopleeventlog.id, peopleeventlog.uuid
            FROM icici_django.peopleeventlog
            INNER JOIN typeassist ON typeassist.id= peopleeventlog.peventtype_id AND typeassist.tacode IN ('MARK', 'SELF', 'TAKE', 'AUDIT')
            LEFT JOIN attachment ON attachment.owner= peopleeventlog.uuid::text
            WHERE 1 = 1
                AND attachment.filename NOT iLIKE '%%.csv' AND attachment.filename NOT iLIKE '%%.txt'
                AND attachment.filename NOT iLIKE '%%.mp4' AND attachment.filename NOT iLIKE '%%.3gp'
                AND peopleeventlog.uuid= %s
            """,params=[pelogid]
        )[0] or self.none()

    def update_fr_results(self, result, id, peopleid, db):
        return self.filter(
            id = id
        ).using(db).update(peventlogextras = result, people_id = peopleid)

    def get_people_attachment(self, pelogid, db):
        pass

    def get_lastmonth_conveyance(self, R):
        from datetime import datetime
        now = datetime.now()
        qset = self.select_related('bu', 'people').filter(
                peventtype__tacode = 'CONVEYANCE',
                punchintime__date__gte = (now - timedelta(days = 30)).date()
            ).exclude(endlocation__isnull = True).values(*R.getlist('fields[]'))
        return qset or self.none()

    def getjourneycoords(self, id):
        from django.contrib.gis.db.models.functions import AsGeoJSON
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

