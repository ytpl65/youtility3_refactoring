from django.contrib import admin
from import_export import resources, fields
from import_export import widgets as wg
from import_export.admin import ImportExportModelAdmin
import apps.tenants.models as tm
from apps.peoples import models as pm
from .forms import (BtForm, ShiftForm, )
import apps.onboarding.models as om
from apps.core import utils

class BaseFieldSet1:
    bu = fields.Field(
        column_name='bu',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True)

    tenant = fields.Field(
        column_name='tenant',
        attribute='tenant',
        widget = wg.ForeignKeyWidget(tm.TenantAwareModel, 'tenantname'),
        saves_null_values = True
    )

class BaseFieldSet2(object):
    client = fields.Field(
        column_name='client',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    bu = fields.Field(
        column_name='bu',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default='NONE'
    )
    tenant = fields.Field(
        column_name='tenant',
        attribute='tenant',
        widget = wg.ForeignKeyWidget(tm.TenantAwareModel, 'tenantname'),
        saves_null_values = True
    )



class TaResource(resources.ModelResource ):
    client = fields.Field(
        column_name='client',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    bu = fields.Field(
        column_name='bu',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default='NONE'
    )
    tenant = fields.Field(
        column_name='tenant',
        attribute='tenant',
        widget = wg.ForeignKeyWidget(tm.TenantAwareModel, 'tenantname'),
        saves_null_values = True
    )
    tatype = fields.Field(
        column_name       = 'tatype',
        attribute         = 'tatype',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )

    class Meta:
        model = om.TypeAssist
        skip_unchanged = True
        import_id_fields = ('id', 'tacode')
        report_skipped = True
        fields = ('id', 'taname', 'tacode', 'tatype', 'tenant', 'bu', 'client')

    def __init__(self, *args, **kwargs):
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        super(TaResource, self).__init__(*args, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.tacode = instance.tacode.upper()
        utils.save_common_stuff(self.request, instance, self.is_superuser)

    def skip_row(self, instance, original):
        return True if om.TypeAssist.objects.filter(tacode = instance.tacode).exists() else False


@admin.register(om.TypeAssist)
class TaAdmin(ImportExportModelAdmin):
    resource_class = TaResource
    list_display = (
        'id', 'tacode', 'tatype', 'mdtz', 'taname',
        'cuser', 'muser', 'cdtz', 'bu', 'client' )

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}

    def get_queryset(self, request):
        return om.TypeAssist.objects.select_related(
            'tatype', 'cuser', 'muser', 'bu', 'client', 'tenant').all()

class BtResource(resources.ModelResource, BaseFieldSet1):
    bu = None
    parent = fields.Field(
        column_name='parent',
        attribute='parent',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'))

    butype = fields.Field(
        column_name='butype',
        attribute='butype',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))

    tenant = fields.Field(
        column_name='tenant',
        attribute='tenant',
        widget = wg.ForeignKeyWidget(tm.Tenant, 'tenantname'))

    identifier = fields.Field(
        column_name='identifier',
        attribute='identifier',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))

    class Meta:
        model = om.Bt
        skip_unchanged = True
        import_id_fields = ('id', 'bucode')
        report_skipped = True
        fields = (
            'id', 'buname', 'bucode', 'butype__tacode',
            'identifier__tacode', 'parent__bucode', 'tenant__tenantname',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(BtResource, self).__init__(*args, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.bucode = instance.bucode.upper()
        utils.save_common_stuff(self.request, instance)

    def get_queryset(self):
        return om.Bt.objects.select_related(
            'identifier', 'parent', 'butype',
            'tenant', 
        ).all()

@admin.register(om.Bt)
class BtAdmin(ImportExportModelAdmin):
    resource_class = BtResource
    fields = ('bucode',  'buname', 'butype', 'parent', 'gpslocation', 'identifier',
              'iswarehouse', 'enable', 'bupreferences')
    exclude = ['bupath']
    list_display = ('bucode', 'id', 'buname', 'butype',
                    'identifier', 'parent', 'butree')
    list_display_links = ('bucode',)
    form = BtForm

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}

    def get_queryset(self, request):
        return om.Bt.objects.select_related('butype', 'identifier', 'parent').all()

class ShiftResource(resources.ModelResource, BaseFieldSet1):

    class Meta:
        model = om.Shift
        skip_unchanged = True
        import_id_fields = ('id',)
        report_skipped = True
        fields = ('id', 'shiftname', 'shiftduration', 'starttime', 'cuser'
                  'endtime', 'nightshiftappicable', 'enable', 'muser', 'bu')

@admin.register(om.Shift)
class ShiftAdmin(ImportExportModelAdmin):
    resource_class = ShiftResource
    form = ShiftForm
    fields = ('bu', 'shiftname', 'shiftduration', 'starttime',
              'endtime', 'nightshiftappicable', 'captchafreq')
    list_display = ('bu', 'shiftname', 'shiftduration',
                    'starttime', 'endtime', 'nightshiftappicable')
    list_display_links = ('shiftname',)

class SitePeopleResource(resources.ModelResource, BaseFieldSet1):

    people = fields.Field(
        column_name='people',
        attribute='people',
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode')
    )
    reportto = fields.Field(
        column_name='reportto',
        attribute='reportto',
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode'))

    shift = fields.Field(
        column_name='shift',
        attribute='shift',
        widget = wg.ForeignKeyWidget(om.Shift, 'shiftname'))
    worktype = fields.Field(
        column_name='worktype',
        attribute='worktype',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode')
    )
    contract = fields.Field(
        column_name='contract',
        attribute='contract',
        widget = wg.ForeignKeyWidget(om.Contract, 'contractname'))

    contractdetail = fields.Field(
        column_name='contractdetail',
        attribute='contractdetail',
        widget = wg.ForeignKeyWidget(om.ContractDetail, 'pk'))

    class Meta:
        model = om.SitePeople
        skip_unchanged = True
        import_id_fields = ('id',)
        report_skipped = True
        fields = ('id', 'fromdt', 'uptodt', 'siteowner', 'seqno', 'reportcapability',
                  'posting_revision', 'nightshiftappicable', 'webcapability',
                  'reportcapability', 'mobilecapability', 'enable', ' emergencycontact',
                  'ackdate', 'isreliver', 'checkpost', 'enablesleepingguard')
