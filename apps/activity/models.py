import uuid
from apps.peoples.models import BaseModel
from apps.activity.managers import (AssetManager, AttachmentManager,
JobManager, JobneedDetailsManager, QsetBlngManager, QuestionManager, ESCManager,LocationManager,
QuestionSetManager, JobneedManager, DELManager, WorkpermitManager, TicketManager)
from apps.tenants.models import TenantAwareModel
from django.utils.translation import gettext_lazy as _
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.postgres.fields import ArrayField
from django.db import models
from datetime import datetime
from django.contrib.gis.db.models import PointField
from django.utils import timezone
from django.conf import settings

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
        PEOPLELIST  = "PEOPLELIST" , _("People List")
        SITELIST    = "SITELIST"   , _("Site List")
    
    class AvptType(models.TextChoices):
        NONE  = "NONE",  _('NONE')
        BACKCAMPIC  = "BACKCAMPIC",  _('Back Camera Pic')
        FRONTCAMPIC = "FRONTCAMPIC", _('Front Camera Pic')
        AUDIO       = "AUDIO",       _('Audio')
        VIDEO       = "VIDEO",       _("Video")

    # id= models.BigIntegerField(primary_key = True)
    quesname  = models.CharField(_("Question Name"), max_length = 200)
    options    = models.TextField(_('Options'), max_length = 2000, null = True)
    min        = models.DecimalField(_("Min"), null = True, blank = True, max_digits = 18, decimal_places = 2, default = 0.00)
    max        = models.DecimalField( _('Max'), null = True, blank = True, max_digits = 18, decimal_places = 2, default = 0.00)
    alerton    = models.CharField(_("Alert on"), max_length = 300, null = True)
    answertype = models.CharField(verbose_name = _("Type"), choices = AnswerType.choices, default="NUMERIC", max_length = 55)  # type in previous
    unit       = models.ForeignKey("onboarding.TypeAssist", verbose_name = _( "Unit"), on_delete = models.RESTRICT, related_name="unit_types", null = True, blank = True)
    client     = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, null = True, blank = True)
    isworkflow = models.BooleanField(_("Is WorkFlow"), default = False)
    enable     = models.BooleanField(_("Enable"), default = True)
    category   = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Category"), on_delete = models.RESTRICT, related_name='category_types', null = True, blank = True)
    avpttype = models.CharField(_("Attachment Type"), max_length = 50, choices = AvptType.choices, null = True, blank = True)
    isavpt   = models.BooleanField(_("Is Attachment Required"), default = False)

    
    objects = QuestionManager()

    class Meta(BaseModel.Meta):
        db_table = 'question'
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'
        constraints = [models.UniqueConstraint(
            fields=['quesname', 'answertype', 'client'], name='ques_name_type_client_uk')]

    def __str__(self) -> str:
        return f"{self.quesname} | {self.answertype}"

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
        CHECKLIST                = "CHECKLIST",                _('Checklist')
        INCIDENTREPORTTEMPLATE   = "INCIDENTREPORTTEMPLATE",   _('Incident Report Template')
        SITEREPORTTEMPLATE       = "SITEREPORTTEMPLATE",       _('Site Report Template')
        WORKPERMITTEMPLATE       = "WORKPERMITTEMPLATE",       _('Work Permit Template')
        RETURNWORKPERMITTEMPLATE = "RETURNWORKPERMITTEMPLATE", _('Return Work Permit Template')
        KPITEMPLATE              = "KPITEMPLATE",              _('Kpi Template')
        SCRAPPEDTEMPLATE         = "SCRAPPEDTEMPLATE",         _('Scrapped Template')
        ASSETAUDIT               = "ASSETAUDIT",               _('Asset Audit')
        MAINTENANCETEMPLATE      = "MAINTENANCETEMPLATE",      _('Maintenance Template')
        ASSETMAINTENANCE         = "ASSETMAINTENANCE",         _('Asset Maintenance')
        QUESTIONSET              = "QUESTIONSET",              _('Question Set')

    # id            = models.BigIntegerField(primary_key = True)
    qsetname           = models.CharField(_("QuestionSet Name"), max_length = 200)
    enable             = models.BooleanField(_("Enable"), default = True)
    assetincludes      = ArrayField(models.CharField(max_length = 50, blank = True), null = True, blank = True, verbose_name= _("Asset Includes"))
    buincludes         = ArrayField(models.CharField(max_length = 50, blank = True), null = True, blank = True, verbose_name= _("Bu Includes"))
    seqno              = models.SmallIntegerField(_("SL No."), default = 1)
    parent             = models.ForeignKey("self", verbose_name = _("Belongs To"), on_delete = models.RESTRICT, null = True, blank = True)
    type               = models.CharField( _("Question Set Type"), choices = Type.choices, null = True, max_length = 50)
    bu                 = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, related_name='qset_bus', null = True, blank = True)
    client             = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, related_name='qset_clients', null = True, blank = True)
    site_grp_includes  = ArrayField(models.CharField(max_length = 50, blank = True), null = True, blank = True, verbose_name= _("Site Group Includes"))
    site_type_includes = ArrayField(models.CharField(max_length = 50, blank = True), null = True, blank = True, verbose_name= _("Site Type Includes"))
    url                = models.CharField(_("Url"), max_length = 250, null = True, blank = True)

    objects = QuestionSetManager()

    class Meta(BaseModel.Meta):
        db_table            = 'questionset'
        verbose_name        = 'QuestionSet'
        verbose_name_plural = 'QuestionSets'
        constraints         = [
            models.UniqueConstraint(
                fields=['qsetname', 'parent', 'type', 'client', 'bu'],
                name='name_type_parent_type_client_bu_uk'
            ),
            models.CheckConstraint(
                check = models.Q(seqno__gte = 0),
                name='slno_gte_0_ck')
        ]

    def __str__(self) -> str:
        return self.qsetname

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
        NONE        = ("NONE", "NONE")
        
    class AvptType(models.TextChoices):
        BACKCAMPIC    = "BACKCAMPIC"   , _('Back Camera Pic')
        FRONTCAMPIC        = "FRONTCAMPIC"       , _('Front Camera Pic')
        AUDIO    = "AUDIO"   , _('Audio')
        VIDEO     = "VIDEO"    , _("Video")
        NONE = ("NONE", "NONE")

    # id               = models.BigIntegerField(_("QSB Id"), primary_key = True)
    ismandatory       = models.BooleanField(_("Is Manadatory"))
    isavpt            = models.BooleanField(_("Is Attachment Required"), default = False)
    seqno             = models.SmallIntegerField(_("Seq No."))
    qset              = models.ForeignKey("activity.QuestionSet", verbose_name = _("Question Set"), on_delete = models.RESTRICT, null = True, blank = True)
    question          = models.ForeignKey("activity.Question", verbose_name = _("Question"), null = True, blank = False,  on_delete = models.RESTRICT)
    answertype        = models.CharField(_("Question Type"), max_length = 50, choices = AnswerType.choices)
    avpttype        = models.CharField(_("Attachment Type"), max_length = 50, choices = AvptType.choices, null = True, blank = True)
    max               = models.DecimalField(_("Max"), null = True, max_digits = 18, decimal_places = 2, default = 0.00)
    min               = models.DecimalField(_("Min"), null = True, max_digits = 18, decimal_places = 2, default = 0.00)
    alerton           = models.CharField(_("Alert on"), null = True, blank = True, max_length = 300)
    options           = models.CharField(_("Option"), max_length = 200, null = True, blank = True)
    client            = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, null = True, blank = True, related_name='qsetbelong_client')
    alertmails_sendto = models.JSONField( _("Alert mails send to"), encoder = DjangoJSONEncoder, default = alertmails_sendto)
    bu                = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='qsetbelong_bu')
    client            = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, null = True, blank = True, related_name='qsetbelong_client')

    objects = QsetBlngManager()
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
        'deviation':False,
    }

