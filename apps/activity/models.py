from calendar import c
from email.policy import default
from enum import Flag
from django.core.exceptions import RequestAborted
from django.db import models, migrations
from django.db.models import base, constraints
from django.db.models.fields import BLANK_CHOICE_DASH, TimeField, files
from apps.peoples.models import BaseModel
from django.utils.translation import gettext_lazy as _
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.gis.db.models import PointField
from apps.tenants.models import TenantAwareModel
from django.conf import settings
from taggit.managers import TaggableManager
from django.db import models
from datetime import datetime
from django.contrib.gis.db.models import PointField
from django.utils import timezone
from apps.activity.managers import(
    QuestionSetManager
)

# Create your models here.
class Question(BaseModel, TenantAwareModel):
    
    class AnswerType(models.TextChoices):
        CHECKBOX    = "CHECKBOX"   , _('Checkbox') 
        DATE        = "DATE"       , _('Date')
        DROPDOWN    = "DROPDOWN"   , _('Dropdown')
        EMAILID     = "EMAILID"    , _("Email Id")
        MULTILINE   = "MULTILINE"  , _("Multiline")
        NUMERIC     = "NUMERIC"    , _("Numeric")
        SIGNATURE   = "SIGNATURE"  , _("Signature")
        SINGLELINE  = "SINGLELINE" , _("Single Line")
        TIME        = "TIME"       , _("Time")
        RATING      = "RATING"     , _("Rating")
        BACKCAMERA  = "BACKCAMERA" , _("Back Camera")
        FRONTCAMERA = "FRONTCAMERA", _("Front Camera")
        PEOPLELIST  = "PEOPLELIST" , _("People List")
        SITELIST    = "SITELIST"   , _("Site List")

    ques_name  = models.CharField(_("Question Name"), max_length=200)
    options    = models.TextField(_('Options'), max_length=2000, null=True)
    min        = models.DecimalField(_("Min"), null=True, blank=True, max_digits=18, decimal_places=2, default=0.00)
    max        = models.DecimalField( _('Max'), null=True, blank=True, max_digits=18, decimal_places=2, default=0.00)
    alerton    = models.CharField(_("Alert on"), max_length=300, null=True)
    answertype = models.CharField(verbose_name=_("Type"), choices=AnswerType.choices, default="NUMERIC", max_length=55)  # type in previous
    unit       = models.ForeignKey("onboarding.TypeAssist", verbose_name=_( "Unit"), on_delete=models.RESTRICT, related_name="unit_types", null=True, blank=True)
    client     = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete=models.RESTRICT, null=True, blank=True)
    isworkflow = models.BooleanField(_("Is WorkFlow"), default=False)
    enable     = models.BooleanField(_("Enable"), default=True)
    category   = models.ForeignKey("onboarding.TypeAssist", verbose_name=_("Category"), on_delete=models.RESTRICT, related_name='category_types', null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table = 'question'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
        constraints = [models.UniqueConstraint(
            fields=['ques_name', 'answertype', 'client'], name='ques_name_type_client_uk')]

    def __str__(self) -> str:
        return f"{self.ques_name} | {self.answertype}"


def site_grp_includes():
    return {
        'sitegrp__id': ""  # save this variable as <sitegrp__id> eg: abcd__12
    }


def site_type_includes():
    return {
        'sitetype__id': ""  # save this variable as <sitetype__id> eg: abcd__12
    }

# will save on client level


class QuestionSet(BaseModel, TenantAwareModel):
    class Type(models.TextChoices):
        CHECKLIST              = "CHECKLIST"             , _('Checklist')
        INCIDENTREPORTTEMPLATE = "INCIDENTREPORTTEMPLATE", _('Incident Report Template')
        SITEREPORTTEMPLATE     = "SITEREPORTTEMPLATE"    , _('Site Report Template')
        WORKPERMITTEMPLATE     = "WORKPERMITTEMPLATE"    , _('Work Permit Template')
        KPITEMPLATE            = "KPITEMPLATE"           , _('Kpi Template')
        SCRAPPEDTEMPLATE       = "SCRAPPEDTEMPLATE"      , _('Scrapped Template')
        ASSETAUDIT             = "ASSETAUDIT"            , _('Asset Audit')
        MAINTENANCETEMPLATE    = "MAINTENANCETEMPLATE"   , _('Maintenance Template')
        ASSETMAINTENANCE       = "ASSETMAINTENANCE"      , _('Asset Maintenance')
        QUESTIONSET            = "QUESTIONSET"           , _('Question Set')

    qset_name          = models.CharField(_("QuestionSet Name"), max_length=200)
    asset              = models.ForeignKey( "activity.Asset", on_delete=models.RESTRICT, null=True, blank=False)
    enable             = models.BooleanField(_("Enable"), default=True)
    assetincludes      = models.TextField(null=True, blank=True)
    buincludes         = models.TextField(null=True, blank=True)
    slno               = models.SmallIntegerField(_("SL No."), default=1)
    parent             = models.ForeignKey("self", verbose_name=_("Belongs To"), on_delete=models.RESTRICT, null=True, blank=True)
    type               = models.CharField( _("Question Set Type"), choices=Type.choices, null=True, max_length=50)
    bu                 = models.ForeignKey("onboarding.Bt", verbose_name=_("Site"), on_delete=models.RESTRICT, related_name='qset_bus', null=True, blank=True)
    client             = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete=models.RESTRICT, related_name='qset_clients', null=True, blank=True)
    site_grp_includes  = models.JSONField(_('Site Groups'), default=site_grp_includes, encoder=DjangoJSONEncoder, blank=True, null=True)
    site_type_includes = models.JSONField(_("Site Types"), default=site_type_includes, encoder=DjangoJSONEncoder, blank=True, null=True)
    url                = models.CharField(_("Url"), max_length=250, null=True, blank=True)

    objects = QuestionSetManager()
    
    class Meta(BaseModel.Meta):
        db_table            = 'questionset'
        verbose_name        = 'QuestionSet'
        verbose_name_plural = 'QuestionSets'
        constraints         = [
            models.UniqueConstraint(
                fields=['qset_name', 'parent', 'type', 'client', 'bu'],
                name='name_type_parent_type_client_bu_uk'
            ),
            models.CheckConstraint(
                check=models.Q(slno__gte=0),
                name='slno_gte_0_ck')
        ]

    def __str__(self) -> str:
        return self.qset_name

