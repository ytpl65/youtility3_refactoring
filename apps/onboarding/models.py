from apps.tenants.models import TenantAwareModel
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.translation import ugettext_lazy as _
from apps.peoples.models import BaseModel

# Create your models here.
def bu_defaults():
    j = {"isvendor": False,         "bupath":"",                   "mobilecapability":[],
        "validimei": "",            "webcapability":[],            "portletcapability":[],   
        "validip": "",              "reliveronpeoplecount": 0,     "reportcapability":[], 
        "usereliver": False,        "pvideolength": 10,            "isserviceprovider": False,
        "malestrength":0,           "femalestrength":0,            "guardstrenth":0,
        "tag":"",                   "siteopentime":"",             "siteclosetime":"",
        "nearbyemergencycontacts":""}
    return j


class Bt(BaseModel, TenantAwareModel):
    btid                = models.BigIntegerField(_('btid'), primary_key=True)
    bucode              = models.CharField(_('bucode'), max_length=15)
    bu_preferences      = models.JSONField(_('bu_preferences'), null=False, default=bu_defaults,  encoder=DjangoJSONEncoder, blank=True)
    identifier          = models.ForeignKey('TypeAssist', null = True, blank=True, on_delete = models.RESTRICT, db_column="identifier", related_name="bu_idfs")
    buname              = models.CharField(_('buname'), max_length=200)
    butype              = models.ForeignKey('TypeAssist', on_delete = models.RESTRICT, null = True, blank=True,  db_column="butype", related_name="bu_butypes")
    parent              = models.ForeignKey('self', null=True, blank=True, on_delete=models.RESTRICT, db_column="parent", related_name="bu_parent")
    enable              = models.BooleanField(_("enable"), default=True)
    iswarehouse         = models.BooleanField(_("iswarehouse"), default=False)
    gpsenable           = models.BooleanField(_("gpsenable"), default=False)
    enablesleepingguard = models.BooleanField(_("enablesleepingguard"), default=False)
    skipsiteaudit       = models.BooleanField(_("skipsiteaudit"), default=False)
    siincludes          = models.TextField(_("siincludes"), default="")
    deviceevent         = models.BooleanField(_("deviceevent"), default=False)
    pdist               = models.FloatField(_("pdist"), default=0.0, blank=True, null=True)
    gpslocation         = models.CharField(_("gpslocation"), max_length=50)



    class Meta(BaseModel.Meta):
        db_table = 'bt'
        verbose_name = 'Buisiness Unit'
        verbose_name_plural = 'Buisiness Units'
        constraints = [
        models.UniqueConstraint(fields=['bucode', 'parent', 'identifier'], name='bu_bucode_parent_identifier_uk')]
        get_latest_by       = ["mdtz", 'cdtz']

    def __str__(self) -> str:
        return self.bucode
    


class TypeAssist(BaseModel, TenantAwareModel):
    tacode = models.CharField(_("tacode"), max_length=50, primary_key=True)
    taname = models.CharField(_("taname"), max_length=100)
    tatype = models.CharField(_("tatype"), max_length=100)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.RESTRICT, related_name='ta_parents')
    buid   = models.ForeignKey("Bt", null=True, blank=True, on_delete=models.RESTRICT, related_name='ta_buids')

    class Meta(BaseModel.Meta):
        db_table = 'typeassist'
        constraints = [
            models.UniqueConstraint(fields=['tacode'], name='ta_tacode_uk')
        ]

    def __str__(self):
        return self.tacode
