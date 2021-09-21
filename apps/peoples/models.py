from django.db.models import CharField
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
    j = {"andriodversion": "",     "appversion": "",    "mobilecapability": [],             "portletcapability": [],
         "reportcapability": [],   "webcapability": [], "loacationtracking": False,         "capturemlog": False,
         "showalltemplates": False,"debug": False,      "showtemplatebasedonfilter": False, "blacklist": False,
         "assignsitegroup": "",    "tempincludes": "",  "mlogsendsto": ""}
    return j



class SecureString(CharField):
    """Custom Encrypted Field"""
    
    def from_db_value(self, value, expression, connection):
        from .utils import decrypt
        if not value == "":
            return value
            #return decrypt(value)
    
    def get_prep_value(self, value):
        from .utils import encrypt
        if not value=="":
            return value
            #return encrypt(value)
        
   
### Base Model, ALl other models inherit this model properties ###
class BaseModel(models.Model):
    cuser = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete = models.RESTRICT, db_column="cuser", related_name="%(class)s_cusers")
    muser = models.ForeignKey(settings.AUTH_USER_MODEL,  null = True, blank=True, on_delete = models.RESTRICT, db_column="muser", related_name="%(class)s_musers")
    cdtz  = models.DateTimeField(_('cdtz'), auto_now_add = True, auto_now=False)
    mdtz  = models.DateTimeField(_('mdtz'), auto_now = True)

    class Meta:
        abstract = True
        ordering = ['mdtz']


############## People Table ###############
class People(AbstractBaseUser, PermissionsMixin, TenantAwareModel, BaseModel):
    GENDER_CHOICES= [('M', 'Male'), ('F', 'Female')]
    
    peopleimg     = models.ImageField(_("peopleimg"), upload_to=upload_peopleimg, default="master/people/blank.png", null=True, blank=True)
    peopleid      = models.BigAutoField(_('peopleid'), primary_key=True, auto_created=True, editable=False)
    peoplecode    = models.CharField(_("peoplecode"), max_length=50)
    peoplename    = models.CharField(_("peoplename"), max_length=120)
    loginid       = models.CharField(_("loginid"), max_length=50, unique=True, null=True, blank=True)
    isadmin       = models.BooleanField(_("isadmin"), default=False)
    is_staff      = models.BooleanField(_('staff status'),default=False)
    isenable      = models.BooleanField(_("isactive"), default=True)
    department    = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete=models.RESTRICT, related_name='people_departments')
    designation   = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete=models.RESTRICT, related_name='people_designations')
    peopletype    = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete=models.RESTRICT, related_name='people_types')
    clientid      = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete=models.RESTRICT, related_name='people_clientids')
    siteid        = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete=models.RESTRICT, related_name='people_siteids')
    reportto      = models.ForeignKey("self", null=True, blank=True, on_delete=models.RESTRICT, related_name='children')
    deviceid      = models.CharField(_("deviceid"), max_length=50, default='-1')
    email         = SecureString(_("email"), max_length=254, unique=True)
    mobno         = SecureString(_("mobno"), max_length=254, unique=True)
    gender        = models.CharField(_("gender"), choices=GENDER_CHOICES, max_length=15, null=True)
    dateofbirth   = models.DateField(_("dob"))
    dateofjoin    = models.DateField(_("doj"))
    dateofreport  = models.DateField(_("dor"), null=True, blank=True)
    people_extras = models.JSONField(_("people_extras"), default = peoplejson,blank=True, encoder=DjangoJSONEncoder)

    objects=PeopleManager()
    USERNAME_FIELD = 'loginid'
    REQUIRED_FIELDS = ['peoplecode',  'peoplename', 'dateofbirth',
                      'dateofjoin', 'mobno', 'email']



    class Meta:
        db_table = 'people'
        constraints = [
            models.UniqueConstraint(fields=['loginid', 'peoplecode', 'siteid'], name='peolple_logind_peoplecode_siteid_uk'),
            models.UniqueConstraint(fields=['peoplecode', 'siteid'], name='people_peoplecode_siteid'),
            models.UniqueConstraint(fields=['loginid', 'siteid'], name='people_loginid_siteid_uk'),
            models.UniqueConstraint(fields=['loginid'], name='people_loginid_uk'),
        ]
    


    def __str__(self) -> str:
        return self.peoplecode



############## Pgroup Table ###############
class Pgroup(BaseModel, TenantAwareModel):
    groupid    = models.BigAutoField(_('groupid'), primary_key=True, auto_created=True, editable=False)
    groupname  = models.CharField(_('groupname'), max_length=250)
    enable     = models.BooleanField(_('enable'), default = True)
    identifier = models.ForeignKey('onboarding.TypeAssist', null=True, blank=True, on_delete = models.RESTRICT, db_column='identifier', related_name="pgroup_idfs")
    siteid     = models.ForeignKey("onboarding.Bt",null=True, blank=True, on_delete = models.RESTRICT, db_column='buid', related_name='pgroup_siteids')
    clientid   = models.ForeignKey('onboarding.Bt', null=True, blank=True, on_delete = models.RESTRICT, db_column='clientid', related_name='pgroup_clientids')
    
    class Meta(BaseModel.Meta):
        db_table = 'pgroup'
        constraints = [
        models.UniqueConstraint(fields=['groupname', 'identifier' ], name='pgroup_groupname_buid_clientid_identifier_key'),
        models.UniqueConstraint(fields=['groupname', 'identifier'], name='pgroup_groupname_buid_identifier_key')
    ]
        get_latest_by = ["mdtz", 'cdtz']
        


    def __str__(self) -> str:
        return self.groupname



