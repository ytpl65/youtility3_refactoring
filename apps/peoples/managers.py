from xmlrpc.client import UNSUPPORTED_ENCODING
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from icecream import ic

class PeopleManager(BaseUserManager):
    use_in_migrations =  True
    fields = ['id', 'peoplecode', 'peoplename', 'loginid', 'isadmin', 'is_staff', 'isverified',
              'enable', 'department_id', 'designation_id', 'peopletype_id', 'client_id', 
              'bu_id', 'cuser_id', 'muser_id', 'reportto_id', 'deviceid', 'enable', 'mobno',
              'cdtz', 'mdtz','gender', 'dateofbirth', 'dateofjoin', 'tenant_id', 'ctzoffset']
    related = ['bu', 'client', 'peopletype', 'muser', 'cuser', 'reportto', 'department', 'designation']
   
    def create_user(self, loginid, password=None, **extra_fields):
        if not loginid:
            raise ValueError("Login id is required for any user!")
        user = self.model(loginid = loginid, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    
    def create_superuser(self, loginid, password=None, **extra_fields):
        if password is None:
            raise TypeError("Super users must have a password.")
        user = self.create_user(loginid, password, **extra_fields)
        
        user.is_superuser = True
        user.is_staff     = True
        user.isadmin      = True
        user.isverified  = True
        user.save(using=self._db)
        return user
    
    def get_people_from_creds(self, loginid, clientcode):
        if qset := self.select_related('client', 'bu').get(
            Q(loginid=loginid) & Q(client__bucode=clientcode)
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
                ~Q(id=1), bu_id = siteid, mdtz__gte = mdtz).values(*self.fields)
        return qset or self.none()
    
    
    



class CapabilityManager(models.Manager):
    use_in_migrations = True
    from apps.peoples import models as pm
    def get_webparentdata(self):
        return self.filter(cfor= self.pm.Capability.Cfor.WEB, parent__capscode='NONE')
        
    
    def get_mobparentdata(self):
        
        return self.filter(cfor = self.pm.Capability.Cfor.MOB, parent__capscode='NONE')
    
    def get_repparentdata(self):
        return self.filter(cfor=self.pm.Capability.Cfor.REPORT, parent__capscode='NONE')
    
    def get_portletparentdata(self):
        return self.filter(cfor=self.pm.Capability.Cfor.PORTLET, parent__capscode='NONE')
    
    def get_child_data(self, parent, cfor):
        return self.filter(cfor=cfor, parent__capscode=parent) if parent else None





class PgblngManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'cuser_id', 'muser_id', 'bu_id', 'client_id', 'people_id', 'cdtz', 'mdtz',
              'assignsites_id', 'pgroup_id', 'isgrouplead', 'ctzoffset', 'tenant_id']
    related = ['cuser', 'muser', 'pgroup', 'people', 'client', 'bu']
    
    def get_modified_after(self, mdtz, peopleid, buid):
        qset = self.select_related(
            *self.related).filter(
                ~Q(id=1),
                mdtz__gte = mdtz, people_id = peopleid, bu_id = buid).values(*self.fields)
        return qset or self.none()
    


class PgroupManager(models.Manager):
    use_in_migrations = True
    fields = ['id', 'groupname', 'enable', 'identifier_id','ctzoffset',
              'bu_id', 'client_id', 'tenant_id', 'cdtz', 'mdtz']
    related = ['identifier', 'bu', 'client', 'cuser', 'muser']
    
    def listview(self, request, fields, related, orderby, dir=None, qobjs=None):
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
                ~Q(id=1), mdtz__gte = mdtz, bu_id = buid,
                identifier__tacode = "PEOPLEGROUP").values(
                    *self.fields)
        return qset or None