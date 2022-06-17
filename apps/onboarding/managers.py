from django.db import models
from django.db.models import Q, F
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
            f"select fn_get_bulist({clientid}, false, true, '{type}'::text, null::{rtype}) as id;")
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
    
    def getsitelist(self, clientid, peopleid):
        #check if people is admin or not
        try:
            p = pm.People.objects.get(id = peopleid)
        except pm.People.DoesNotExist:
            return self.none()
        else:
            if p.isadmin:
                bulist = self.get_bu_list_ids(clientid)
                bus = self.filter(id__in = bulist)
                qset = bus.annotate(bu_id = F('id')).filter(identifier__tacode = 'SITE').values(
                    'bu_id', 'bucode', 'butype_id', 'enable', 'cdtz', 'mdtz', 'skipsiteaudit',
                     'buname', 'cuser_id', 'muser_id', 'identifier_id'
                )
                return qset or self.none()
            else:   
                pass
    
    
    

    def get_bus_idfs(self, R, idf=None):
        # qobjs, dir,  fields, length, start = utils.get_qobjs_dir_fields_start_length(R)
        # qset=self.filter(
        #     ~Q(bucode__in=('NONE', 'SPS', 'YTPL')), identifier__tacode = idf, enable=True).select_related(
        #         'parent', 'identifier').annotate(buid = F('id')).values(*fields).order_by(dir)
        # idfs = self.filter(
        #     ~Q(identifier__tacode = 'NONE'), ~Q(bucode__in=('NONE', 'SPS', 'YTPL'))).order_by(
        #         'identifier__tacode').distinct(
        #             'identifier__tacode').values('identifier__tacode')
        # total = qset.count()
        
        # if qobjs:
        #     filteredqset = qset.filter(qobjs)
        #     fcount = filteredqset.count()
        #     filteredqset = filteredqset[start:start+length]
        #     return total, fcount, filteredqset, idfs
        # qset = qset[start:start+length]
        # return total, total, qset, idfs
        fields = R.getlist('fields[]')
        qset=self.filter(
             ~Q(bucode__in=('NONE', 'SPS', 'YTPL')), identifier__tacode = idf, enable=True).select_related(
                 'parent', 'identifier').annotate(buid = F('id')).values(*fields)
        idfs = self.filter(
             ~Q(identifier__tacode = 'NONE'), ~Q(bucode__in=('NONE', 'SPS', 'YTPL'))).order_by(
                 'identifier__tacode').distinct(
                     'identifier__tacode').values('identifier__tacode')
        return qset, idfs

    
    
        


    

    
    
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
    


class GeofenceManager(models.Manager):
    use_in_migrations: True
    fields = ['id', 'cdtz',  'mdtz', 'ctzoffset', 'gfcode', 'gfname', 'alerttext', 'geofencecoords', 
              'enable',  'alerttogroup_id', 'alerttopeople_id', 'bu_id', 'client_id', 'cuser_id', 'muser_id']
    related = ['cuser', 'muser', 'bu', 'client']
    
    def get_geofence_list(self, fields, related, session):
        qset = self.select_related(*related).filter(
            ~Q(gfcode='NONE'), enable=True, client_id=session['client_id'],
        ).values(*fields)
        return qset or self.none()
    
    def get_geofence_json(self, pk):
        from django.contrib.gis.db.models.functions import AsGeoJSON
        obj = self.annotate(geofencejson = AsGeoJSON('geofence')).get(id = pk).geofencejson
        obj = utils.getformatedjson(jsondata = obj, rettype=str)
        return obj or self.none()
    
    def get_gfs_for_siteids(self, siteids):
        from django.contrib.gis.db.models.functions import AsGeoJSON
        import json
        if qset := self.annotate(geofencecoords=AsGeoJSON('geofence')).select_related(*self.related).filter(bu_id__in=siteids).values(*self.fields):
            geofencestring = ""
            for obj in qset:
                geodict = json.loads(obj['geofencecoords'])
                for lng, lat in  geodict['coordinates'][0]:
                    geofencestring+=f'{lat},{lng}|'
                obj['geofencecoords'] = geofencestring
            return qset
        return self.none()
    