############## Pgbelonging Table ###############
class Pgbelonging(BaseModel, TenantAwareModel):
    pgbid       = models.BigAutoField(primary_key=True, auto_created=True, editable=False)
    groupid     = models.ForeignKey('Pgroup', null=True, blank=True, on_delete = models.RESTRICT, db_column='groupid', related_name="pgbelongs_grps")
    peopleid    = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete = models.RESTRICT,  db_column='peopleid', related_name="pgbelongs_peoples")
    isgrouplead = models.BooleanField(_('isgrouplead'), default = False)
    assignsites = models.ForeignKey('onboarding.Bt', null=True,  blank=True, on_delete = models.RESTRICT, db_column='assignsites', related_name="pgbelongs_assignsites")
    siteid      = models.ForeignKey("onboarding.Bt",null=True, blank=True, on_delete = models.RESTRICT, db_column='buid', related_name='pgbelonging_sites')
    clientid    = models.ForeignKey('onboarding.Bt', null=True, blank=True, on_delete = models.RESTRICT, db_column='clientid', related_name='pgbelonging_clients')
    
    class Meta(BaseModel.Meta):
        db_table = 'pgbelonging'
        constraints = [
        models.UniqueConstraint(fields=['groupid', 'peopleid', 'assignsites'], name='pgbelonging_groupid_peopleid_buid_assignsites_clientid')
    ]
        get_latest_by = ["mdtz",'cdtz']
        
    
    def __str__(self) -> str:
        return self.groupid



############## Capability Table ###############
class Capability(BaseModel, TenantAwareModel):  
    CFOR_CHOICES = [('WEB', 'WEB'), ('PORTLET', 'PORTLET'), ('REPORT', 'REPORT'), ('MOB', 'MOB')]
    capsid      = models.AutoField(primary_key=True, auto_created=True, editable=False)
    capscode    = models.CharField(_('caps'), max_length=50)
    capsname    = models.CharField(_('includes'), max_length=1000, default = None, blank=True, null=True)
    parent      = models.ForeignKey('self', on_delete=models.RESTRICT, db_column='parent', null=True, blank=True, related_name='children')
    cfor        = models.CharField(_('cfor'), max_length=10, default='WEB', choices=CFOR_CHOICES)
    clientid    = models.ForeignKey('onboarding.Bt',  null=True, blank=True, on_delete = models.RESTRICT, db_column='clientid')

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

def peventlog_json():
    j={'photorecognitionthreshold':None, 'photorecognitionscore':None, 
    'photorecognitiontimestamp':None, 'photorecognitionserviceresponse':None}
    return j

############## PeopleEventlog Table ###############
class PeopleEventlog(BaseModel, TenantAwareModel):
    pelogid         = models.BigAutoField(_('pelogid'), primary_key=True, auto_created=True, editable=False)
    peopleid        = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete = models.RESTRICT, db_column='peopleid')
    peventtype      = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete = models.RESTRICT, db_column='peventtype', related_name='eventypes')
    punchstatus     = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete = models.RESTRICT, db_column='punchstatus', related_name='statustypes')
    verifiedby      = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete = models.RESTRICT, db_column='verifiedby', related_name='verifiedpeoples')
    buid            = models.ForeignKey("onboarding.Bt", null=True, blank=True, on_delete = models.RESTRICT, db_column='buid')
    transportmode   = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete = models.RESTRICT, db_column='transportmode', related_name='transportmodetypes')
    clientid        = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete = models.RESTRICT, db_column='clientid', related_name='clientids')
    siteid          = models.ForeignKey("onboarding.Bt",  null=True, blank=True, on_delete = models.RESTRICT, db_column='siteid', related_name='siteids')
    accuracy        = models.IntegerField(_("accuracy"), null=True, blank=True)
    deviceid        = models.CharField(_("deviceid"), max_length=50, null=True, blank=True)
    datetime        = models.DateTimeField(_("datetime"), auto_now=False, auto_now_add=False)
    gpslocation     = models.CharField(_("gpslocation"), max_length=50, default='0.0,0.0')
    facerecognition = models.BooleanField(_("facerecognition"), default=False)
    expamt          = models.IntegerField(_("exampt"), null=True, blank=True)
    duration        = models.IntegerField(_("duration"), null=True, blank=True)
    reference       = models.CharField(_("reference"),null=True, max_length=50, blank=True)
    remarks         = models.CharField(_("remarks"),null=True, max_length=500, blank=True)
    distance        = models.IntegerField(_("distance"), null=True, blank=True)
    ctzoffset       = models.IntegerField(_("ctzoffset"), null=True, default=0, blank=True)
    otherlocation   = models.CharField(_("otherlocation"), null=True, max_length=200, blank=True)
    peventlogextras = models.JSONField(_("peventlogextras"), encoder=DjangoJSONEncoder, default=peventlog_json)


    class Meta:
        db_table='peopleeventlog'
        get_latest_by = ['mdtz']

    def __str__(self) -> str:
        return self.peventtype
