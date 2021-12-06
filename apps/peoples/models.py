from django.db.models import CharField
from django.db.models.fields import BooleanField
from django.urls import reverse
from django.conf import settings
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from .managers import PeopleManager, CapabilityManager
from .utils import  upload_peopleimg
from apps.tenants.models import TenantAwareModel
import logging
logger = logging.getLogger('django')

# Create your models here.


def peoplejson():
    return {
        "andriodversion": "",
        "appversion": "",
        "mobilecapability": [],
        "portletcapability": [],
        "reportcapability": [],
        "webcapability": [],
        "loacationtracking": False,
        "capturemlog": False,
        "showalltemplates": False,
        "debug": False,
        "showtemplatebasedonfilter": False,
        "blacklist": False,
        "assignsitegroup": "",
        "tempincludes": "",
        "mlogsendsto": "",
    }



class SecureString(CharField):
    """Custom Encrypted Field"""
    
    def from_db_value(self, value, expression, connection):
        from .utils import decrypt
        if value != "":
            return value
            #return decrypt(value)
    
    def get_prep_value(self, value):
        from .utils import encrypt
        if value != "":
            return value
            #return encrypt(value)
        
   
### Base Model, ALl other models inherit this model properties ###
class BaseModel(models.Model):
    cuser = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete = models.RESTRICT, related_name="%(class)s_cusers")
    muser = models.ForeignKey(settings.AUTH_USER_MODEL,  null = True, blank=True, on_delete = models.RESTRICT,related_name="%(class)s_musers")
    cdtz  = models.DateTimeField(_('cdtz'), auto_now_add = True, auto_now=False)
    mdtz  = models.DateTimeField(_('mdtz'), auto_now = True)

    class Meta:
        abstract = True
        ordering = ['mdtz']


############## People Table ###############
class People(AbstractBaseUser, PermissionsMixin, TenantAwareModel, BaseModel):
    GENDER_CHOICES= [('M', 'Male'), ('F', 'Female')]
    
    peopleimg     = models.ImageField(_("peopleimg"), upload_to=upload_peopleimg, default="master/people/blank.png", null=True, blank=True)
    peoplecode    = models.CharField(_("Code"), max_length=50)
    peoplename    = models.CharField(_("Name"), max_length=120)
    loginid       = models.CharField(_("Login Id"), max_length=50, unique=True, null=True, blank=True)
    isadmin       = models.BooleanField(_("Is Admin"), default=False)
    is_staff      = models.BooleanField(_('staff status'),default=False)
    is_verified   = models.BooleanField(_("Is Active"), default=False)
    enable        = models.BooleanField(_("Enable"), default=True)
    shift         = models.ForeignKey('onboarding.Shift', null=True, blank=True, on_delete=models.RESTRICT, related_name='onboarding_shift')
    department    = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete=models.RESTRICT, related_name='people_departments')
    designation   = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete=models.RESTRICT, related_name='people_designations')
    peopletype    = models.ForeignKey("onboarding.TypeAssist", verbose_name="People Type", null=True, blank=True, on_delete=models.RESTRICT, related_name='people_types')
    clientid      = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete=models.RESTRICT, related_name='people_clientids')
    siteid        = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete=models.RESTRICT, related_name='people_siteids')
    reportto      = models.ForeignKey("self", null=True, blank=True, on_delete=models.RESTRICT, related_name='children', verbose_name='Report to')
    deviceid      = models.CharField(_("Device Id"), max_length=50, default='-1')
    email         = SecureString(_("Email"), max_length=254)
    mobno         = SecureString(_("Mob No"), max_length=254, null=True)
    gender        = models.CharField(_("Gender"), choices=GENDER_CHOICES, max_length=15, null=True)
    dateofbirth   = models.DateField(_("Date of Birth"))
    dateofjoin    = models.DateField(_("Date of Join"))
    dateofreport  = models.DateField(_("Date of Report"), null=True, blank=True)
    people_extras = models.JSONField(_("people_extras"), default = peoplejson, blank=True, encoder=DjangoJSONEncoder)

    objects=PeopleManager()
    USERNAME_FIELD = 'loginid'
    REQUIRED_FIELDS = ['peoplecode',  'peoplename', 'dateofbirth'
                      'dateofjoin', 'email']



    class Meta:
        db_table = 'people'
        constraints = [
            models.UniqueConstraint(fields=['loginid', 'peoplecode', 'siteid'], name='peolple_logind_peoplecode_siteid_uk'),
            models.UniqueConstraint(fields=['peoplecode', 'siteid'], name='people_peoplecode_siteid'),
            models.UniqueConstraint(fields=['loginid', 'siteid'], name='people_loginid_siteid_uk'),
            models.UniqueConstraint(fields=['loginid'], name='people_loginid_uk'),
            models.UniqueConstraint(fields=['loginid', 'mobno', 'email'], name='loginid_mobno_email_uk'),
        ]
    


    def __str__(self) -> str:
        return self.peoplecode

    def get_absolute_wizard_url(self):
        return reverse("peoples:wiz_people_update", kwargs={"pk": self.pk})



