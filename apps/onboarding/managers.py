from datetime import datetime
from urllib import request
from django.db import models
from django.db.models import Q, F
import apps.peoples.models as pm
from django.db.models.functions import Concat
from django.db.models import Value as V
from apps.core import utils

class BtManager(models.Manager):
    use_in_migrations = True
    @staticmethod
    def get_people_bu_list(people):
        """
        Returns all BU's assigned to people
        """
        if people and people.people_extras['assignsitegroup']:
            if assigned_sites := people.people_extras['assignsitegroup']:
                if (
                    qset := pm.Pgbelonging.objects.filter(
                        Q(pgroup_id__in = assigned_sites)
                    )
                    .values_list('assignsites', flat = True)
                    .distinct()
                ):
                    return tuple(qset)
            return ""

    def get_all_bu_of_client(self, clientid, type='array'):
        """
        Returns all BU's on given client_id
        """
        rtype = 'bigint[]' if type == "array" else 'jsonb'
        qset = self.raw(
            f"select fn_get_bulist({clientid}, false, true, '{type}'::text, null::{rtype}) as id;")
        return qset[0].id if qset else self.none()
    
    def get_all_sites_of_client(self, clientid):
        """
        Returns all sites of a given clientid
        """
        all_buids = self.get_all_bu_of_client(clientid)
        return self.filter(id__in = all_buids, identifier__tacode = 'SITE') or self.none()
    

    def find_site(self, clientid, sitecode):
        """
        Finds site on given client_id and site_id
        """
        qset = self.filter(
            Q(identifier__tacode = 'SITE') & Q(bucode = sitecode) 
            & ~Q(parent__id = -1) & Q(id__in = self.get_all_bu_of_client(clientid))
        )
        return qset[0] if qset else  self.none()

    def get_sitelist_web(self, clientid, peopleid):
        """
        Return sitelist assigned to peopleid
        considering whether people is admin or not.
        """
        qset = utils.runrawsql('select fn_get_siteslist_web(%s, %s)', [clientid, peopleid])
        return qset or self.none()

    def get_whole_tree(self, clientid):
        """
        Returns bu tree 
        """
        import json
        rtype = 'bigint[]'
        qset_json = self.raw(
            f"select fn_get_bulist({clientid}, true, true, 'array'::text, null::{rtype}) as id;")
        return qset_json[0].id if qset_json else  []

    def getsitelist(self, clientid, peopleid):
        # check if people is admin or not
        try:
            p = pm.People.objects.get(id = peopleid)
        except pm.People.DoesNotExist:
            return self.none()
        else:
            if p.isadmin:
                bulist = self.get_all_bu_of_client(clientid)
                bus = self.filter(id__in = bulist)
                qset = bus.annotate(bu_id = F('id')).filter(identifier__tacode = 'SITE').values(
                    'bu_id', 'bucode', 'butype_id', 'enable', 'cdtz', 'mdtz', 'skipsiteaudit',
                     'buname', 'cuser_id', 'muser_id', 'identifier_id', 'bupreferences'
                )
                return qset or self.none()
            pass
    
    def load_parent_choices(self, request):
        search_term = request.GET.get('search')
        parentid = -1 if request.GET.get('parentid') == 'None' else request.GET.get('parentid')
        buids = utils.runrawsql("select fn_get_bulist(%s, true, true, 'array'::text, null::bigint[]) as buids", [parentid])
        qset = self.filter(id__in=buids[0]['buids']).select_related('identifier', 'parent')
        qset = qset.filter(buname__icontains = search_term) if search_term else qset
        qset = qset.annotate(
            text = Concat(F('buname'), V(" ("), F('identifier__tacode'), V(")"))).exclude(
                identifier__tacode = 'SITE').values('id', 'text')
        return qset or self.none()

    def get_bus_idfs(self, R, request, idf = None):
        S = request.session
        
        bu_ids = self.get_whole_tree(S['client_id'])
        
        fields = R.getlist('fields[]')
        qset = self.filter(
             ~Q(bucode__in=('NONE', 'SPS', 'YTPL')), identifier__tacode = idf, enable = True, id__in = bu_ids).select_related(
                 'parent', 'identifier').annotate(buid = F('id')).values(*fields)
        idfs = self.filter(
             ~Q(identifier__tacode = 'NONE'), ~Q(bucode__in=('NONE', 'SPS', 'YTPL')),id__in = bu_ids ).order_by(
                 'identifier__tacode').distinct(
                     'identifier__tacode').values('identifier__tacode')
        return qset, idfs

    def get_client_list(self, fields, related):
        qset = self.filter(
            identifier__tacode = 'CLIENT').select_related(*related).values(
                *fields).order_by('-mdtz')
        return qset or self.none()


    def handle_bupostdata(self, request):
        "handles post data submitted by editor in client form"
        R, S = request.POST, request.session
        r = {'enable':R['enable'] == '1'}
        PostData = {'bucode':R['bucode'].upper(), 'buname':R['buname'], 'parent_id' : R['parent'], 'identifier_id':R['identifier'],
                    'enable':r['enable'],
                'cuser':request.user, 'muser':request.user, 'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset'])}
        
        if R['action'] == 'create':
            if self.filter(bucode=R['bucode'].upper()).exists():
                return {'data':list(self.none()), 'error':'Bu code already exists'}
            ID = self.create(**PostData).id
        
        elif R['action'] == 'edit':
            PostData.pop('cuser')
            PostData.pop('cdtz')
            updated = self.filter(pk=R['pk']).update(**PostData)
            ic(updated)
            if updated: ID = R['pk']
        else:
            ic(R['pk'])
            self.filter(pk=R['pk']).delete()
            return {'data':list(self.none())}
        
        qset = self.filter(id=ID).values('id', 'bucode', 'buname', 'identifier__tacode', 'identifier_id', 
                 'parent__buname', 'parent_id', 'enable') or self.none()
        return {'data':list(qset)}
        
    
    def handle_adminspostdata(self, request):
        # sourcery skip: use-named-expression
        "handles post data submitted by editor in client form"
        R, S = request.POST, request.session
        r = {'isadmin':R['isadmin'] == '1'}
        PostData = {'peoplecode':R['peoplecode'].upper(), 'peoplename':R['peoplename'], 'bu_id' : 1, 'loginid':R['loginid'],
                    'client_id':R['client_id'] , 'email':R['email'], 'gender':R['gender'],'mobno':R['mobno'], 'isadmin':r['isadmin'], 'dateofbirth':R['dateofbirth'],
                    'dateofjoin':R['dateofjoin'],
                'cuser':request.user, 'muser':request.user, 'cdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset']),
                'mdtz':utils.getawaredatetime(datetime.now(), R['ctzoffset'])}
        
        if not utils.verify_mobno(R['mobno']):
            return {'data':list(self.none()),
                    'fieldErrors':[{'name':'mobno', 'status':"Please Enter Correct Mobile Number!"}]}
        if not utils.verify_emailaddr(R['email']):
            return {'data':list(self.none()),
                    'fieldErrors':[{'name':'email', 'status':"Please Enter Correct Email Address!"}]}
        
        if R['action'] == 'create':
            if pm.People.objects.filter(peoplecode=R['peoplecode'].upper(),  client_id = S['client_id']).exists():
                return {'data':list(self.none()), 'error':'People code already exists'}
            
            if pm.People.objects.filter(loginid = R['loginid'], client_id = S['client_id'] ).exists():
                return {'data':list(self.none()), 'error':'Login id already exists'}
            
            if pm.People.objects.filter(email = R['email'], client_id = S['client_id']).exists():
                return {'data':list(self.none()), 'error':'Email already exists'}
            
            ID = pm.People.objects.create(**PostData).id
        
        elif R['action'] == 'edit':
            PostData.pop('cuser')
            PostData.pop('mdtz')
            updated = pm.People.objects.filter(pk=R['pk']).update(**PostData)
            if updated: ID = R['pk']
        else:
            pm.People.objects.filter(pk=R['pk']).delete()
            return {'data':list(self.none())}
        
        qset = pm.People.objects.filter(id=ID).values(
            'id', 'peoplecode', 'peoplename', 'loginid', 'email',
        'isadmin', 'mobno', 'gender', 'dateofbirth', 'dateofjoin')
        
        if qset:
            user = pm.People.objects.get(id=qset[0]['id'])
            user.set_password(f'{qset[0]["loginid"]}@123')
            user.save()
        return {'data':list(qset)}
        

    def get_listbus(self, request):
        "return list bus for client_form"
        if request.GET.get("id") == "None":
            return self.none()
        qset = self.filter(identifier__tacode='SITE').exclude(bucode__in=['NONE', 'YTPL']).distinct().values(
            'id', 'bucode', 'buname', 'enable', 'parent__buname', 'identifier__tacode', 'parent_id', 'identifier_id').order_by('-mdtz')
        return qset or self.none()
    

    def get_listadmins(self, request):
        "return list admins for client_form"
        if request.GET.get("clientid") in ["None", None]:
            return self.none()
        qset = pm.People.objects.filter(
            isadmin=True, client_id = request.GET.get('clientid'),
            
            ).exclude(peoplecode__in=['NONE', 'SUPERADMIN']).distinct().values(
            'peoplecode', 'peoplename', 'loginid', 'isadmin', 'mobno', 'email',
            'gender', 'id', 'dateofbirth', 'dateofjoin'
        ).order_by('-mdtz')
        return qset or self.none()
    
    def get_allsites_of_client(self, clientid, request=None, fields=None):
        "return all the sites of a client"
        qset = self.get_bus_based_on_idf(clientid, 'SITE', request, fields)
        return qset or self.none()
    
    def get_bus_based_on_idf(self, clientid, idf, request=None, fields=None):
        "return all the bu list based on given identifier of a client"
        if request:
            clientid = request.GET.get('client_id')
            idf = request.GET.get('identifier')
        if clientid not in (None, 'None'):
            buids = utils.runrawsql("select fn_get_bulist(%s, true, true, 'array'::text, null::bigint[]) as buids", [clientid])
            qset = self.filter(id__in=buids[0]['buids']).select_related('identifier', 'parent', 'butype')
            qset = qset.filter(identifier__tacode=idf).exclude(
                    bucode__in=['NONE', 'YTPL']).distinct().values(*fields)
            return qset or self.none()
        return self.none()

    





class TypeAssistManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'tacode', 'taname', 'tatype_id', 'cuser_id', 'muser_id',
              'ctzoffset',
              'bu_id', 'client_id', 'tenant_id', 'cdtz', 'mdtz']
    related = ['cuser', 'muser', 'bu', 'client', 'tatype']

    def get_typeassist_modified_after(self, mdtz, clientid):
        """
        Return latest typeassist data
        """
        if not isinstance(mdtz, datetime):
            mdtz = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        none_entry = self.filter(tacode = 'NONE').values(*self.fields)
        qset = self.select_related(*self.related).filter(
            Q(mdtz__gte = mdtz) & (Q(client_id__in=[clientid]) | Q(cuser__is_superuser=True) | Q(cuser__peoplecode='NONE'))  & Q(enable=True)
            ).values(*self.fields)
        qset = qset.union(none_entry)
        return qset or None
    
    def load_identifiers(self, request):
        search_term = request.GET.get('search')
        qset = self.filter(tatype__tacode='BVIDENTIFIER').annotate(text = F('taname')).exclude(taname='Client').values('text', 'id').distinct()
        qset = qset.filter(taname__icontains = search_term, tatype__tacode='BVIDENTIFIER') if search_term else qset
        return qset or self.none()
    
    def get_escalationlevels(self, request):
        R, S = request.GET, request.session
        if R.get('id') in [None, "None", ""]:
            return self.none()
        ic(R)
        if qobj := self.filter(id=R['id']).first():
            return list(qobj.esc_types.select_related('escalationtemplate', 'assignedperson', 'assignedgroup').values(
                'assignedfor', 'assignedperson__peoplename', 'assignedperson__peoplecode', 
                'assignedgroup__groupname', 'frequency', 'frequencyvalue', 'id', 'level',
                'assignedperson_id', 'assignedgroup_id'
            )) or []
        return []
    
    def filter_for_dd_notifycategory_field(self, request, choices=False, sitewise=False):
        S = request.session
        qset = self.filter(
            client_id__in = [S['client_id'], 1],
            bu_id__in = S['assignedsites'] + [1],
            tatype__tacode = 'NOTIFYCATEGORY',
            enable=True
        )
        ic(qset)
        if sitewise:
            qset = qset.filter(bu_id__in = [S['bu_id'], 1])
        if choices:
            qset = qset.annotate(text = Concat(F('taname'), V(' ('), F('tacode'), V(')'))).values_list(
                'id', 'text'
            )
        return qset or self.none()



