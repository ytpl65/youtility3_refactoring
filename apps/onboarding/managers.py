from django.db import models
from django.db.models import Q
import apps.onboarding.models as om
import apps.peoples.models as pm


class BtManager(models.Manager):
    use_in_migrations = True
    def get_people_bu_list(self, people):
        """
        Returns all BU's assigned to people
        """
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

        
    def get_bu_list_ids(self, clientid, type='array'):
        """
        Returns all BU's on given client_id
        """
        rtype = 'bigint[]' if type == "array" else 'jsonb'
        qset = self.raw(
            f"select fn_get_bulist({clientid}, true, false, {type}::text, null::{rtype}) as id;")
        return qset[0].id if qset else None
    
        
    def find_site(self, clientid, sitecode):
        """
        Finds site on given client_id and site_id
        """
        qset = self.filter(
            Q(identifier__tacode = 'SITE') & Q(bucode = sitecode) 
            & ~Q(parent__id = -1) & Q(id__in = self.get_bu_list_ids(clientid))
        )
        return qset[0] if qset else  None
    
    
    def get_sitelist_web(self, clientid, peopleid):
        """
        Return sitelist assigned to peopleid
        considering whether people is admin or not.
        """
        qset = self.raw(f"select fn_get_siteslist_web({clientid}, {peopleid})")
        return qset if qset else None