from django.conf import settings
from django.urls import reverse
from django.contrib.auth import default_app_config
from django.db.models import constraints
from apps.tenants.models import TenantAwareModel
from django.db import models
from .managers import BtManager
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _
from apps.peoples.models import BaseModel
# Create your models here.


class HeirarchyModel(models.Model):
    class Meta:
        abstract = True

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
            raise ValidationError("A user cannot have itself \
                    or one of its' children as parent.")


def bu_defaults():
    return {
        "mobilecapability": [],
        "validimei": "",
        "webcapability": [],
        "portletcapability": [],
        "validip": "",
        "reliveronpeoplecount": 0,
        "reportcapability": [],
        "usereliver": False,
        "pvideolength": 10,
        "guardstrenth": 0,
        "malestrength": 0,
        "femalestrength": 0,
        "siteclosetime": "",
        "tag": "",
        "siteopentime": "",
        "nearbyemergencycontacts": "",
    }


class Bt(BaseModel, TenantAwareModel, HeirarchyModel):
    
    
    bucode              = models.CharField(_('Code'), max_length=15)
    bu_preferences      = models.JSONField(_('bu_preferences'), null=True, default=bu_defaults,  encoder=DjangoJSONEncoder, blank=True)
    identifier          = models.ForeignKey('TypeAssist', null=True, blank=True, on_delete=models.RESTRICT, related_name="bu_idfs", verbose_name='Identifier')
    buname              = models.CharField(_('Name'), max_length=200)
    butree              = models.CharField(_('Bu Path'), null=True, blank=True, max_length=300)
    butype              = models.ForeignKey('TypeAssist', on_delete=models.RESTRICT,  null=True, blank=True,  related_name="bu_butypes", verbose_name="Type")
    parent              = models.ForeignKey('self', null=True, blank=True, on_delete=models.RESTRICT, related_name="children", verbose_name="Belongs To")
    enable              = models.BooleanField(_("Enable"), default=True)
    iswarehouse         = models.BooleanField(_("Is Warehouse"), default=False)
    gpsenable           = models.BooleanField(_("GPS Enable"), default=False)
    enablesleepingguard = models.BooleanField(_("Enable SleepingGuard"), default=False)
    skipsiteaudit       = models.BooleanField(_("Skip SiteAudit"), default=False)
    siincludes          = models.TextField(_("Site Inclides"), default="")
    deviceevent         = models.BooleanField(_("Device Event"), default=False)
    pdist               = models.FloatField(_("pdist"), default=0.0, blank=True, null=True)
    gpslocation         = models.CharField(_("GPS Location"), max_length=50, blank=True, default="0.0,0.0", null=True)
    isvendor            = models.BooleanField(_("Is Vendor"), default=False)
    is_serviceprovider  = models.BooleanField(_("Is ServiceProvider"), default=False)

    objects = BtManager()

    class Meta(BaseModel.Meta):
        db_table = 'bt'
        verbose_name = 'Buisiness Unit'
        verbose_name_plural = 'Buisiness Units'
        constraints = [models.UniqueConstraint(
            fields=['bucode', 'parent', 'identifier'],
            name='bu_bucode_parent_identifier_uk')]
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self) -> str:
        return f'{self.buname} ({self.bucode})'

    def get_absolute_wizard_url(self):
        return reverse("onboarding:wiz_bu_update", kwargs={"pk": self.pk})


class Contract(BaseModel, TenantAwareModel):
    bu               = models.ForeignKey('Bt', null=True, on_delete=models.RESTRICT,  related_name='contract_bu', verbose_name='Site')
    customer         = models.ForeignKey('Bt', null=True, on_delete=models.RESTRICT, related_name='contract_customer', verbose_name='Customer')
    contractname       = models.CharField(max_length=50)
    contract_startdate = models.DateField(null=True)
    contract_enddate   = models.DateField(null=True)
    enable             = models.BooleanField(default=True)
    isaddposting       = models.BooleanField(default=False)
    revno              = models.IntegerField()
    remarks            = models.CharField(null=True, max_length=50)

    class Meta(BaseModel.Meta):
        db_table = 'contract'
        constraints = [
            models.UniqueConstraint(
                fields=['contractname', 'revno', 'bu'],
                name='cname_revno_bu_uk'),
            models.CheckConstraint(
                check=models.Q(revno__gte=0),
                name='revno_gte_0_ck')]
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self):
        return self.contractname


class ContractDetail(BaseModel, TenantAwareModel):
    contract  = models.ForeignKey('Contract', null=True, on_delete=models.RESTRICT, related_name="cd_contract", verbose_name='Contract')
    worktype    = models.ForeignKey('TypeAssist', null=True, on_delete=models.RESTRICT, related_name="cd_worktype", verbose_name='Work Type')
    quantity    = models.IntegerField()
    cdstartdate = models.DateTimeField(null=True)
    cdenddate   = models.DateField(null=True)

    class Meta(BaseModel.Meta):
        db_table = 'contractdetails'
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name='qty_gte_0_ck')]

    def __str__(self):
        return self.contract.contractname


class Shift(BaseModel, TenantAwareModel):
    bu                   = models.ForeignKey('Bt', null=True, on_delete=models.RESTRICT,related_name="shift_bu", verbose_name='Site')
    shiftname            = models.CharField(max_length=50, verbose_name="Name")
    shiftduration        = models.IntegerField(null=True, verbose_name="Shift Duration")
    starttime            = models.TimeField(verbose_name="Start time")
    endtime              = models.TimeField(verbose_name='End time')
    nightshift_appicable = models.BooleanField(default=True, verbose_name="Night Shift Applicable")
    captchafreq          = models.IntegerField(default=10, null=True)
    enable               = models.BooleanField(verbose_name='Enable', default=True)

    class Meta(BaseModel.Meta):
        db_table = 'shift'
        constraints = [models.UniqueConstraint(
            fields=['shiftname', 'bu'], name='shiftname_bu_uk')]
        get_latest_by = ['mdtz', 'cdtz']

    def __str__(self):
        return f'{self.shiftname} ({self.starttime} - {self.endtime})'

    def get_absolute_wizard_url(self):
        return reverse("onboarding:wiz_shift_update", kwargs={"pk": self.pk})