def alertmails_sendto():
    return {
        "id__code": []
    }


class QuestionSetBelonging(BaseModel, TenantAwareModel):
    class AnswerType(models.TextChoices):
        CHECKBOX    = "CHECKBOX"   , _('Checkbox')
        DATE        = "DATE"       , _('Date')
        DROPDOWN    = "DROPDOWN"   , _('Dropdown')
        EMAILID     = "EMAILID"    , _("Email Id")
        MULTILINE   = "MULTILINE"  , _("Multiline")
        NUMERIC     = "NUMERIC"    , _("Numeric")
        SIGNATURE   = "SIGNATURE"  , _("Signature")
        SINGLELINE  = "SINGLELINE" , _("Single Line")
        TIME        = "TIME"       , _("Time")
        RATING      = "RATING"     , _("Rating")
        BACKCAMERA  = "BACKCAMERA" , _("Back Camera")
        FRONTCAMERA = "FRONTCAMERA", _("Front Camera")
        PEOPLELIST  = "PEOPLELIST" , _("People List")
        SITELIST    = "SITELIST"   , _("Site List")

    ismandatory       = models.BooleanField(_("Is Manadatory"))
    slno              = models.SmallIntegerField(_("Seq No."))
    qset              = models.ForeignKey("activity.QuestionSet", verbose_name=_("Question Set"), on_delete=models.RESTRICT, null=True, blank=True)
    question          = models.ForeignKey("activity.Question", verbose_name=_("Question"), null=True, blank=False,  on_delete=models.RESTRICT)
    answertype        = models.CharField(_("Question Type"), max_length=50, choices=AnswerType.choices)
    max               = models.DecimalField(_("Max"), null=True, max_digits=18, decimal_places=2, default=0.00)
    min               = models.DecimalField(_("Min"), null=True, max_digits=18, decimal_places=2, default=0.00)
    alerton           = models.CharField(_("Alert on"), null=True, blank=True, max_length=300)
    options           = models.CharField(_("Option"), max_length=200, null=True, blank=True)
    client            = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete=models.RESTRICT, null=True, blank=True, related_name='qsetbelong_client')
    alertmails_sendto = models.JSONField( _("Alert mails send to"), encoder=DjangoJSONEncoder, default=alertmails_sendto)
    bu                = models.ForeignKey("onboarding.Bt", verbose_name=_("Site"), on_delete=models.RESTRICT, null=True, blank=True, related_name='qsetbelong_bu')
    client            = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete=models.RESTRICT, null=True, blank=True, related_name='qsetbelong_client')

    class Meta(BaseModel.Meta):
        db_table            = 'questionsetbelonging'
        verbose_name        = 'QuestionSetBelonging'
        verbose_name_plural = 'QuestionSetBelongings'
        constraints         = [
            models.UniqueConstraint(
                fields=['qset', 'question', 'client', 'bu'],
                name='qset_question_client_bu_uk'
            )
        ]

    def __str__(self) -> str:
        return self.answertype


