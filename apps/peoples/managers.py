from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from icecream import ic

class PeopleManager(BaseUserManager):
    use_in_migrations =  True
   
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
        user.is_verified  = True
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





    