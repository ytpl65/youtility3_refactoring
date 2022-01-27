from django.contrib import admin
from import_export import resources, fields
from import_export import widgets as wg
from import_export.admin import ImportExportModelAdmin

from apps.peoples import models as pm
from .forms import (BtForm, ShiftForm, TypeAssistForm, BuPrefForm, SitePeopleForm,
                    ContractDetailForm, ContractForm)
import apps.onboarding.models as om


class BaseFieldSet1():
    cuser = fields.Field(
        column_name='cuser',
        attribute='cuser',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'),
        saves_null_values=True)

    muser = fields.Field(
        column_name='muser',
        attribute='muser',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'),
        saves_null_values=True)

    buid = fields.Field(
        column_name='buid',
        attribute='buid',
        widget=wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values=True)


class BaseFieldSet2():
    cuser = fields.Field(
        column_name='cuser',
        attribute='cuser',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'),
        saves_null_values=True)

    muser = fields.Field(
        column_name='muser',
        attribute='muser',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'),
        saves_null_values=True)

    clientid = fields.Field(
        column_name='clientid',
        attribute='clientid',
        widget=wg.ForeignKeyWidget(om.Bt, 'bucode')
    )
    buid = fields.Field(
        column_name='buid',
        attribute='buid',
        widget=wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values=True
    )


class TaResource(resources.ModelResource, BaseFieldSet1):

    parent = fields.Field(
        column_name='parent',
        attribute='parent',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values=True
    )

    class Meta:
        model = om.TypeAssist
        skip_unchanged = True
        import_id_fields = ('id',)
        report_skipped = True
        clean_model_instances = True
        fields = ('id', 'taname', 'tacode', 'tatype', 'cuser', 'muser')

    def before_save_instance(self, instance, using_transactions, dry_run):
        super().before_save_instance(instance, using_transactions, dry_run)
        instance.tacode = instance.tacode.upper()


class TaAdmin(ImportExportModelAdmin):
    resource_class = TaResource
    list_display = ('id', 'tacode', 'tatype', 'cdtz', 'mdtz', 'cuser', 'muser')


admin.site.register(om.TypeAssist, TaAdmin)


class BtResource(resources.ModelResource, BaseFieldSet1):
    buid = None
    parent = fields.Field(
        column_name='parent',
        attribute='parent',
        widget=wg.ForeignKeyWidget(om.Bt, 'bucode'))

    butype = fields.Field(
        column_name='butype',
        attribute='butype',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))

    identifier = fields.Field(
        column_name='identifier',
        attribute='identifier',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))

    class Meta:
        model = om.Bt
        skip_unchanged = True
        import_id_fields = ('id',)
        report_skipped = True
        fields = ('id', 'buname', 'bucode', 'butype',
                  'identifier', 'parent', 'cuser', 'muser',)


@admin.register(om.Bt)
class BtAdmin(ImportExportModelAdmin):
    resource_class = BtResource
    form = BtForm
    fields = ('bucode',  'buname', 'butype', 'parent', 'gpslocation', 'identifier',
              'iswarehouse', 'enable', 'bu_preferences')
    exclude = ['bupath']
    list_display = ('bucode', 'id', 'buname', 'butype',
                    'identifier', 'parent', 'butree')
    list_display_links = ('bucode',)


class ShiftResource(resources.ModelResource, BaseFieldSet1):

    class Meta:
        model = om.Shift
        skip_unchanged = True
        import_id_fields = ('id',)
        report_skipped = True
        fields = ('id', 'shiftname', 'shiftduration', 'starttime', 'cuser'
                  'endtime', 'nightshift_appicable', 'enable', 'muser', 'buid')


@admin.register(om.Shift)
class ShiftAdmin(ImportExportModelAdmin):
    resource_class = ShiftResource
    form = ShiftForm
    fields = ('buid', 'shiftname', 'shiftduration', 'starttime',
              'endtime', 'nightshift_appicable', 'captchafreq')
    list_display = ('buid', 'shiftname', 'shiftduration',
                    'starttime', 'endtime', 'nightshift_appicable')
    list_display_links = ('shiftname',)


class SitePeopleResource(resources.ModelResource, BaseFieldSet1):

    peopleid = fields.Field(
        column_name='peopleid',
        attribute='peopleid',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode')
    )
    reportto = fields.Field(
        column_name='reportto',
        attribute='reportto',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'))

    shift = fields.Field(
        column_name='shift',
        attribute='shift',
        widget=wg.ForeignKeyWidget(om.Shift, 'shiftname'))
    worktype = fields.Field(
        column_name='worktype',
        attribute='worktype',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode')
    )
    contract_id = fields.Field(
        column_name='contract_id',
        attribute='contract_id',
        widget=wg.ForeignKeyWidget(om.Contract, 'contractname'))

    contractdetailid = fields.Field(
        column_name='contractdetailid',
        attribute='contractdetailid',
        widget=wg.ForeignKeyWidget(om.ContractDetail, 'pk'))

    class Meta:
        model = om.SitePeople
        skip_unchanged = True
        import_id_fields = ('id',)
        report_skipped = True
        fields = ('id', 'fromdt', 'uptodt', 'siteowner', 'slno', 'reportcapability',
                  'posting_revision', 'nightshift_appicable', 'webcapability',
                  'reportcapability', 'mobilecapability', 'enable', ' emergencycontact',
                  'ackdate', 'isreliver', 'checkpost', 'enablesleepingguard')
