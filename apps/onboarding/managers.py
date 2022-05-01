from django.db import models
from django.db.models import Q
import apps.onboarding.models as om
import apps.peoples.models as pm
from apps.core import utils


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
            f"select fn_get_bulist({clientid}, true, false, '{type}'::text, null::{rtype}) as id;")
        return qset[0].id if qset else self.none()
    
        
    def find_site(self, clientid, sitecode):
        """
        Finds site on given client_id and site_id
        """
        qset = self.filter(
            Q(identifier__tacode = 'SITE') & Q(bucode = sitecode) 
            & ~Q(parent__id = -1) & Q(id__in = self.get_bu_list_ids(clientid))
        )
        return qset[0] if qset else  self.none()
    
    
    def get_sitelist_web(self, clientid, peopleid):
        """
        Return sitelist assigned to peopleid
        considering whether people is admin or not.
        """
        qset = self.raw(f"select fn_get_siteslist_web({clientid}, {peopleid}) as id")
        return qset or self.none()
    
    
    def get_whole_tree(self, clientid):
        """
        Returns bu tree 
        """
        import json
        rtype = 'bigint[]'
        qset_json = self.raw(
            f"select fn_get_bulist({clientid}, true, true, 'array'::text, null::{rtype}) as id;")
        return json.loads(qset_json[0].id if qset_json else '{}')  
    

    def get_bus_idfs(self, idf=None, qobjs=None):
        fields = ['buname', 'parent__buname', 'identifier__tacode']
        if not qobjs:

            if not idf: idf = 'SITE'
            qset = self.filter(~Q(bucode__in=('NONE', 'SPS', 'YTPL')), enable=True).select_related('parent', 'identifier')
            idfs =  qset.filter(
                ~Q(identifier__tacode = 'NONE'), identifier__tacode=idf).distinct(
                        'mdtz', 'identifier').values(
                            'identifier__tacode')
            return qset.values(*fields) or self.none(), idfs or self.none()
        else:
            if not idf: idf = 'SITE'
            qset = self.filter(qobjs, ~Q(bucode__in=('NONE', 'SPS', 'YTPL')), enable=True).select_related('parent', 'identifier')
            idfs =  qset.filter(
                ~Q(identifier__tacode = 'NONE'), identifier__tacode=idf).distinct(
                        'mdtz', 'identifier').values(
                            'identifier__tacode')
            return qset.values(*fields) or self.none(), idfs or self.none()

    
    def get_bus_idfs(self, R, idf=None, qobjs=None):
        if R.get('search[value]'):
            ic("searched")
            qobjs = utils.searchValue2(R.getlist('fields[]'), R['search[value]'])
            ic(qobjs)
        
        orderby, fields = R.getlist('order[0][column]'), R.getlist('fields[]')
        length, start = int(R['length']), int(R['start'])
        if orderby:
            key = R[f'columns[{orderby}][data]']
            dir = f"-{key}" if R['order[0][dir]'] == 'desc' else f"{key}"
        else:
            dir = "-mdtz"
        qset=self.filter(~Q(bucode__in=('NONE', 'SPS', 'YTPL')), enable=True).select_related('parent', 'identifier').values(*fields).order_by(dir)
        idfs = qset.filter(~Q(identifier__tacode = 'NONE'), identifier__tacode=idf).values('tacode')
        total = qset.count()
        
        if qobjs:
            filteredqset = qset.filter(qobjs)
            idfs = filteredqset.filter(~Q(identifier__tacode = 'NONE'), identifier__tacode=idf).values('idfs')
            fcount = filteredqset.count()
            filteredqset = filteredqset[start:start+length]
            return total, fcount, filteredqset, idfs
        qset = qset[start:start+length]
        return total, total, qset, idfs



    

    
    
class TypeAssistManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'tacode', 'taname', 'tatype_id', 'cuser_id', 'muser_id',
              'ctzoffset',
              'bu_id', 'client_id', 'tenant_id', 'cdtz', 'mdtz']
    related = ['cuser', 'muser', 'bu', 'client','tatype']
    
    def get_typeassist_modified_after(self, mdtz, clientid):
        """
        Return latest typeassist data
        """
        from datetime import datetime
        if not isinstance(mdtz, datetime):
            mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        
        qset = self.select_related(*self.related).filter(
            ~Q(id=1) & Q(mdtz__gte = mdtz) & Q(client_id__in = [clientid])
        ).values(*self.fields)
        return qset or None