class SitePeople(BaseModel, TenantAwareModel):
    bu                  = models.ForeignKey('Bt', null=True, on_delete=models.RESTRICT, related_name="sp_bu")
    people              = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.RESTRICT,  related_name="sp_people")
    reportto            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,on_delete=models.RESTRICT,  related_name="sp_reportto")
    shift               = models.ForeignKey('Shift', null=True, on_delete=models.RESTRICT, related_name="sp_shift")
    worktype            = models.ForeignKey('TypeAssist', null=True, on_delete=models.RESTRICT,  related_name="sp_worktype")
    contract            = models.ForeignKey('Contract', null=True, on_delete=models.RESTRICT, related_name="sp_contract")
    contractdetail      = models.ForeignKey('ContractDetail', null=True, on_delete=models.RESTRICT, related_name="sp_contractdetail")
    fromdt              = models.DateField()
    uptodt              = models.DateField()
    siteowner           = models.BooleanField(default=False)
    slno                = models.IntegerField(default=1)
    posting_revision    = models.IntegerField(default=1)
    webcapability       = models.CharField(null=True, max_length=1000)
    mobilecapability    = models.CharField(null=True, max_length=1000)
    reportcapability    = models.CharField(null=True, max_length=1000)
    enable              = models.BooleanField(default=True)
    emergencycontact    = models.BooleanField(null=True, default=False)
    ackdate             = models.DateTimeField(null=True, auto_now_add=True)
    isreliver           = models.BooleanField(null=True, default=False)
    checkpost           = models.BigIntegerField(null=True)
    enablesleepingguard = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        db_table = 'sitepeople'
        constraints = [
            models.UniqueConstraint(fields=['people', 'bu', 'posting_revision', 'contract', 'slno'],
                                    name='people_bu_postrev_contr_slno_uk')]
        get_latest_by = ["mdtz", 'cdtz']

    def __str__(self):
        return self.people.peoplecode


class TypeAssist(BaseModel, TenantAwareModel):
    tacode = models.CharField(_("tacode"), max_length=50, unique=True)
    taname = models.CharField(_("taname"), max_length=100)
    tatype = models.ForeignKey( "self", null=True, blank=True, on_delete=models.RESTRICT, related_name='children')
    bu   = models.ForeignKey("Bt", null=True, blank=True, on_delete=models.RESTRICT, related_name='ta_bus')

    class Meta(BaseModel.Meta):
        db_table = 'typeassist'

    def __str__(self):
        return f'{self.taname} ({self.tacode})'

    def get_absolute_url(self):
        return reverse("onboarding:ta_update", kwargs={"pk": self.pk})

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
        if self.tatype is not None:
            parent = self.tatype
            parents.extend(parent.get_all_parents())
        return parents

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.tatype in self.get_all_children():
            raise ValidationError("A user cannot have itself \
                    or one of its' children as parent.")


def wizard_default():
    return {'wizard_data': {}}


def formData_default():
    return {'form_id': {}}


class WizardDraft(models.Model):
    createdby   = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="created_by")
    cdtz        = models.DateTimeField(auto_now_add=True, auto_now=False)
    mdtz        = models.DateTimeField(auto_now=True)
    bu          = models.ForeignKey("Bt", null=True, blank=True,on_delete=models.CASCADE, related_name='wiz_bus')
    wizard_data = models.JSONField(null=True, default=wizard_default,  encoder=DjangoJSONEncoder, blank=True)
    form_data   = models.JSONField( null=True, default=formData_default,  encoder=DjangoJSONEncoder, blank=True)

    class Meta:
        db_table = 'wizard_draft'
        constraints = [
            models.UniqueConstraint(
                fields=['createdby', 'id'], name="draft_per_user")
        ]
        get_latest_by = ['mdtz']

    def __str__(self):
        return f"{self.id}--{self.createdby.peoplecode}"


class GeofenceMaster(BaseModel):
    gfcode        = models.CharField(_("Code"), max_length=100)
    gfname        = models.CharField(_("Name"), max_length=100)
    alerttext     = models.CharField(_("Alert Text"), max_length=100)
    geofence      = models.TextField(_("GeoFence"))
    alerttogroup  = models.ForeignKey("peoples.Pgroup", verbose_name=_( "Alert to Group"), on_delete=models.RESTRICT)
    alerttopeople = models.ForeignKey("peoples.People", verbose_name=_(""), on_delete=models.RESTRICT)
    client        = models.ForeignKey("onboarding.Bt", verbose_name=_("Client"), on_delete=models.RESTRICT, related_name="for_clients")
    bu            = models.ForeignKey("onboarding.Bt", verbose_name=_( "Site"), on_delete=models.RESTRICT, related_name='for_sites')
    enable        = models.BooleanField(_("Enable"), default=True)

    class Meta(BaseModel.Meta):
        db_table = 'geofencemaster'
        constraints = [
            models.UniqueConstraint(
                fields=['gfcode', 'bu'], name='gfcode_bu_uk')
        ]
        get_latest_by = ['mdtz']

    def __str__(self):
        return f'{self.gfname} ({self.gfname})'
