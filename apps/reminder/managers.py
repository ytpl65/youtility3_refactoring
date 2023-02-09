from django.db import models
from django.db.models import Q, F, Count, Case, When
from datetime import datetime, timedelta, timezone


class ReminderManager(models.Manager):
    use_in_migrations = True
    
    
    def get_all_due_reminders(self):
        qset = self.select_related(
            'bt', 'job', 'asset', 'qset', 'pgroup', 'people'
        ).annotate(
            rdate = F('reminderdate') + timedelta(minutes=F('ctzoffset')),
            pdate = F('plandatetime') + timedelta(minutes=F('ctzoffset'))
        ).filter(
            reminderdate__gt = datetime.now(timezone.utc),
            status__ne = 'SUCCESS'
        ).values(
            'rdate', 'pdate', 'job__jobname', 'bu__buname', 'asset__assetname', 'job__jobdesc',
            'qset__qsetname', 'priority', 'reminderin', 'people__peoplename', 'cuser__peoplename',
            'group__groupname', 'people_id', 'group_id', 'cuser_id', 'muser_id', 'mailsids', 
            'muser__peoplename'
        ).distinct()
        return qset or self.none()