def geojson_jobnjobneed():
    return {
        'gpslocation':""
    }
class Job(BaseModel, TenantAwareModel):
    class Identifier(models.TextChoices):
        TASK             = ('TASK', 'Task')
        TICKET           = ('TICKET', 'Ticket')
        INTERNALTOUR     = ('INTERNALTOUR', 'Internal Tour')
        EXTERNALTOUR     = ('EXTERNALTOUR', 'External Tour')
        PPM              = ('PPM', 'PPM')
        OTHER            = ('OTHER', 'Other')
        SITEREPORT       = ("SITEREPORT", "Site Report")
        INCIDENTREPORT   = ('INCIDENTREPORT', "Incident Report")
        ASSETLOG         = ("ASSETLOG",	"Asset Log")
        ASSETMAINTENANCE = ("ASSETMAINTENANCE",	"Asset Maintenance")
        GEOFENCE         = ('GEOFENCE', 'Geofence')

    class Priority(models.TextChoices):
        HIGH   = "HIGH" , _('High')
        LOW    = "LOW"  , _('Low')
        MEDIUM = "MEDIUM", _('Medium')

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

    # id          = models.BigIntegerField(_("Job Id"), primary_key = True)
    jobname         = models.CharField(_("Name"), max_length = 100)
    jobdesc         = models.CharField(_("Description"), max_length = 500)
    fromdate        = models.DateTimeField( _("From date"), auto_now = False, auto_now_add = False)
    uptodate        = models.DateTimeField( _("To date"), auto_now = False, auto_now_add = False)
    cron            = models.CharField(_("Cron Exp."), max_length = 200, default='* * * * *')
    identifier      = models.CharField(_("Job Type"), max_length = 100, choices = Identifier.choices, null = True)
    planduration    = models.IntegerField(_("Plan duration (min)"))
    gracetime       = models.IntegerField(_("Grace Time"))
    expirytime      = models.IntegerField(_("Expiry Time"))
    lastgeneratedon = models.DateTimeField(_("Last generatedon"), auto_now = False, auto_now_add = True)
    asset           = models.ForeignKey("activity.Asset", verbose_name = _("Asset"), on_delete = models.RESTRICT, null = True, blank = True)
    priority        = models.CharField(_("Priority"), max_length = 100, choices = Priority.choices)
    qset            = models.ForeignKey("activity.QuestionSet", verbose_name = _("QuestionSet"), on_delete = models.RESTRICT, null = True, blank = True)
    people          = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name = _( "Aggresive auto-assign to People"), on_delete = models.RESTRICT, null = True, blank = True, related_name='job_aaatops')
    pgroup          = models.ForeignKey("peoples.Pgroup", verbose_name = _("People Group"), on_delete = models.RESTRICT, null = True, blank = True, related_name='job_pgroup')
    sgroup          = models.ForeignKey("peoples.Pgroup", verbose_name = _("Site Group"), on_delete= models.RESTRICT,  null = True, blank = True, related_name='job_sgroup')
    geofence        = models.ForeignKey("onboarding.GeofenceMaster", verbose_name = _("Geofence"), on_delete = models.RESTRICT, null = True, blank = True)
    parent          = models.ForeignKey("self", verbose_name = _("Belongs to"), on_delete = models.RESTRICT, null = True, blank = True)
    seqno           = models.SmallIntegerField(_("Serial No."))
    client          = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, related_name='job_clients', null = True, blank = True)
    bu              = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, related_name='job_bus', null = True, blank = True)
    shift           = models.ForeignKey("onboarding.Shift", verbose_name = _("Shift"), on_delete = models.RESTRICT, null = True, related_name="job_shifts")
    starttime       = models.TimeField(_("Start time"), auto_now = False, auto_now_add = False, null = True)
    endtime         = models.TimeField(_("End time"), auto_now = False, auto_now_add = False, null = True)
    ticketcategory  = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Ticket Category"), on_delete = models.RESTRICT, null = True, blank = True, related_name="job_tktcategories")
    scantype        = models.CharField(_("Scan Type"), max_length = 50, choices = Scantype.choices)
    frequency       = models.CharField(verbose_name = _("Frequency type"), null = True, max_length = 55, choices = Frequency.choices, default = Frequency.NONE.value)
    other_info      = models.JSONField(_("Other info"), default = other_info, blank = True, encoder = DjangoJSONEncoder)
    geojson         = models.JSONField(default = geojson_jobnjobneed, blank = True, null=True, encoder = DjangoJSONEncoder)
    enable          = models.BooleanField(_("Enable"), default = True)

    objects = JobManager()

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
                check = models.Q(gracetime__gte = 0),
                name='gracetime_gte_0_ck'
            ),
            models.CheckConstraint(
                check = models.Q(planduration__gte = 0),
                name='planduration_gte_0_ck'
            ),
            models.CheckConstraint(
                check = models.Q(expirytime__gte = 0),
                name='expirytime_gte_0_ck'
            )
        ]

    def __str__(self):
        return self.jobname