def other_info():
    return {
        'tour_frequency': 1,
        'is_randomized': False,
        'distance': None,
        'breaktime': 0,
    }


class Job(BaseModel, TenantAwareModel):
    class Identifier(models.TextChoices):
        TASK             = ('TASK', 'Task')
        TICKET           = ('TICKET', 'Ticket')
        INTERNALTOUR     = ('INTERNALTOUR', 'Internal Tour')
        EXTERNALTOUR     = ('EXTERNALTOUR', 'External Tour')
        PPM              = ('PPM', 'PPM')
        OTHER            = ('OTHER', 'Other')
        SITEREPORT       = ("SITEREPORT","Site Report")
        INCIDENTREPORT   = ('INCIDENTREPORT', "Incident Report")
        ASSETLOG         = ("ASSETLOG",	"Asset Log")
        ASSETMAINTENANCE = ("ASSETMAINTENANCE",	"Asset Maintenance")

    class Priority(models.TextChoices):
        HIGH   = "HIGH" , _('High')
        LOW    = "LOW"  , _('Low')
        MEDIUM = "MEDIU", _('Medium')

    class Scantype(models.TextChoices):
        QR      = "QR"     , _('QR')
        NFC     = "NFC"    , _('NFC')
        SKIP    = "SKIP"   , _('Skip')
        ENTERED = "ENTERED", _('Entered')

    class Frequency(models.TextChoices):
        NONE        = "NONE"       , _('None')
        DAILY       = "DAILY"      , _("Daily")
        WEEKLY      = "WEEKLY"     , _("Weekly")
        MONTHLY     = "MONTHLY"    , _("Monthly")
        BIMONTHLY   = "BIMONTHLY"  , _("Bimonthly")
        QUARTERLY   = "QUARTERLY"  , _("Quarterly")
        HALFYEARLY  = "HALFYEARLY" , _("Half Yearly")
        YEARLY      = "YEARLY"     , _("Yearly")
        FORTNIGHTLY = "FORTNIGHTLY", _("Fort Nightly")

    jobname         = models.CharField(_("Name"), max_length=100)
    jobdesc         = models.CharField(_("Description"), max_length=500)
    from_date       = models.DateTimeField( _("From date"), auto_now=False, auto_now_add=False)
    upto_date       = models.DateTimeField( _("To date"), auto_now=False, auto_now_add=False)
    cron            = models.CharField(_("Cron Exp."), max_length=200)
    identifier      = models.CharField(_("Job Type"), max_length=100, choices=Identifier.choices, null=True)
    planduration    = models.IntegerField(_("Plan duration (min)"))
    gracetime       = models.IntegerField(_("Grace Time"))
    expirytime      = models.IntegerField(_("Expiry Time"))
    lastgeneratedon = models.DateTimeField(_("Last generatedon"), auto_now=False, auto_now_add=True)
    asset           = models.ForeignKey("activity.Asset", verbose_name=_("Asset"), on_delete=models.RESTRICT, null=True, blank=True)
    priority        = models.CharField(_("Priority"), max_length=100, choices=Priority.choices)
    qset            = models.ForeignKey("activity.QuestionSet", verbose_name=_("QuestionSet"), on_delete=models.RESTRICT, null=True, blank=True)
    people          = models.ForeignKey('peoples.People', verbose_name=_( "Aggresive auto-assign to People"), on_delete=models.RESTRICT, null=True, blank=True, related_name='job_aaatops')
    pgroup          = models.ForeignKey("peoples.Pgroup", verbose_name=_("Group"), on_delete=models.RESTRICT, null=True, blank=True)
    geofence        = models.ForeignKey("onboarding.GeofenceMaster", verbose_name=_("Geofence"), on_delete=models.RESTRICT, null=True, blank=True)
    parent          = models.ForeignKey("self", verbose_name=_("Belongs to"), on_delete=models.RESTRICT, null=True, blank=True)
    slno            = models.SmallIntegerField(_("Serial No."))
    client          = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete=models.RESTRICT, related_name='job_clients', null=True, blank=True)
    bu              = models.ForeignKey("onboarding.Bt", verbose_name=_("Site"), on_delete=models.RESTRICT, related_name='job_bus', null=True, blank=True)
    shift           = models.ForeignKey("onboarding.Shift", verbose_name=_("Shift"), on_delete=models.RESTRICT, null=True, related_name="job_shifts")
    starttime       = models.TimeField(_("Start time"), auto_now=False, auto_now_add=False, null=True)
    endtime         = models.TimeField(_("End time"), auto_now=False, auto_now_add=False, null=True)
    ticket_category = models.ForeignKey("onboarding.TypeAssist", verbose_name=_("Ticket Category"), on_delete=models.RESTRICT, null=True, blank=True, related_name="job_tktcategories")
    scantype        = models.CharField(_("Scan Type"), max_length=50, choices=Scantype.choices)
    frequency       = models.CharField(verbose_name=_("Frequency type"), null=True, max_length=55, choices=Frequency.choices)
    ctzoffset       = models.CharField(_("TZ_Offset"), max_length = 55, null=True, blank=True)
    other_info      = models.JSONField(_("Other info"), default=other_info, blank=True, encoder=DjangoJSONEncoder)

    class Meta(BaseModel.Meta):
        db_table            = 'job'
        verbose_name        = 'Job'
        verbose_name_plural = 'Jobs'
        constraints         = [
            models.UniqueConstraint(
                fields=['jobname', 'asset',
                        'qset', 'parent', 'identifier'],
                name='jobname_asset_qset_id_parent_identifier_uk'
            ),
            models.CheckConstraint(
                check=models.Q(gracetime__gte=0),
                name='gracetime_gte_0_ck'
            ),
            models.CheckConstraint(
                check=models.Q(planduration__gte=0),
                name='planduration_gte_0_ck'
            ),
            models.CheckConstraint(
                check=models.Q(expirytime__gte=0),
                name='expirytime_gte_0_ck'
            )
        ]

    def __str__(self):
        return self.jobname