############## Pgroup Table ###############
class Pgroup(BaseModel, TenantAwareModel):
    groupname  = models.CharField(_('Name'), max_length=250)
    enable     = models.BooleanField(_('Enable'), default = True)
    identifier = models.ForeignKey('onboarding.TypeAssist', null=True, blank=True, on_delete = models.RESTRICT, related_name="pgroup_idfs")
    siteid     = models.ForeignKey("onboarding.Bt",null=True, blank=True, on_delete = models.RESTRICT, related_name='pgroup_siteids')
    clientid   = models.ForeignKey('onboarding.Bt', null=True, blank=True, on_delete = models.RESTRICT, related_name='pgroup_clientids')
    
    class Meta(BaseModel.Meta):
        db_table = 'pgroup'
        constraints = [
        models.UniqueConstraint(fields=['groupname', 'identifier' ], name='pgroup_groupname_buid_clientid_identifier_key'),
        models.UniqueConstraint(fields=['groupname', 'identifier'], name='pgroup_groupname_buid_identifier_key')
    ]
        get_latest_by = ["mdtz", 'cdtz']
        


    def __str__(self) -> str:
        return self.groupname
    
    def get_absolute_wizard_url(self):
        return reverse("peoples:wiz_pgropup_update", kwargs={"pk": self.pk})



############## Pgbelonging Table ###############
class Pgbelonging(BaseModel, TenantAwareModel):
    groupid     = models.ForeignKey('Pgroup', null=True, blank=True, on_delete = models.RESTRICT, related_name="pgbelongs_grps")
    peopleid    = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete = models.RESTRICT,  related_name="pgbelongs_peoples")
    isgrouplead = models.BooleanField(_('Group Lead'), default = False)
    assignsites = models.ForeignKey('onboarding.Bt', null=True,  blank=True, on_delete = models.RESTRICT, related_name="pgbelongs_assignsites")
    siteid      = models.ForeignKey("onboarding.Bt",null=True, blank=True, on_delete = models.RESTRICT,  related_name='pgbelonging_sites')
    clientid    = models.ForeignKey('onboarding.Bt', null=True, blank=True, on_delete = models.RESTRICT, related_name='pgbelonging_clients')
    
    class Meta(BaseModel.Meta):
        db_table = 'pgbelonging'
        constraints = [
        models.UniqueConstraint(fields=['groupid', 'peopleid', 'assignsites'], name='pgbelonging_groupid_peopleid_buid_assignsites_clientid')
    ]
        get_latest_by = ["mdtz",'cdtz']
        
    
    def __str__(self) -> str:
        return str(self.id)



############## Capability Table ###############
class Capability(BaseModel, TenantAwareModel):  
    CFOR_CHOICES = [('WEB', 'WEB'), ('PORTLET', 'PORTLET'), ('REPORT', 'REPORT'), ('MOB', 'MOB')]
    capscode    = models.CharField(_('Code'), max_length=50)
    capsname    = models.CharField(_('Capability'), max_length=1000, default = None, blank=True, null=True)
    parent      = models.ForeignKey('self', on_delete=models.RESTRICT,  null=True, blank=True, related_name='children', verbose_name="Belongs_to")
    cfor        = models.CharField(_('Capability_for'), max_length=10, default='WEB', choices=CFOR_CHOICES,)
    clientid    = models.ForeignKey('onboarding.Bt',  null=True, blank=True, on_delete = models.RESTRICT)
    enable      = models.BooleanField(_('Enable'), default=True)

    objects = CapabilityManager()
    
    class Meta(BaseModel.Meta):
        db_table            = 'capability'
        verbose_name        = 'Capability'
        verbose_name_plural = 'Capabilities'
        get_latest_by       = ["mdtz",'cdtz']
        constraints = [
        models.UniqueConstraint(fields=['capscode', 'cfor'], name="capability_caps_cfor_uk"),]

    def __str__(self) -> str:
        return self.capsname
    
    def get_absolute_url(self):
        return reverse("peoples:cap_update", kwargs={"pk": self.pk})
    
    def get_all_children(self):
        children = [self]
        try:
            child_list = self.children.all()
        except AttributeError:
            return children
        for child in child_list:
            children.extend(child.get_all_children())
        return children

    def get_all_parents(self):
        parents = [self]
        if self.parent is not None:
            parent = self.parent
            parents.extend(parent.get_all_parents())
        return parents

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.parent in self.get_all_children():
            raise ValidationError("A capability cannot have itself \
                    or one of its' children as parent.")
