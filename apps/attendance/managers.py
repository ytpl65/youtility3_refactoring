from datetime import timedelta
import imp
from django.db import models
from apps.activity.models import Attachment
Q = models.Q
class PELManager(models.Manager):
    use_in_migrations = True
    
    def get_current_month_sitevisitorlog(self, peopleid):
        from datetime import datetime
        qset = self.select_related('bu', 'peventtype').filter(
            ~Q(people_id = -1), peventtype__tacode = 'AUDIT',
            people_id = peopleid, datefor__gte = datetime.date() - timedelta(days=7))
        return qset or self.none()
    
    def get_people_attachment(self, pelogid):
        return self.raw(
            """
            SELECT peopleeventlog.people_id, peopleeventlog.id
            FROM peopleeventlog
            INNER JOIN typeassist ON typeassist.id= peopleeventlog.peventtype_id AND typeassist.tacode IN ('MARK', 'SELF', 'TAKE', 'AUDIT')
            LEFT JOIN attachment ON attachment.owner= peopleeventlog.id
            WHERE 1=1
                AND attachment.filename NOT iLIKE '%%.csv' AND attachment.filename NOT iLIKE '%%.txt'
                AND attachment.filename NOT iLIKE '%%.mp4' AND attachment.filename NOT iLIKE '%%.3gp'
                AND peopleeventlog.id= %s
            """,params=[pelogid]
        )[0] or self.none()
    
    def update_fr_results(self, result, id, peopleid):
        return self.filter(
            id=id
        ).update(peventlogextras = result, people_id = peopleid)