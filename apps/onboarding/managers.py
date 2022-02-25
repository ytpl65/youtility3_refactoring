from django.db import models
from django.db.models import Q
import apps.onboarding.models as om
import apps.peoples.models as pm


class BtManager(models.Manager):
    use_in_migrations = True

    def get_bu_list(self, clientid, butype=None):
        '''
        returns sites/zones/branches/...on given clientid
        '''
        if not butype and clientid:
            if (
                qset := self.filter(~Q(butype__tacode='CLIENT') & Q(parent_id=clientid))
                .values_list('id', flat=True)
                .order_by('butype')
            ):
                result = map(str, qset)
                return ','.join(result)
        elif clientid:
            if (
                qset := self.filter(Q(butype=butype) & Q(parent_id=clientid))
                .values_list('id', flat=True)
                .distinct()
                .order_by('bucode')
            ):
                return ','.join(list(qset))
        else: return 
    
    def get_people_bu_list(self, people):
        '''
        return bu list [ids...] assigned to people
        '''
        if people and people.people_extras['assignsitegroup']:
            import json
            if assigned_sites := json.loads(
                people.people_extras['assignsitegroup']
            ):
                if (
                    qset := pm.Pgbelonging.objects.filter(
                        Q(group_id__in=assigned_sites)
                    )
                    .values_list('assignsites', flat=True)
                    .distinct()
                ):
                    return ','.join(list(qset))
            return ""
        
    def get_bu_list_ids(self, clientid):
        return list_str.split(',') if (list_str := self.get_bu_list(clientid)) else []