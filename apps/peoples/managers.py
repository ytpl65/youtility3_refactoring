from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from icecream import ic

class PeopleManager(BaseUserManager):
    use_in_migrations =  True
   
    def _create_user(self, loginid, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not loginid:
            raise ValueError('The given loginid must be set')
        user = self.model(loginid=loginid, **extra_fields)
        user.save(using=self._db)
        return user
    
    def create_user(self, loginid, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(loginid, password, **extra_fields)

    
    def create_superuser(self, loginid, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('isadmin', True)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(loginid, password, **extra_fields)


class CapabilityManager(models.Manager):
    use_in_migrations = True

    def get_webparentdata(self):
        return self.filter(cfor='WEB', parent__capscode='NONE')
    
    def get_mobparentdata(self):
        return self.filter(cfor='MOB', parent__capscode='NONE')
    
    def get_repparentdata(self):
        return self.filter(cfor='REPORT', parent__capscode='NONE')
    
    def get_portletparentdata(self):
        return self.filter(cfor='PORTLET', parent__capscode='NONE')
    
    def get_child_data(self, parent, cfor):
        if not parent:
            return None
        return self.filter(cfor=cfor, parent__capscode=parent)





    