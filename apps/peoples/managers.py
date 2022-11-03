from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.db.models import Q, F, Value as V
from django.db.models.functions import Concat
from django.contrib.gis.db.models.functions import  AsGeoJSON
from django.utils.translation import ugettext_lazy as _
from icecream import ic

class PeopleManager(BaseUserManager):
    use_in_migrations =  True
    fields = ['id', 'peoplecode', 'peoplename', 'loginid', 'isadmin', 'is_staff', 'isverified',
              'enable', 'department_id', 'designation_id', 'peopletype_id', 'client_id', 
              'bu_id', 'cuser_id', 'muser_id', 'reportto_id', 'deviceid', 'enable', 'mobno',
              'cdtz', 'mdtz', 'gender', 'dateofbirth', 'dateofjoin', 'tenant_id', 'ctzoffset']
    related = ['bu', 'client', 'peopletype', 'muser', 'cuser', 'reportto', 'department', 'designation']

    def create_user(self, loginid, password = None, **extra_fields):
        if not loginid:
            raise ValueError("Login id is required for any user!")
        user = self.model(loginid = loginid, **extra_fields)
        user.set_password(password)
        user.save(using = self._db)
        return user

    def create_superuser(self, loginid, password = None, **extra_fields):
        if password is None:
            raise TypeError("Super users must have a password.")
        user = self.create_user(loginid, password, **extra_fields)

        user.is_superuser = True
        user.is_staff     = True
        user.isadmin      = True
        user.isverified  = True
        user.save(using = self._db)
        return user

    def get_people_from_creds(self, loginid, clientcode):
        if qset := self.select_related('client', 'bu').get(
            Q(loginid = loginid) & Q(client__bucode = clientcode)
        ):
            return qset

    def update_deviceid(self, deviceid, peopleid):
        return self.filter(id = peopleid).update(deviceid = deviceid)

    def reset_deviceid(self, peopleid):
        return self.filter(id = peopleid).update(deviceid = "-1")

    def get_people_modified_after(self, mdtz, siteid):
        """
        Returns latest sitepeople
        """
        qset = self.select_related(
            *self.related).filter(
                 Q(bu_id = siteid), Q(mdtz__gte = mdtz)).values(*self.fields).order_by('-mdtz')
        ic(qset.query)
        return qset or self.none()

    def get_emergencycontacts(self, siteid, clientid):
        "returns mobnos of people with given assigned siteid"
        qset = self.filter(bu_id = siteid, client_id = clientid).values_list('mobno', flat = True).exclude(mobno = None)
        return qset or self.none()

    def get_emergencyemails(self, siteid, clientid):
        "returns emails of people with given assigned siteid"
        qset = self.filter(bu_id = siteid, client_id = clientid).values_list('email', flat = True)
        return qset or self.none()
    
    def controlroomchoices(self):
        "returns people whose worktype is in [AO, AM, CR] choices for bu form"
        qset = self.filter(
            Q(designation__tacode__in = ['CR']) |  Q(worktype__tacode__in = ['CR']),
            enable=True,
        ).annotate(text =Concat(F('peoplename'), V(' ('), F('peoplecode'), V(')'))).values_list('id', 'text')
        return qset or self.none()
    
    def get_assigned_sites(self, clientid, peopleid):
        from apps.onboarding.models import Bt
        qset = Bt.objects.filter(id__gte=12, id__lte=150).annotate(
            text = Concat(F('buname'),  V(' ('), F('bucode'), V(')'))).values_list('id', 'text')
        
        return qset



class CapabilityManager(models.Manager):
    use_in_migrations = True
    def get_webparentdata(self):
        return self.filter(cfor= self.pm.Capability.Cfor.WEB, parent__capscode='NONE')

    def get_mobparentdata(self):

        return self.filter(cfor = self.pm.Capability.Cfor.MOB, parent__capscode='NONE')

    def get_repparentdata(self):
        return self.filter(cfor = self.pm.Capability.Cfor.REPORT, parent__capscode='NONE')

    def get_portletparentdata(self):
        return self.filter(cfor = self.pm.Capability.Cfor.PORTLET, parent__capscode='NONE')

    def get_child_data(self, parent, cfor):
        return self.filter(cfor = cfor, parent__capscode = parent) if parent else None
    
    def get_caps(self, cfor):
        qset = self.filter(cfor = cfor).values_list('capscode', 'capsname')
        return qset or self.none()



class PgblngManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'cuser_id', 'muser_id', 'bu_id', 'client_id', 'people_id', 'cdtz', 'mdtz',
              'assignsites_id', 'pgroup_id', 'isgrouplead', 'ctzoffset', 'tenant_id']
    related = ['cuser', 'muser', 'pgroup', 'people', 'client', 'bu']

    def get_modified_after(self, mdtz, peopleid, buid):
        qset = self.select_related(
            *self.related).filter(
                mdtz__gte = mdtz, people_id = peopleid, bu_id = buid).values(*self.fields).order_by('-mdtz')
        return qset or self.none()

    def get_assigned_sitesto_sitegrp(self, id):
        qset = self.select_related('pgroup').filter(pgroup_id = id).annotate(
            buname = F('assignsites__buname'),
            buid = F('assignsites__id'),
        ).values('buname', 'buid')
        ic(qset)
        return qset or self.none()
    
    def get_sitesfromgroup(self, job):
        "return sites under group with given sitegroupid"
        from apps.activity.models import Job
        qset = Job.objects.get_sitecheckpoints_exttour(job)
        if not qset:
            qset = self.annotate(
                gpslocation = AsGeoJSON('assignsites__gpslocation'),
                buname = F('assignsites__buname'), bucode=F('assignsites__bucode'),
                buid = F('assignsites_id'), solid = F('assignsites__solid')
            ).select_related('assignsites', 'identifier').filter(
                pgroup_id = job['sgroup_id']
            ).values('gpslocation', 'bucode', 'buname', 'buid', 'solid')
            if qset:
                for q in qset:
                    q.update(
                        {'seqno':None, 'starttime':None, 'endtime':None, 'qsetid':job['qset_id'],
                        'qsetname':job['qset__qsetname'], 'duration':None, 'expirytime':None,
                        'distance':None, 'jobid':None, 'assetid':1, 'breaktime':None})
        return qset or self.none()
        



class PgroupManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'groupname', 'enable', 'identifier_id', 'ctzoffset',
              'bu_id', 'client_id', 'tenant_id', 'cdtz', 'mdtz']
    related = ['identifier', 'bu', 'client', 'cuser', 'muser']

    def listview(self, request, fields, related, orderby, dir = None, qobjs = None):
        # sourcery skip: assign-if-exp, swap-if-expression
        order = "" if dir == 'asc' else "-"
        if not qobjs:
            objs = self.select_related(
                *related).filter(
                    identifier__tacode = 'SITEGROUP').values(
                        *fields).order_by(f'{order}{orderby}')
        else:
            objs = self.select_related(
                *related).filter(
                    qobjs, identifier__tacode = 'SITEGROUP').values(
                        *fields).order_by(f'{order}{orderby}')

        return objs or self.none()

    def get_groups_modified_after(self, mdtz, buid):
        """
        Return latest group info
        """
        qset = self.select_related(
            *self.related).filter(
                Q(id=1) | Q(mdtz__gte = mdtz) & Q(bu_id = buid) &
                Q(identifier__tacode = "PEOPLEGROUP")).values(
                    *self.fields)
        return qset or None

    def list_view_sitegrp(self, R):
        from apps.core import utils
        qobjs, dir,  fields, length, start = utils.get_qobjs_dir_fields_start_length(R)
        qset = self.filter(
            ~Q(groupname = 'NONE'), 
            enable = True,
            identifier__tacode = 'SITEGROUP',
        ).select_related('identifier').values(*fields).order_by(dir)

        total = qset.count()
        if qobjs:
            filteredqset = qset.filter(qobjs)
            fcount = filteredqset.count()
            filteredqset = filteredqset[start:start+length]
            return total, fcount, filteredqset
        qset = qset[start:start+length]
        return total, total, qset

    def get_assignedsitegroup_forclient(self, clientid):
        qset = self.filter(
            client_id = clientid,
            identifier__tacode = 'SITEGROUP'
            ).values_list('id', 'groupname')
        return qset or self.none()
