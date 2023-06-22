from gettext import install
from django.contrib import admin
from import_export import resources, fields
from import_export import widgets as wg
from import_export.admin import ImportExportModelAdmin
import apps.tenants.models as tm
from apps.service.validators import clean_point_field, clean_string
from apps.peoples import models as pm
from .forms import (BtForm, ShiftForm, )
import apps.onboarding.models as om
from apps.core import utils

class BaseResource(resources.ModelResource):
    CLIENT = fields.Field(
        column_name='Client*',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    BV = fields.Field(
        column_name='BV*',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default='NONE'
    )
    

    
    def __init__(self, *args, **kwargs):
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
    def before_save_instance(self, instance, using_transactions, dry_run):
        utils.save_common_stuff(self.request, instance, self.is_superuser)
        super().before_save_instance(instance, using_transactions, dry_run)

    


class BaseFieldSet2:
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


class TaResource(BaseResource):
    
    TYPE = fields.Field(
        column_name       = 'Type*',
        attribute         = 'tatype',
        default           = om.TypeAssist, 
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )
    CODE = fields.Field(attribute='tacode', column_name='Code*')
    NAME = fields.Field(attribute='taname', column_name='Name*')
    ID   = fields.Field(attribute='id', column_name='ID')

    class Meta:
        model = om.TypeAssist
        skip_unchanged = True
        import_id_fields = ('CLIENT', 'CODE', 'ID') 
        report_skipped = True
        fields = ('NAME', 'CODE', 'TYPE',  'BV', 'CLIENT')


    def before_import_row(self, row, row_number, **kwargs):
        row['Code*'] = clean_string(row.get('Code*', 'NONE'), code=True)
        row['Name*'] = clean_string(row.get('Name*', "NONE"))
        return super().before_import_row(row, row_number=row_number, **kwargs)

    def before_save_instance(self, instance, using_transactions, d7ry_run=False):
        utils.save_common_stuff(self.request, instance)
        
    def skip_row(self, instance, original, row, import_validation_errors=None):
        ic("running")
        ic(row['Code*'])
        super().skip_row(instance, original, row, import_validation_errors=None)
        return row['Code*'] in [None, ""]
        


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

class BtResource(BaseResource):
    CLIENT = BV = None
    BelongsTo = fields.Field(
        column_name='Belongs To',
        default=utils.get_or_create_none_bv,
        attribute='parent',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'))

    BuType = fields.Field(
        column_name='Site Type',
        default=utils.get_or_create_none_typeassist,
        attribute='butype',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))

    tenant = fields.Field(
        column_name='Tenant',
        default=utils.get_or_create_none_tenant,
        attribute='tenant',
        widget = wg.ForeignKeyWidget(tm.Tenant, 'tenantname'))

    Identifier = fields.Field(
        column_name='Type',
        attribute='identifier',
        default=utils.get_or_create_none_typeassist(),
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))
    
    ID   = fields.Field(attribute='id', column_name="ID")
    Code = fields.Field(attribute='bucode', column_name='Code*')
    Name = fields.Field(attribute='buname', column_name='Name')
    GPS = fields.Field(attribute='gpslocation', column_name='GPS Location', saves_null_values=True)
    SOLID = fields.Field(attribute='solid', column_name='Sol Id')
    Enable = fields.Field(attribute='enable', column_name='Enable', default=True)

    class Meta:
        model = om.Bt
        start_row=6
        skip_unchanged = True
        import_id_fields = ('ID', 'Code')
        report_skipped = True
        fields = (
            'ID', 'Name', 'Code', 'BuType', 'SOLID', 
            'Enable', 'GPS',
            'Identifier', 'BelongsTo', 'tenant',)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(BtResource, self).__init__(*args, **kwargs)
    
    def before_import_row(self, row, **kwargs):
        ic(row)
        # self._gpslocation = clean_point_field(row['GPS Location'])
        # self._solid = clean_point_field(row['Sol Id'])

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.bucode = instance.bucode.upper()
        instance.gpslocation = self._gpslocation
        instance.solid = int(self._solid)
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

class ShiftResource(resources.ModelResource):
    Client = fields.Field(
        column_name='Client',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    BV = fields.Field(
        column_name='BV',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default='NONE'
    )
    
    Name          = fields.Field(attribute='shiftname', column_name='Shift Name')
    ID            = fields.Field(attribute='id')
    StartTime     = fields.Field(attribute='starttime', column_name='Start Time', widget=wg.TimeWidget())
    EndTime       = fields.Field(attribute='endtime', column_name='End Time', widget=wg.TimeWidget())
    ShiftDuration = fields.Field(attribute='shiftduration', column_name='Shift Duration', widget=wg.TimeWidget())
    IsNightShift  = fields.Field(attribute='nightshiftappicable', column_name="Is Night Shift", widget=wg.BooleanWidget())
    Enable        = fields.Field(attribute='enable', widget=wg.BooleanWidget())
    
    class Meta:
        model = om.Shift
        skip_unchanged = True
        import_id_fields = ('ID',)
        report_skipped = True
        fields = ('ID', 'Name', 'ShiftDuration', 'StartTime', 'Client',
                  'EndTime', 'IsNightShift', 'Enable', 'BV')

@admin.register(om.Shift)
class ShiftAdmin(ImportExportModelAdmin):
    resource_class = ShiftResource
    form = ShiftForm
    fields = ('bu', 'shiftname', 'shiftduration', 'starttime',
              'endtime', 'nightshiftappicable', 'captchafreq')
    list_display = ('bu', 'shiftname', 'shiftduration',
                    'starttime', 'endtime', 'nightshiftappicable')
    list_display_links = ('shiftname',)

class SitePeopleResource(resources.ModelResource, BaseFieldSet2):

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
