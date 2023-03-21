from django.db import models

# Create your models here.
import uuid
from apps.peoples.models import BaseModel
from django.contrib.gis.db.models import PointField
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import ArrayField
from apps.tenants.models import TenantAwareModel
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from .managers import VendorManager, WorkOrderManager



def geojson():
    return {
        'gpslocation':""
    }

class Wom(BaseModel, TenantAwareModel):
    class Workstatus(models.TextChoices):
        ASSIGNED   = ('ASSIGNED', 'Assigned')
        COMPLETED  = ('COMPLETED', 'Completed')
        INPROGRESS = ('INPROGRESS', 'Inprogress')
        CANCELLED  = ('CANCELLED', 'Cancelled')
        
    class WorkPermitStatus(models.TextChoices):
        NOTNEED   = ('NOT_REQUIRED', 'Not Required')
        APPROVED  = ('APPROVED', 'Approved')
        REJECTED = ('REJECTED', 'Rejected')
        PARTIALLY_APPROVED  = ('PARTIALLY_APPROVED', 'Partially Approved')
        
    class Priority(models.TextChoices):
        HIGH   = ('HIGH', 'High')
        LOW    = ('LOW', 'Low')
        MEDIUM = ('MEDIUM', 'Medium')
    
    uuid             = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    description      = models.CharField(_("Job Description"), max_length = 200)
    plandatetime     = models.DateTimeField(_("Plan date time"), auto_now = False, auto_now_add = False)
    expirydatetime   = models.DateTimeField(_("Expiry date time"), auto_now = False, auto_now_add = False)
    gracetime        = models.IntegerField(_("Grace time"), null=True, blank=True)
    starttime        = models.DateTimeField( _("Start time"), auto_now = False, auto_now_add = False, null = True)
    endtime          = models.DateTimeField(_("Start time"), auto_now = False, auto_now_add = False, null = True)
    gpslocation      = PointField(_('GPS Location'),null = True, geography = True, srid = 4326)
    asset            = models.ForeignKey("activity.Asset", verbose_name = _("Asset"), on_delete= models.RESTRICT, null = True, blank = True, related_name='wo_assets')
    location         = models.ForeignKey('activity.Location', verbose_name=_('Location'), on_delete=models.RESTRICT, null=True, blank=True)
    workstatus       = models.CharField('Job Status', choices = Workstatus.choices, default=Workstatus.ASSIGNED,  max_length = 60, null = True)
    workpermit       = models.CharField(_('Work Permit'), choices=WorkPermitStatus.choices, default=WorkPermitStatus.NOTNEED, max_length=35)
    priority         = models.CharField(_("Priority"), max_length = 50, choices = Priority.choices)
    qset             = models.ForeignKey("activity.QuestionSet", verbose_name = _("QuestionSet"), on_delete  = models.RESTRICT, null = True, blank = True)
    vendor           = models.ForeignKey('Vendor', null=True, blank=False, on_delete=models.RESTRICT, verbose_name='Vendor')
    performedby      = models.CharField(max_length=55, verbose_name='Performed By', )
    parent           = models.ForeignKey("self", verbose_name = _("Belongs to"),  on_delete  = models.RESTRICT,  null = True, blank = True)
    alerts           = models.BooleanField(_("Alerts"), default = False, null = True)
    client           = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='wo_clients')
    bu               = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='wo_bus')
    ticketcategory   = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Notify Category"), null= True, blank = True, on_delete = models.RESTRICT)
    ismailsent       = models.BooleanField(_('Is Mail Sent'), default= False)
    isdenied       = models.BooleanField(_('Is Denied'), default= False)
    geojson = models.JSONField(verbose_name=_('Geo Json'), default=geojson, null=False)
    attachmentcount  = models.IntegerField(_('Attachment Count'), default = 0)
    categories       = ArrayField(models.CharField(max_length = 50, blank = True), null = True, blank = True, verbose_name= _("Categories"))

    objects = WorkOrderManager()
    
    class Meta(BaseModel.Meta):
        db_table = "wom"
        verbose_name = "work order management"
        constraints         = [
            models.UniqueConstraint(
                fields = ['qset', 'client', 'id'],
                name='qset_client'
            ),
        ]