def asset_json():
    return {
        'service': "",
        'ismeter':False,
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
        "multifactor": 1
    }


class Asset(BaseModel, TenantAwareModel):
    class Identifier(models.TextChoices):
       NONE       = ("NONE", "None")
       ASSET      = ("ASSET", "Asset")
       CHECKPOINT = ("CHECKPOINT", "Checkpoint")
       NEA        = ("NEA", "Non Engineering Asset")

    class RunningStatus(models.TextChoices):
        MAINTENANCE = ("MAINTENANCE", "Maintenance")
        STANDBY     = ("STANDBY", "Standby")
        WORKING     = ("WORKING", "Working")
        SCRAPPED    = ("SCRAPPED", "Scrapped")

    uuid          = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    assetcode     = models.CharField(_("Asset Code"), max_length = 50, unique=True)
    assetname     = models.CharField(_("Asset Name"), max_length = 250)
    enable        = models.BooleanField(_("Enable"), default = True)
    iscritical    = models.BooleanField(_("Is Critical"))
    gpslocation   = PointField(_('GPS Location'), null = True, geography = True, srid = 4326, blank = True)
    parent        = models.ForeignKey("self", verbose_name = _( "Belongs to"), on_delete = models.RESTRICT, null = True, blank = True)
    identifier    = models.CharField( _('Asset Identifier'), choices = Identifier.choices, max_length = 55, default = Identifier.NONE.value)
    runningstatus = models.CharField(_('Running Status'), choices = RunningStatus.choices, max_length = 55)
    type          = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Type"), on_delete = models.RESTRICT, null = True, blank = True, related_name='asset_types')
    client        = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, null = True, blank = True, related_name='asset_clients')
    bu            = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='asset_bus')
    category      = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Category"), null = True, blank = True, on_delete = models.RESTRICT, related_name='asset_categories')
    subcategory   = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Sub Category"), null = True, blank = True, on_delete = models.RESTRICT, related_name='asset_subcategories')
    brand         = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Brand"), null = True, blank = True, on_delete = models.RESTRICT, related_name='asset_brands')
    unit          = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Unit"), null = True, blank = True, on_delete = models.RESTRICT, related_name='asset_units')
    capacity      = models.DecimalField(_("Capacity"), default = 0.0, max_digits = 18, decimal_places = 2)
    servprov      = models.ForeignKey("onboarding.Bt", verbose_name = _( "Client"), on_delete = models.RESTRICT, null = True, related_name='asset_serv_providers')
    location      = models.ForeignKey("activity.Location", verbose_name=_("Location"), on_delete=models.RESTRICT, null=True, blank=True)
    asset_json    = models.JSONField( encoder = DjangoJSONEncoder, blank = True, null = True, default = asset_json)

    objects = AssetManager()

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
        SITEREPORT       = ("SITEREPORT", "Site Report")
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
        NONE        = ('NONE', 'None')
        DAILY       = ("DAILY", "Daily")
        WEEKLY      = ("WEEKLY", "Weekly")
        MONTHLY     = ("MONTHLY", "Monthly")
        BIMONTHLY   = ("BIMONTHLY", "Bimonthly")
        QUARTERLY   = ("QUARTERLY", "Quarterly")
        HALFYEARLY  = ("HALFYEARLY", "Half Yearly")
        YEARLY      = ("YEARLY", "Yearly")
        FORTNIGHTLY = ("FORTNIGHTLY", "Fort Nightly")

    uuid             = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    jobdesc          = models.CharField(_("Job Description"), max_length = 200)
    plandatetime     = models.DateTimeField(_("Plan date time"), auto_now = False, auto_now_add = False)
    expirydatetime   = models.DateTimeField(_("Expiry date time"), auto_now = False, auto_now_add = False)
    gracetime        = models.IntegerField(_("Grace time"))
    receivedonserver = models.DateTimeField(_("Recived on server"), auto_now = False, auto_now_add = True)
    starttime        = models.DateTimeField( _("Start time"), auto_now = False, auto_now_add = False, null = True)
    endtime          = models.DateTimeField(_("Start time"), auto_now = False, auto_now_add = False, null = True)
    gpslocation      = PointField(_('GPS Location'),null = True, geography = True, srid = 4326)
    remarks          = models.CharField(_("Remark"), max_length = 200, null = True, blank = True)
    asset            = models.ForeignKey("activity.Asset", verbose_name = _("Asset"), on_delete= models.RESTRICT, null = True, blank = True, related_name='jobneed_assets')
    frequency        = models.CharField(verbose_name = _("Frequency type"), null = True, max_length = 55, choices = Frequency.choices, default = Frequency.NONE.value)
    job              = models.ForeignKey("activity.Job", verbose_name = _("Job"), on_delete  = models.RESTRICT, null = True, blank = True, related_name='jobs')
    jobstatus        = models.CharField('Job Status', choices = JobStatus.choices, max_length = 60, null = True)
    jobtype          = models.CharField(_("Job Type"), max_length = 50, choices = JobType.choices, null = True)
    performedby      = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name = _("Performed by"), on_delete = models.RESTRICT, null = True, blank = True, related_name='jobneed_performedby')
    priority         = models.CharField(_("Priority"), max_length = 50, choices = Priority.choices)
    qset             = models.ForeignKey("activity.QuestionSet", verbose_name = _("QuestionSet"), on_delete  = models.RESTRICT, null = True, blank = True)
    scantype         = models.CharField(_("Scan type"), max_length = 50, choices = Scantype.choices, default = Scantype.NONE.value)
    people           = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name = _("People"), on_delete = models.RESTRICT,  null = True, blank = True)
    pgroup           = models.ForeignKey("peoples.Pgroup", verbose_name = _("People Group"), on_delete= models.RESTRICT,  null = True, blank = True, related_name='jobneed_pgroup')
    sgroup           = models.ForeignKey("peoples.Pgroup", verbose_name = _("Site Group"), on_delete= models.RESTRICT,  null = True, blank = True, related_name='jobneed_sgroup')
    identifier       = models.CharField(_("Jobneed Type"), max_length = 50, choices = Identifier.choices, null = True)
    parent           = models.ForeignKey("self", verbose_name = _("Belongs to"),  on_delete  = models.RESTRICT,  null = True, blank = True)
    alerts           = models.BooleanField(_("Alerts"), default = False, null = True)
    seqno            = models.SmallIntegerField(_("Sl No."))
    client           = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='jobneed_clients')
    bu               = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='jobneedf_bus')
    ticketcategory   = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Ticket Category"), null= True, blank = True, on_delete = models.RESTRICT)
    othersite        = models.CharField(_("Other Site"), max_length = 100, default = None, null = True)
    multifactor      = models.DecimalField(_("Multiplication Factor"), default = 1, max_digits = 10, decimal_places = 6)
    raisedby         = models.CharField(_("Raised by"), max_length = 55, default="", null = True)
    raisedtktflag    = models.BooleanField(_("RaiseTicketFlag"), default = False, null = True)
    ismailsent       = models.BooleanField(_('Is Mail Sent'), default= False)
    attachmentcount  = models.IntegerField(_('Attachment Count'), default = 0)
    other_info       = models.JSONField(_("Other info"), default = other_info, blank = True, encoder = DjangoJSONEncoder)
    geojson          = models.JSONField(default = geojson_jobnjobneed, blank = True,null=True, encoder = DjangoJSONEncoder)
    deviation        = models.BooleanField(_("Deviation"), default = False, null=True)


    objects = JobneedManager()

    class Meta(BaseModel.Meta):
        db_table            = 'jobneed'
        verbose_name        = 'Jobneed'
        verbose_name_plural = 'Jobneeds'
        constraints         = [
            models.CheckConstraint(
                check = models.Q(gracetime__gte = 0),
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
        NONE        = ("NONE", "NONE")
    
    class AvptType(models.TextChoices):
        BACKCAMPIC    = "BACKCAMPIC"   , _('Back Camera Pic')
        FRONTCAMPIC        = "FRONTCAMPIC"       , _('Front Camera Pic')
        AUDIO    = "AUDIO"   , _('Audio')
        VIDEO     = "VIDEO"    , _("Video")
        NONE = ("NONE", "NONE")

# id              = models.BigIntegerField(_("Jobneed details"), primary_key = True)
    uuid            = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    seqno           = models.SmallIntegerField(_("SL No."))
    question        = models.ForeignKey("activity.Question", verbose_name = _("Question"),  null = True, blank = True, on_delete = models.RESTRICT)
    answertype      = models.CharField(_("Answer Type"), max_length = 50, choices = AnswerType.choices, null = True)
    answer          = models.CharField(_("Answer"), max_length = 250, default="", null = True)
    isavpt          = models.BooleanField(_("Is Attachement Required"), default = False)
    avpttype        = models.CharField(_("Attachment Type"), max_length = 50, choices = AvptType.choices, null=True, blank=True)
    options         = models.CharField( _("Option"), max_length = 200, null = True, blank = True)
    min             = models.DecimalField(_("Min"), max_digits = 18,  decimal_places = 4, null = True)
    max             = models.DecimalField(_("Max"), max_digits = 18, decimal_places = 4, null = True)
    alerton         = models.CharField( _("Alert On"), null = True, blank = True, max_length = 50)
    ismandatory     = models.BooleanField(_("Is Mandatory"), default = True)
    jobneed         = models.ForeignKey("activity.Jobneed", verbose_name = _( "Jobneed"), null = True, blank = True, on_delete = models.RESTRICT)
    alerts          = models.BooleanField(_("Alerts"), default = False)
    attachmentcount = models.IntegerField(_('Attachment count'), default = 0)

    objects = JobneedDetailsManager()

    class Meta(BaseModel.Meta):
        db_table     = 'jobneeddetails'
        verbose_name = 'JobneedDetails'

class Attachment(BaseModel, TenantAwareModel):
    class AttachmentType(models.TextChoices):
        NONE  = ('NONE', 'NONE')
        ATMT  = ("ATTACHMENT", "Attachment")
        REPLY = ("REPLY", "Reply")
        SIGN  = ("SIGN",  "SIGN")

    uuid           = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    filepath       = models.CharField(max_length = 100, null = True, blank = True)
    filename       = models.ImageField(null = True, blank = True)
    ownername      = models.ForeignKey("onboarding.Typeassist", on_delete = models.RESTRICT, null = True, blank = True)
    owner          = models.CharField(null= True, max_length = 255)
    bu             = models.ForeignKey("onboarding.Bt", null = True,blank = True, on_delete = models.RESTRICT)
    datetime       = models.DateTimeField(editable = True, default = datetime.utcnow)
    attachmenttype = models.CharField(choices = AttachmentType.choices, max_length = 55, default = AttachmentType.NONE.value)
    gpslocation    = PointField(_('GPS Location'),null = True, geography = True, srid = 4326)

    objects = AttachmentManager()
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
    # id     = models.BigIntegerField(_("Device Id"), primary_key = True)
    devicecode    = models.CharField(max_length = 50)
    devicename    = models.CharField(max_length = 50)
    belongsTo     = models.ForeignKey('self', null = True, blank = True, on_delete = models.RESTRICT)
    enable        = models.BooleanField(default = True)
    runningStatus = models.ForeignKey("onboarding.TypeAssist", null = True, blank = True, on_delete = models.RESTRICT,related_name='device_status')
    devicetype    = models.ForeignKey("onboarding.TypeAssist", null = True, blank = True, on_delete = models.RESTRICT, related_name='device_types')
    devicedesc    = models.CharField(null = True, max_length = 50)
    ipaddress     = models.CharField(null = True , blank = True, max_length = 100)
    bu            = models.ForeignKey("onboarding.Bt", null = True,blank = True, on_delete = models.RESTRICT)

    class Meta(BaseModel.Meta):
        db_table = 'device'
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self):
        return self.devicecode

class Event(BaseModel, TenantAwareModel):
    # id           = models.BigIntegerField(_("Event Id"), primary_key = True)
    eventdesc     = models.CharField(max_length = 250, null = True, blank = True)
    device        = models.ForeignKey("activity.Device", null = True, blank = True, on_delete = models.RESTRICT, related_name='event_device')
    eventdatetime = models.DateTimeField(default = timezone.now)
    eventtype     = models.ForeignKey("onboarding.TypeAssist", null = True, blank = True, on_delete = models.RESTRICT, related_name='event_types')
    category      = models.IntegerField(null = True, blank = True)
    source        = models.CharField(max_length = 100, null = True, blank = True)
    note          = models.CharField(max_length = 100, null = True, blank = True)
    starttime     = models.DateTimeField(editable = True, null = True, blank = True)
    endtime       = models.DateTimeField(editable = True, null = True, blank = True)
    bu            = models.ForeignKey("onboarding.Bt", null = True,blank = True, on_delete = models.RESTRICT)

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
        NEW       = ('NEW', 'New')
        CANCEL    = ('CANCEL', 'Cancel')
        CLOSE     = ('CLOSE', 'Close')
        ESCALATED = ('ESCALATED', 'Escalated')
        AUTOCLOSE = ('AUTOCLOSE', 'Autoclose')
        ASSIGNED  = ('ASSIGNED', 'Assigned' )

    class TicketSource(models.TextChoices):
        SYSTEMGENERATED = ('SYSTEMGENERATED', 'New Generated')
        USERDEFINED     = ('USERDEFINED', 'User Defined')


    uuid           = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
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
    events             = models.TextField(null=True, blank=True)
    isescalated        = models.BooleanField(default=True)
    ticketsource       = models.CharField(max_length=50, choices=TicketSource.choices, null=True, blank=True)

    objects = TicketManager() 
    
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
    

    # id                = models.BigIntegerField(primary_key = True)
    body               = models.CharField(max_length = 500, null = True)
    job = models.ForeignKey("activity.Job", verbose_name=_("Job"),null=True, on_delete=models.RESTRICT)
    level              = models.IntegerField(null = True, blank = True)
    frequency          = models.CharField(max_length = 10, default='DAY', choices = Frequency.choices)
    frequencyvalue     = models.IntegerField(null = True, blank = True)
    assignedfor        = models.CharField(max_length = 50)
    assignedperson     = models.ForeignKey(settings.AUTH_USER_MODEL, null = True, blank = True, on_delete = models.RESTRICT, related_name="escalation_people")
    assignedgroup      = models.ForeignKey('peoples.Pgroup', null = True, blank = True, on_delete = models.RESTRICT, related_name="escalation_grps")
    bu                 = models.ForeignKey("onboarding.Bt", null = True,blank = True, on_delete = models.RESTRICT)
    escalationtemplate = models.CharField(max_length = 30)
    notify             = models.TextField(blank = True, null = True)
    client                 = models.ForeignKey("onboarding.Bt", null = True,blank = True, on_delete = models.RESTRICT, related_name='esc_clients')

    objects = ESCManager() 
    
    class Meta(BaseModel.Meta):
        db_table = 'escalationmatrix'
        get_latest_by = ["mdtz", 'cdtz']

class DeviceEventlog(BaseModel, models.Model):
    class DeviceEvent(models.TextChoices):
        STEPCOUNT     = ('stepcount', 'Step Count')
        LOCATIONALERT = ('locationalert', 'Location Alert')
        DEVICEOGS     = ('devicelogs', 'Device Logs')
        LOGIN         = ('login', 'Log In')
        LOGOUT        = ('logout', 'Log Out')
    
    class NetworkProviderChoices(models.TextChoices):
        BLUETOOTH = ('bluetooth', 'Bluetooth')
        WIFI      = ('wifi', 'WIFI')
        ETHERNET  = ('ethernet', 'Ethernet')
        MOB       = ('mobile', 'Mobile')
        NONE      = ('none', 'None')
        
    class LocationAllowedChoices(models.TextChoices):
        LOCATIONALWAYS = ('locationalways', 'Location Always')
        ONLYWHILEUSING = ('onlywhileyusing', 'Only While Using')
        NONE           = ('NONE', 'NONE')
        

    uuid                   = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    deviceid               = models.CharField(_("Device Id"), max_length = 55)
    eventvalue             = models.CharField(_("Device Event"), max_length = 50, choices = DeviceEvent.choices)
    locationserviceenabled = models.BooleanField(_("Is Location Serivice Enabled"),default=False)
    islocationmocked       = models.BooleanField(_("Is Location Spoofed"),default=False)
    locationpermission     = models.CharField(max_length=25, choices=LocationAllowedChoices.choices, default=LocationAllowedChoices.NONE.value)
    gpslocation            = PointField(null=True, srid=4326,geography = True)
    accuracy               = models.CharField(max_length=25, default="-")
    altitude               = models.CharField(max_length=25, default='-')
    bu                     = models.ForeignKey("onboarding.Bt", null = True,blank = True, on_delete = models.RESTRICT)
    client                 = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete= models.RESTRICT, null = True, blank = True, related_name='deviveevents_clients')
    receivedon             = models.DateTimeField(_("Received On"), auto_now = False, auto_now_add = True)
    people                 = models.ForeignKey('peoples.People', null = True, blank = True, on_delete = models.RESTRICT, related_name="deviceevent_people")
    batterylevel           = models.CharField(_("Battery Level"), max_length = 50, default = 'NA')
    signalstrength         = models.CharField(_("Signal Strength"), max_length = 50, default = 'NA')
    availintmemory         = models.CharField(_("Available Internal Memory"), max_length = 50, default = 'NA')
    availextmemory         = models.CharField(_("Available External Memory"), max_length = 50, default = 'NA')
    signalbandwidth        = models.CharField(_("Signal Bandwidth"), max_length = 50, default = 'NA')
    platformversion        = models.CharField(_("Android Version"), max_length = 50, default = 'NA')
    applicationversion     = models.CharField(_("App Version"), max_length = 50, default = 'NA')
    networkprovidername    = models.CharField(max_length=55, choices=NetworkProviderChoices.choices, default=NetworkProviderChoices.NONE.value)
    modelname              = models.CharField(_("Model Name"), max_length = 50, default = 'NA')
    installedapps          = models.CharField(_("Installed Apps"), max_length = 500, default = 'NA')
    stepcount              = models.CharField(max_length = 55, default='No Steps')

    objects = DELManager()
    class Meta(BaseModel.Meta):
        db_table = 'deviceeventlog'
        get_latest_by = ["mdtz", 'cdtz']
    
    def __str__(self) -> str:
        return f'{self.deviceid} {self.eventvalue}'