def asset_json():
    return {
        'service': "",
        'meter': "",
        "bill_val": 0.0,
        "supplier": '',
        'msn': "",
        "bill_date": "",
        "purchase_date": "",
        "model": "",
        "inst_date": "",  # installation date
        "sfdate": "",
        "stdate": "",
        "yom": "",  # year of Mfg
        "tempcode": "",
        "po_number": "",
        "invoice_no": "",
        "invoice_date": "",
        "far_asset_id": "",
        "mult_factor": 1
    }


class Asset(BaseModel, TenantAwareModel):
    class Identifier(models.TextChoices):
       NONE       = ("NONE", "None")
       ASSET      = ("ASSET", "Asset")
       CHECKPOINT = ("CHECKPOINT", "Checkpoint")
       LOCATION   = ("LOCATION", "Location")
       SMARTPLACE = ("SMARTPLACE", "Smartplace")
       
    class RunningStatus(models.TextChoices):
        MAINTENANCE = ("MAINTENANCE", "Maintenance")
        STANDBY     = ("STANDBY", "Standby")
        WORKING     = ("WORKING", "Working")
        SCRAPPED    = ("SCRAPPED", "Scrapped")   

    assetcode     = models.CharField(_("Asset Code"), max_length=50)
    assetname     = models.CharField(_("Asset Name"), max_length=250)
    enable        = models.BooleanField(_("Enable"), default=True)
    iscritical    = models.BooleanField(_("Is Critical"))
    gpslocation   = PointField(_('GPS Location'), null=True, geography=True, srid=4326)
    parent        = models.ForeignKey("self", verbose_name=_( "Belongs to"), on_delete = models.RESTRICT, null=True, blank=True)
    identifier    = models.CharField( _('Asset Identifier'), choices=Identifier.choices, max_length=55)
    runningstatus = models.CharField(_('Running Status'), choices=RunningStatus.choices, max_length=55)
    type          = models.ForeignKey("onboarding.TypeAssist", verbose_name=_("Type"), on_delete = models.RESTRICT, null=True, blank=True, related_name='asset_types')
    client        = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete = models.RESTRICT, null=True, blank=True, related_name='asset_clients')
    bu            = models.ForeignKey("onboarding.Bt", verbose_name=_("Site"), on_delete = models.RESTRICT, null=True, blank=True, related_name='asset_bus')
    category      = models.ForeignKey("onboarding.TypeAssist", verbose_name=_("Category"), null = True, blank=True, on_delete=models.RESTRICT, related_name='asset_categories')
    subcategory   = models.ForeignKey("onboarding.TypeAssist", verbose_name=_("Sub Category"), null = True, blank=True, on_delete=models.RESTRICT, related_name='asset_subcategories')
    brand         = models.ForeignKey("onboarding.TypeAssist", verbose_name=_("Brand"), null = True, blank=True, on_delete=models.RESTRICT, related_name='asset_brands')
    unit          = models.ForeignKey("onboarding.TypeAssist", verbose_name=_("Unit"), null = True, blank=True, on_delete=models.RESTRICT, related_name='asset_units')
    capacity      = models.DecimalField(_("Capacity"), default=0.0, max_digits=18, decimal_places=2)
    serv_prov     = models.ForeignKey("onboarding.Bt", verbose_name=_( "Client"), on_delete = models.RESTRICT, null=True, related_name='asset_serv_providers')
    asset_json    = models.JSONField( encoder = DjangoJSONEncoder, blank=True, null=True, default=asset_json)

    class Meta(BaseModel.Meta):
        db_table            = 'asset'
        verbose_name        = 'Asset'
        verbose_name_plural = 'Assets'

    def __str__(self):
        return f'{self.assetname} ({self.assetcode})'