class Vendor(BaseModel, TenantAwareModel):
    uuid    = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    code    = models.CharField(_("Code"), max_length=50, null=True, blank=False)
    name    = models.CharField(_('Name'), max_length=55, null=True, blank=False)
    address = models.TextField(max_length=500, verbose_name='Address', blank=True, null= True)
    gpslocation      = PointField(_('GPS Location'),null = True, geography = True, srid = 4326)
    enable = models.BooleanField(_("Enable"), default=True)
    mobno   = models.CharField(_("Mob No"), max_length=15)
    email   = models.CharField(_('Email'), max_length=100)
    client           = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='vendor_clients')
    bu               = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='vendor_bus')
    
    objects = VendorManager()
    class Meta(BaseModel.Meta):
        db_table = "vendor"
        verbose_name = "vendor company"
        constraints         = [
            models.UniqueConstraint(
                fields = ['code', 'client'],
                name='code_client'
            ),
        ]
    
    def __str__(self) -> str:
        return f'{self.name} ({self.code})'

    
class Approver(BaseModel, TenantAwareModel):
    people = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT, null=True, verbose_name=_('User'))
    wom    = models.ForeignKey(Wom, verbose_name=_("Work Order"), on_delete=models.RESTRICT, null=True)
    client = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='approver_clients')
    bu     = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='approver_bus')

    class Meta(BaseModel.Meta):
        db_table = 'approver'
        verbose_name = 'Approver'
    


class WomDetails(BaseModel, TenantAwareModel):
    class AnswerType(models.TextChoices):
        CHECKBOX    = ('CHECKBOX', 'Checkbox')
        DATE        = ('DATE', 'Date')
        DROPDOWN    = ('DROPDOWN', 'Dropdown')
        EMAILID     = ("EMAILID", "Email Id")
        MULTILINE   = ("MULTILINE", "Multiline")
        NUMERIC     = ("NUMERIC", "Numeric")
        SIGNATURE   = ("SIGNATURE", "Signature")
        SINGLELINE  = ("SINGLELINE", "Single Line")
        TIME        = ("TIME", "Time")
        RATING      = ("RATING", "Rating")
        BACKCAMERA  = ("BACKCAMERA", "Back Camera")
        FRONTCAMERA = ("FRONTCAMERA", "Front Camera")
        PEOPLELIST  = ("PEOPLELIST", "People List")
        SITELIST    = ("SITELIST", "Site List")
        NONE        = ("NONE", "NONE")
    
    class AvptType(models.TextChoices):
        BACKCAMPIC    = "BACKCAMPIC"   , _('Back Camera Pic')
        FRONTCAMPIC        = "FRONTCAMPIC"       , _('Front Camera Pic')
        AUDIO    = "AUDIO"   , _('Audio')
        VIDEO     = "VIDEO"    , _("Video")
        NONE = ("NONE", "NONE")
    
    uuid            = models.UUIDField(unique=True, editable=False, blank=True, default=uuid.uuid4)
    seqno           = models.SmallIntegerField(_('SL #'))
    question        = models.ForeignKey("activity.Question", verbose_name=_(""), on_delete=models.RESTRICT)
    answertype      = models.CharField(_("Answer Type"), max_length=50, choices=AnswerType.choices, null=True)
    answer          = models.CharField(_("Answer"), max_length = 250, default="", null = True)
    isavpt          = models.BooleanField(_("Is Attachement Required"), default = False)
    avpttype        = models.CharField(_("Attachment Type"), max_length = 50, choices = AvptType.choices, null=True, blank=True)
    options         = models.CharField( _("Option"), max_length = 200, null = True, blank = True)
    min             = models.DecimalField(_("Min"), max_digits = 18,  decimal_places = 4, null = True)
    max             = models.DecimalField(_("Max"), max_digits = 18, decimal_places = 4, null = True)
    alerton         = models.CharField( _("Alert On"), null = True, blank = True, max_length = 50)
    ismandatory     = models.BooleanField(_("Is Mandatory"), default = True)
    wom             = models.ForeignKey(Wom, verbose_name = _( "Jobneed"), null = True, blank = True, on_delete = models.RESTRICT)
    alerts          = models.BooleanField(_("Alerts"), default = False)
    attachmentcount = models.IntegerField(_('Attachment count'), default = 0)
    client          = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='womdetails_clients')
    bu              = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='womdetails_bus')

    
    class Meta(BaseModel.Meta):
        db_table = 'womdetails'
        verbose_name = 'Wom Details'
        constraints = [
            models.UniqueConstraint(
                fields = ['question', 'client'],
                name="question_client"
            )
        ]