class WorkPermit(BaseModel, models.Model):
    class WorkPermitChoices(models.TextChoices):
        PENDING    = 'PENDING',  _('Pending')
        APPROVED   = 'APPROVED', _('Approved')
        REJECTED   = 'REJECTED', _('Rejected')
    
    class WorkStatusChoices(models.TextChoices):
        INCOMPLETE = 'INCOMPLETE', _('Incomplete')
        COMPLETED  = 'COMPLETED',  _('Completed')
    
    uuid       = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    wptype     = models.ForeignKey("activity.QuestionSet", verbose_name=_("WorkPermit Type"), on_delete=models.RESTRICT, null=True)
    seqno      = models.IntegerField(null=True)
    wpstatus   = models.CharField(_("Status"), max_length=30, choices=WorkPermitChoices.choices)
    workstatus = models.CharField(_("Work Status"), max_length=30, choices=WorkStatusChoices.choices)
    approvedby = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name=_(""), on_delete=models.RESTRICT, null=True, related_name='wp_approvers')
    parent     = models.ForeignKey("self", verbose_name=_(""), on_delete=models.RESTRICT, null=True)
    client     = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete=models.RESTRICT, null=True, related_name='wp_clients')
    bu         = models.ForeignKey("onboarding.Bt", verbose_name=_("Bt"), on_delete=models.RESTRICT, null=True, related_name='wp_sites')
    attcount   = models.IntegerField(_("Attachment Count"), null=True)
    
    
    objects = WorkpermitManager()
    class Meta(BaseModel.Meta):
        db_table = 'workpermit'
        get_latest_by = ["mdtz", 'cdtz']