class Jobneed(BaseModel, TenantAwareModel):
    class Priority(models.TextChoices):
        HIGH   = ('HIGH', 'High')
        LOW    = ('LOW', 'Low')
        MEDIUM = ('MEDIUM', 'Medium')


    class Identifier(models.TextChoices):
        TASK             = ('TASK', 'Task')
        TICKET           = ('TICKET', 'Ticket')
        INTERNALTOUR     = ('INTERNALTOUR', 'Internal Tour')
        EXTERNALTOUR     = ('EXTERNALTOUR', 'External Tour')
        PPM              = ('PPM', 'PPM')
        OTHER            = ('OTHER', 'Other')
        SITEREPORT       = ("SITEREPORT","Site Report")
        INCIDENTREPORT   = ('INCIDENTREPORT', "Incident Report")
        ASSETLOG         = ("ASSETLOG",	"Asset Log")
        ASSETMAINTENANCE = ("ASSETMAINTENANCE",	"Asset Maintenance")


    class Scantype(models.TextChoices):
        NONE    = ('NONE', 'None')
        QR      = ('QR', 'QR')
        NFC     = ('NFC', 'NFC')
        SKIP    = ('SKIP', 'Skip')
        ENTERED = ('ENTERED', 'Entered')
    
    
    class JobStatus(models.TextChoices):
        ASSIGNED           = ('ASSIGNED', 'Assigned')
        AUTOCLOSED         = ('AUTOCLOSED', 'Auto Closed')
        COMPLETED          = ('COMPLETED', 'Completed')
        INPROGRESS         = ('INPROGRESS', 'Inprogress')
        PARTIALLYCOMPLETED = ('PARTIALLYCOMPLETED', 'Partially Completed')
        RESOLVED           = ("RESOLVED",  "Resolved")
        OPEN               = ("OPEN",      "Open")
        CANCELLED          = ("CANCELLED", "Cancelled")
        ESCALATED          = ("ESCALATED", "Escalated")
        NEW                = ("NEW",       "New")
        MAINTENANCE        = ("MAINTENANCE", "Maintenance")
        STANDBY            = ("STANDBY", "Standby")
        WORKING            = ("WORKING", "Working")
        SCRAPPED           = ("SCRAPPED", "Scrapped")

    

    
    class JobType(models.TextChoices):
        SCHEDULE = ('SCHEDULE', 'Schedule')
        ADHOC    = ('ADHOC', 'Adhoc')
    

    
    class Frequency(models.TextChoices):
        NONE        = ('NONE','None')
        DAILY       = ("DAILY","Daily")
        WEEKLY      = ("WEEKLY","Weekly")
        MONTHLY     = ("MONTHLY", "Monthly")
        BIMONTHLY   = ("BIMONTHLY","Bimonthly")
        QUARTERLY   = ("QUARTERLY","Quarterly")
        HALFYEARLY  = ("HALFYEARLY","Half Yearly")
        YEARLY      = ("YEARLY", "Yearly")
        FORTNIGHTLY = ("FORTNIGHTLY", "Fort Nightly")
 
    jobdesc           = models.CharField(_("Job Description"), max_length=200)
    plandatetime      = models.DateTimeField(_("Plan date time"), auto_now=False, auto_now_add=False)
    expirydatetime    = models.DateTimeField(_("Expiry date time"), auto_now=False, auto_now_add=False)
    gracetime         = models.IntegerField(_("Grace time"))
    recievedon_server = models.DateTimeField(_("Recived on server"), auto_now=False, auto_now_add=True)
    starttime         = models.DateTimeField( _("Start time"), auto_now=False, auto_now_add=False, null=True)
    endtime           = models.DateTimeField(_("Start time"), auto_now=False, auto_now_add=False, null=True)
    gpslocation       = PointField(_('GPS Location'),null=True, geography=True, srid=4326)
    remarks           = models.CharField(_("Remark"), max_length=200, null=True, blank=True)
    asset             = models.ForeignKey("activity.Asset", verbose_name=_("Asset"), on_delete= models.RESTRICT, null=True, blank=True, related_name='jobneed_assets')
    frequency         = models.CharField(verbose_name=_("Frequency type"), null       = True, max_length=55, choices=Frequency.choices)
    job               = models.ForeignKey("activity.Job", verbose_name=_("Job"), on_delete  = models.RESTRICT, null=True, blank=True, related_name='jobs')
    jobstatus         = models.CharField('Job Status', choices = JobStatus.choices, max_length=60, null=True)
    jobtype           = models.CharField(_("Job Type"), max_length=50, choices=JobType.choices, null=True)
    performed_by      = models.ForeignKey("peoples.People", verbose_name=_("Performed by"), on_delete = models.RESTRICT, null=True, blank=True, related_name='jobneed_performedby')
    priority          = models.CharField(_("Priority"), max_length=50, choices=Priority.choices)
    qset              = models.ForeignKey("activity.QuestionSet", verbose_name=_("QuestionSet"), on_delete  = models.RESTRICT, null=True, blank=True)
    scantype          = models.CharField(_("Scan type"), max_length=50, choices=Scantype.choices)
    people            = models.ForeignKey("peoples.People", verbose_name=_("People"), on_delete = models.RESTRICT,  null=True, blank=True)
    pgroup            = models.ForeignKey("peoples.Pgroup", verbose_name=_("Group"), on_delete= models.RESTRICT,  null=True, blank=True)
    identifier        = models.CharField(_("Jobneed Type"), max_length=50, choices=Identifier.choices, null=True)
    parent            = models.ForeignKey("self", verbose_name=_("Belongs to"),  on_delete  = models.RESTRICT,  null=True, blank=True)
    alerts            = models.BooleanField(_("Alerts"), default=False, null=True)
    ticketno          = models.IntegerField(_("Ticket No"), default=0)
    slno              = models.SmallIntegerField(_("Sl No."))
    client            = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete= models.RESTRICT, null=True, blank=True, related_name='jobneed_clients')
    bu                = models.ForeignKey("onboarding.Bt", verbose_name=_("Site"), on_delete = models.RESTRICT, null=True, blank=True, related_name='jobneedf_bus')
    ticket_category   = models.ForeignKey("onboarding.TypeAssist", verbose_name=_("Ticket Category"), null= True, blank=True, on_delete=models.RESTRICT)
    othersite         = models.CharField(_("Other Site"), max_length=100, default=None, null=True)
    mult_factor       = models.DecimalField(_("Multiplication Factor"), default=1, max_digits=10, decimal_places=6)
    raisedby          = models.CharField(_("Raised by"), max_length=55, default="", null=True)
    raisedtktflag     = models.BooleanField(_("RaiseTicketFlag"), default=False, null=True)
    other_info        = models.JSONField(_("Other info"), default=other_info, blank=True, encoder=DjangoJSONEncoder)
    ctzoffset         = models.IntegerField(_("TZ_Offset"),  null=True, blank=True)

    class Meta(BaseModel.Meta):
        db_table            = 'jobneed'
        verbose_name        = 'Jobneed'
        verbose_name_plural = 'Jobneeds'
        constraints         = [
            models.CheckConstraint(
                check=models.Q(gracetime__gte=0),
                name='jobneed_gracetime_gte_0_ck'
            ),
        ]