class GeofenceManager(models.Manager):
    use_in_migrations: True
    fields = ['id', 'cdtz',  'mdtz', 'ctzoffset', 'gfcode', 'gfname', 'alerttext', 'geofencecoords', 
              'enable',  'alerttogroup_id', 'alerttopeople_id', 'bu_id', 'client_id', 'cuser_id', 'muser_id']
    related = ['cuser', 'muser', 'bu', 'client']

    def get_geofence_list(self, fields, related, session):
        qset = self.select_related(*related).filter(
             enable = True, client_id = session['client_id'],
        ).values(*fields)
        return qset or self.none()

    def get_geofence_json(self, pk):
        from django.contrib.gis.db.models.functions import AsGeoJSON
        obj = self.annotate(geofencejson = AsGeoJSON('geofence')).get(id = pk).geofencejson
        obj = utils.getformatedjson(jsondata = obj, rettype = str)
        return obj or self.none()

    def get_gfs_for_siteids(self, siteids):
        from django.contrib.gis.db.models.functions import AsGeoJSON
        import json
        if qset := self.annotate(geofencecoords = AsGeoJSON('geofence')).select_related(*self.related).filter(bu_id__in = siteids).values(*self.fields):
            geofencestring = ""
            for obj in qset:
                geodict = json.loads(obj['geofencecoords'])
                for lng, lat in  geodict['coordinates'][0]:
                    geofencestring += f'{lat},{lng}|'
                obj['geofencecoords'] = geofencestring
            return qset
        return self.none()

    def getPeoplesGeofence(self, request):
        
        searchterm = request.GET.get('search')
        qset = pm.People.objects.filter(
            client_id = request.session['client_id'],
            enable=True, isverified=True,
        )
        
        qset = qset.filter(peoplename__icontains = searchterm) if searchterm else qset
        qset = qset.annotate(
            text = Concat('peoplename', V(' ('), 'peoplecode', V(')'))
        ).values('text', 'id').distinct()
        return qset or self.none()  
    
    
class ShiftManager(models.Manager):
    use_in_migrations: True
    
    def shift_listview(self, request, related, fields):
        S = request.session
        return self.filter(
            ~Q(shiftname='NONE'),
            client_id = S['client_id'],
            bu_id = S['bu_id'],
        ).annotate(
        dsgn = Concat(F('designation__taname'), V(' ('), F('designation__tacode'), V(')'))    
        ).select_related('designation').values(
            'id', 'shiftname', 'dsgn', 'starttime',
            'endtime', 'nightshiftappicable'
        ) or self.none()