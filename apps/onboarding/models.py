from django.conf import settings
from django.contrib.auth import default_app_config
from django.db.models import constraints
from apps.tenants.models import TenantAwareModel
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import gettext_lazy as _
from apps.peoples.models import BaseModel
# Create your models here.
class HeirarchyModel(models.Model):
    class Meta:
        abstract=True
    
    
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
    bucode              = models.CharField(_('bucode'), max_length=15)
    bu_preferences      = models.JSONField(_('bu_preferences'), null=False, default=bu_defaults,  encoder=DjangoJSONEncoder, blank=True)
    identifier          = models.ForeignKey('TypeAssist', null = True, blank=True, on_delete = models.RESTRICT, db_column="identifier", related_name="bu_idfs")
    buname              = models.CharField(_('buname'), max_length=200)
    butree              = models.CharField(_('bupath'), null=True, blank=True, max_length=300)
    butype              = models.ForeignKey('TypeAssist', on_delete = models.RESTRICT, null = True, blank=True,  db_column="butype", related_name="bu_butypes")
    parent              = models.ForeignKey('self', null=True, blank=True, on_delete=models.RESTRICT, db_column="parent", related_name="children")
    enable              = models.BooleanField(_("enable"), default=True)
    iswarehouse         = models.BooleanField(_("iswarehouse"), default=False)
    gpsenable           = models.BooleanField(_("gpsenable"), default=False)
    enablesleepingguard = models.BooleanField(_("enablesleepingguard"), default=False)
    skipsiteaudit       = models.BooleanField(_("skipsiteaudit"), default=False)
    siincludes          = models.TextField(_("siincludes"), default="")
    deviceevent         = models.BooleanField(_("deviceevent"), default=False)
    pdist               = models.FloatField(_("pdist"), default=0.0, blank=True, null=True)
    gpslocation         = models.CharField(_("gpslocation"), max_length=50, blank=True, default="0.0,0.0", null=True)
    isvendor            = models.BooleanField(_("isvendor"), default=False)
    is_serviceprovider  = models.BooleanField(_("is_serviceprovider"), default=False)



    class Meta(BaseModel.Meta):
        db_table            = 'bt'
        verbose_name        = 'Buisiness Unit'
        verbose_name_plural = 'Buisiness Units'
        constraints         = [models.UniqueConstraint(fields=['bucode', 'parent', 'identifier'], 
                                name='bu_bucode_parent_identifier_uk')]
        get_latest_by       = ["mdtz", 'cdtz']

    
    def __str__(self) -> str:
        return self.bucode



class Contract(BaseModel, TenantAwareModel):
    buid               = models.ForeignKey('Bt', null=True, on_delete=models.RESTRICT,db_column="buid", related_name='contract_buid')
    customerid         = models.ForeignKey('Bt', null=True, on_delete=models.RESTRICT, db_column="customerid", related_name='contract_customer')
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
            models.UniqueConstraint(fields=['contractname', 'revno', 'buid'],
                                    name='cname_revno_buid_uk'),
            models.CheckConstraint(check=models.Q(revno__gte=0),
                                    name='revno_gte_0_ck')]
        get_latest_by  = ["mdtz", 'cdtz']

    def __str__(self):
        return self.contractname



class ContractDetail(BaseModel, TenantAwareModel):
    contractid       = models.ForeignKey('Contract', null=True, on_delete=models.RESTRICT, db_column='contractid', related_name="cd_contract")
    worktype         = models.ForeignKey('TypeAssist', null=True, on_delete=models.RESTRICT, db_column='worktype', related_name="cd_worktype")
    quantity         = models.IntegerField()
    cdstartdate      = models.DateTimeField(null=True)
    cdenddate        = models.DateField(null=True)

    class Meta(BaseModel.Meta):
        db_table = 'contractdetails'
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gte=0),
                                    name='qty_gte_0_ck')]
            
    def __str__(self):
        return self.contractid.contractname



class Shift(BaseModel, TenantAwareModel):
    buid                 = models.ForeignKey('Bt', null=True, on_delete=models.RESTRICT, db_column="buid", related_name="shift_buid")
    shiftname            = models.CharField(max_length=50)
    shiftduration        = models.IntegerField(null=True)
    starttime            = models.TimeField()
    endtime              = models.TimeField()
    nightshift_appicable = models.BooleanField(default=True)
    captchafreq          = models.IntegerField(default=10)

    class Meta(BaseModel.Meta):
        db_table = 'shift'
        constraints = [models.UniqueConstraint(fields=['shiftname', 'buid'], name='shiftname_buid_uk')]
        get_latest_by = ['mdtz', 'cdtz']

    def __str__(self):
        return self.shiftname



class SitePeople(BaseModel, TenantAwareModel):
    buid                = models.ForeignKey('Bt', null=True, on_delete=models.RESTRICT, db_column="buid", related_name="sp_buid")
    peopleid            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.RESTRICT, db_column="peopleid", related_name="sp_people")
    reportto            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.RESTRICT, db_column="reportto", related_name="sp_reportto")
    shift               = models.ForeignKey('Shift', null=True, on_delete=models.RESTRICT, db_column="shift", related_name="sp_shift")
    worktype            = models.ForeignKey('TypeAssist', null=True, on_delete=models.RESTRICT, db_column="worktype", related_name="sp_worktype")
    contract_id         = models.ForeignKey('Contract', null=True, on_delete=models.RESTRICT, db_column="contract", related_name="sp_contractid")
    contractdetailid    = models.ForeignKey('ContractDetail', null=True, on_delete=models.RESTRICT, db_column="contractdetailid", related_name="sp_contractdetail")
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
            models.UniqueConstraint(fields=['peopleid', 'buid', 'posting_revision', 'contract_id', 'slno'],
                                    name='people_buid_postrev_contr_slno_uk')]
        get_latest_by       = ["mdtz", 'cdtz']

    def __str__(self):
        return self.peopleid.peoplecode


class TypeAssist(BaseModel, TenantAwareModel, HeirarchyModel):
    tacode = models.CharField(_("tacode"), max_length=50, unique=True)
    taname = models.CharField(_("taname"), max_length=100)
    tatype = models.CharField(_("tatype"), max_length=100)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.RESTRICT, related_name='children')
    buid   = models.ForeignKey("Bt", null=True, blank=True, on_delete=models.RESTRICT, related_name='ta_buids')

    class Meta(BaseModel.Meta):
        db_table = 'typeassist'


    def __str__(self):
        return self.tacode

def wizard_default():
    return {'wizard_data':{}}


def formData_default():
    return {'form_id':{}}


class WizardDraft(models.Model):
    createdby = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="created_by")
    cdtz = models.DateTimeField( auto_now_add = True, auto_now=False)
    mdtz = models.DateTimeField(auto_now=True)
    buid = models.ForeignKey("Bt", null=True, blank=True, on_delete=models.CASCADE, related_name='wiz_buids')
    wizard_data = models.JSONField(null=True, default=wizard_default,  encoder=DjangoJSONEncoder, blank=True)
    form_data = models.JSONField(null=True, default=formData_default,  encoder=DjangoJSONEncoder, blank=True)

    class Meta:
        db_table = 'wizard_draft'
        constraints = [
            models.UniqueConstraint(fields=['createdby', 'id'], name="draft_per_user")
        ]
        get_latest_by = ['mdtz']

    def __str__(self):
        return f"{self.id}--{self.createdby.peoplecode}"