class JobneedDetails(BaseModel, TenantAwareModel):
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
    
    slno         = models.SmallIntegerField(_("SL No."))
    question     = models.ForeignKey("activity.Question", verbose_name=_("Question"),  null=True, blank=True, on_delete=models.RESTRICT)
    answertype   = models.CharField(_("Answer Type"), max_length=50, choices=AnswerType.choices, null=True)
    answer       = models.CharField(_("Answer"), max_length=250, default="")
    options      = models.CharField( _("Option"), max_length=200, null=True, blank=True)
    min          = models.DecimalField(_("Min"), max_digits=18,  decimal_places=4, null=True)
    max          = models.DecimalField(_("Max"), max_digits=18, decimal_places=4, null=True)
    alerton      = models.CharField( _("Alert On"), null=True, blank=True, max_length=50)
    is_mandatory = models.BooleanField(_("Is Mandatory"), default=False)
    jobneed      = models.ForeignKey("activity.Jobneed", verbose_name=_( "Jobneed"), null=True, blank=True, on_delete=models.RESTRICT)
    alerts       = models.BooleanField(_("Alerts"), default=False)

    class Meta(BaseModel.Meta):
        db_table     = 'jobneeddetails'
        verbose_name = 'JobneedDetails'


class Attachment(BaseModel, TenantAwareModel):
    class AttachmentType(models.TextChoices):
        NONE  = ('NONE', 'NONE')
        ATMT  = ("ATTACHMENT","Attachment")
        REPLY = ("REPLY", "Reply")
        SIGN  = ("SIGN",  "SIGN")
    
    filepath       = models.CharField(max_length=100, null=True, blank=True)
    filename       = models.ImageField(null=True, blank=True)
    ownername      = models.ForeignKey("onboarding.Typeassist", on_delete=models.RESTRICT, null=True, blank=True)
    owner          = models.IntegerField(default = -1)
    bu             = models.ForeignKey("onboarding.Bt", null=True,blank=True, on_delete=models.RESTRICT)
    datetime       = models.DateTimeField(editable=True, default=datetime.utcnow)
    attachmenttype = models.CharField(choices = AttachmentType.choices, max_length=55, default=AttachmentType.NONE)
    gpslocation    = PointField(_('GPS Location'),null=True, geography=True, srid=4326)

    class Meta(BaseModel.Meta):
        db_table = 'attachment'
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self):
        return self.filename.name
    