def loc_json():
    return {
        'address':""
    }


class Location(BaseModel, TenantAwareModel):
    class LocationStatus(models.TextChoices):
        MAINTENANCE = ("MAINTENANCE", "Maintenance")
        STANDBY     = ("STANDBY", "Standby")
        WORKING     = ("WORKING", "Working")
        SCRAPPED    = ("SCRAPPED", "Scrapped")
    
    uuid        = models.UUIDField(unique = True, editable = True, blank = True, default = uuid.uuid4)
    loccode     = models.CharField(_("Asset Code"), max_length = 50, unique=True)
    locname     = models.CharField(_("Asset Name"), max_length = 250)
    enable      = models.BooleanField(_("Enable"), default = True)
    iscritical  = models.BooleanField(_("Is Critical"))
    gpslocation = PointField(_('GPS Location'), null = True, geography = True, srid = 4326, blank = True)
    parent      = models.ForeignKey("self", verbose_name = _( "Belongs to"), on_delete = models.RESTRICT, null = True, blank = True)
    locstatus   = models.CharField(_('Running Status'), choices = LocationStatus.choices, max_length = 55)
    type        = models.ForeignKey("onboarding.TypeAssist", verbose_name = _("Type"), on_delete = models.RESTRICT, null = True, blank = True, related_name='location_types')
    client      = models.ForeignKey("onboarding.Bt", verbose_name = _("Client"), on_delete = models.RESTRICT, null = True, blank = True, related_name='location_clients')
    bu          = models.ForeignKey("onboarding.Bt", verbose_name = _("Site"), on_delete = models.RESTRICT, null = True, blank = True, related_name='location_bus')
    locjson     = models.JSONField(_("Location Json"), encoder=DjangoJSONEncoder, blank=True, null=True, default=loc_json)

    objects = LocationManager()
    
    def __str__(self) -> str:
        return f'({self.loccode}) {self.locname}'
    
    class Meta(BaseModel.Meta):
        db_table = 'location'
        get_latest_by = ["mdtz", 'cdtz']