def tickethistory():
    return {
        'history':[]
    }

class Device(BaseModel, TenantAwareModel):
    devicecode    = models.CharField(max_length=50)
    devicename    = models.CharField(max_length=50)
    belongsTo     = models.ForeignKey('self', null=True, blank=True, on_delete=models.RESTRICT)
    enable        = models.BooleanField(default=True)
    runningStatus = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete=models.RESTRICT,related_name='device_status')
    devicetype    = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete=models.RESTRICT, related_name='device_types')
    devicedesc    = models.CharField(null=True, max_length=50)
    ipaddress     = models.CharField(null=True , blank=True, max_length=100)
    bu            = models.ForeignKey("onboarding.Bt", null=True,blank=True, on_delete=models.RESTRICT)

    class Meta(BaseModel.Meta):
        db_table = 'device'
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self):
        return self.devicecode


class Event(BaseModel, TenantAwareModel):
    eventdesc     = models.CharField(max_length=250, null=True, blank=True)
    device      = models.ForeignKey("activity.Device", null=True, blank=True, on_delete=models.RESTRICT, related_name='event_device')
    eventdatetime = models.DateTimeField(default=timezone.now)
    eventtype     = models.ForeignKey("onboarding.TypeAssist", null=True, blank=True, on_delete=models.RESTRICT, related_name='event_types')
    category      = models.IntegerField(null=True, blank=True)
    source        = models.CharField(max_length=100, null=True, blank=True)
    note          = models.CharField(max_length=100, null=True, blank=True)
    starttime     = models.DateTimeField(editable=True, null=True, blank=True)
    endtime       = models.DateTimeField(editable=True, null=True, blank=True)
    bu         = models.ForeignKey("onboarding.Bt", null=True,blank=True, on_delete=models.RESTRICT)

    class Meta(BaseModel.Meta):
        db_table = 'event'
        get_latest_by = ["cdtz", 'mdtz']

    def __str__(self):
        return self.eventdesc
    
def ticket_defaults():
    return {"statusjbdata":[]}

class Ticket(BaseModel, TenantAwareModel):
    class Priority(models.TextChoices):
        HIGH   = ('HIGH', 'High')
        LOW    = ('LOW', 'Low')
        MEDIUM = ('MEDIUM', 'Medium')
    
    class Status(models.TextChoices):
        NEW       = ('NEW','New')
        CANCEL    = ('CANCEL','Cancel')
        CLOSE     = ('CLOSE','Close')
        ESCALATED = ('ESCALATED','Escalated' )
        ASSIGNED  = ('ASSIGNED','Assigned' )

    class TicketSource(models.TextChoices):
        SYSTEMGENERATED = ('SYSTEMGENERATED', 'System Generated')
        USERDEFINED     = ('USERDEFINED', 'User Defined')


    ticketno           = models.IntegerField(null=True,blank=True)   
    ticketdesc         = models.CharField(max_length=250)
    assignedtopeople   = models.ForeignKey('peoples.People', null=True, blank=True, on_delete=models.RESTRICT, related_name="ticket_people")
    assignedtogroup    = models.ForeignKey('peoples.Pgroup', null=True, blank=True, on_delete=models.RESTRICT, related_name="ticket_grps")
    comments           = models.CharField(max_length=250, null=True)
    bu                 = models.ForeignKey("onboarding.Bt", null=True,blank=True, on_delete=models.RESTRICT)
    priority           = models.CharField(_("Priority"), max_length=50, choices=Priority.choices, null=True, blank=True)
    escalationtemplate = models.CharField(max_length=30, null=True, blank=True)
    modifieddatetime   = models.DateTimeField(default=timezone.now)
    level              = models.IntegerField(default=0)
    status             = models.CharField(_("Status"), max_length=50, choices=Status.choices,null=True, blank=True)
    performedby        = models.ForeignKey('peoples.People', null=True, blank=True, on_delete=models.RESTRICT, related_name="ticket_performedby")
    ticketlog          = models.JSONField(null=True,  encoder=DjangoJSONEncoder, blank=True, default=ticket_defaults)
    event              = models.ForeignKey("activity.Event", null=True,blank=True, on_delete=models.RESTRICT)
    isescalated        = models.BooleanField(default=True)
    ticketsource       = models.CharField(max_length=50, choices=TicketSource.choices, null=True, blank=True)

    class Meta(BaseModel.Meta):
            db_table      = 'ticket'
            get_latest_by = ["cdtz", 'mdtz']
            constraints         = [
                models.UniqueConstraint(
                    fields=['bu', 'ticketno'],
                    name='bu_ticketno_uk'
                )
            ]

    def __str__(self):
        return self.ticketdesc




class EscalationMatrix(BaseModel, TenantAwareModel):
    class Frequency(models.TextChoices):
        MINUTE = ('MINUTE', 'MINUTE')
        HOUR   = ('HOUR', 'HOUR')
        DAY    = ('DAY', 'DAY')
        WEEK   = ('WEEK', 'WEEK')
    
    body           = models.CharField(max_length=500, null=True)
    level          = models.IntegerField(null=True, blank=True)
    frequency      = models.CharField(max_length=10, default='DAY', choices=Frequency.choices)
    frequencyvalue = models.IntegerField(null=True, blank=True)
    assignedfor    = models.CharField(max_length=50)
    assignedperson = models.ForeignKey('peoples.People', null=True, blank=True, on_delete=models.RESTRICT, related_name="escalation_people")
    assignedgroup  = models.ForeignKey('peoples.Pgroup', null=True, blank=True, on_delete=models.RESTRICT, related_name="escalation_grps")
    bu             = models.ForeignKey("onboarding.Bt", null=True,blank=True, on_delete=models.RESTRICT)
    escalationtemplate = models.CharField(max_length=30)
    notify         = models.TextField(blank=True, null=True)
    bu             = models.ForeignKey("onboarding.Bt", null=True,blank=True, on_delete=models.RESTRICT)

    class Meta(BaseModel.Meta):
        db_table = 'escalationmatrix'
        get_latest_by = ["mdtz", 'cdtz']