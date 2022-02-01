import logging
log = logging.getLogger('__main__')
from multiprocessing.spawn import import_main_path
from django.contrib import admin
from .models import People,  Pgroup, Pgbelonging, Capability
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export import widgets as wg
from apps.peoples import models as pm
from apps.onboarding import models as om
from apps.onboarding.admin import BaseFieldSet1, BaseFieldSet2
import apps.peoples.utils as putils


def save_people_passwd(user):
    log.info('Password is created by system... DONE')
    paswd = user.loginid + '@' + 'youtility'
    user.set_password(paswd)



# Register your models here.
class PeopleResource(resources.ModelResource, BaseFieldSet2):
    shift = fields.Field(
        column_name='shift',
        attribute='shift',
        widget=wg.ForeignKeyWidget(om.Shift, 'shiftname')
    )
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode')
    )
    designation = fields.Field(
        column_name='designation',
        attribute='designation',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode')
    )
    peopletype = fields.Field(
        column_name='peopletype',
        attribute='peopletype',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode')
    )
    reportto = fields.Field(
        column_name='reportto',
        attribute='reportto',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode')
    )
    dateofbirth = fields.Field(
        column_name='dateofbirth',
        attribute='dateofbirth',
        widget=wg.DateWidget(format='%d-%b-%Y')
    )

    class Meta:
        model = pm.People
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('id',)
        fields = ['id', 'peoplecode', 'peoplename', 'loginid', 'designation', 'department', 'mobno', 'email',
                  'buid', 'dateofjoin', 'dateofreport', 'dateofbirth', 'gender', 'peopletype', 'enable',
                  'isadmin', 'buid', 'shift', 'clientid']

    def before_save_instance(self, instance, using_transactions, dry_run):
        super().before_save_instance(instance, using_transactions, dry_run)
        instance.peoplecode = instance.peoplecode.upper()
        save_people_passwd(instance)


@admin.register(People)
class PeopleAdmin(ImportExportModelAdmin):
    resource_class = PeopleResource
    fields = ['peoplecode', 'peoplename', 'loginid', 'designation', 'department', 'mobno', 'email',
              'buid', 'dateofjoin', 'dateofreport', 'dateofbirth', 'gender', 'peopletype', 'enable',
              'isadmin', 'shift', 'people_extras', 'clientid']

    list_display = ['id', 'peoplecode', 'peoplename', 'loginid', 'designation', 'mobno', 'email',
                    'reportto', 'dateofjoin', 'gender', 'peopletype', 'enable', 'isadmin', 'clientid', 'shift']

    list_display_links = ['peoplecode', 'peoplename']


class PgroupResource(resources.ModelResource, BaseFieldSet2):

    identifier = fields.Field(
        column_name='identifier',
        attribute='identifier',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode')
    )

    class Meta:
        model = pm.Pgroup
        skip_unchanged = True
        report_skipped = True
        fields = ['groupname', 'enable', 'identifier',
                  'buid', 'clientid', 'cuser', 'muser']


@admin.register(Pgroup)
class PgroupAdmin(ImportExportModelAdmin):
    resource_class = PgroupResource
    fields = ['groupname', 'enable',
              'identifier', 'clientid', 'buid']
    list_display = ['id', 'groupname',
                    'enable', 'identifier', 'clientid', 'buid']
    list_display_links = ['groupname', 'enable', 'identifier']


class PgbelongingResource(resources.ModelResource, BaseFieldSet2):
    groupid = fields.Field(
        column_name='groupid',
        attribute='groupid',
        widget=wg.ForeignKeyWidget(pm.Pgroup, 'groupname')
    )
    peopleid = fields.Field(
        column_name='peopleid',
        attribute='peopleid',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode')
    )

    class Meta:
        model = pm.Pgbelonging
        skip_unchanged = True
        report_skipped = True
        fields = ['groupid', 'peopleid', 'isgrouplead',
                  'assignsites', 'clientid', 'buid', 'cuser', 'muser']


@admin.register(Pgbelonging)
class PgbelongingAdmin(ImportExportModelAdmin):
    resource_class = PgbelongingResource
    fields = ['id', 'groupid', 'peopleid',
              'isgrouplead', 'assignsites', 'buid', 'clientid']
    list_display = ['id', 'groupid', 'peopleid',
                    'isgrouplead', 'assignsites', 'buid']
    list_display_links = ['groupid', 'peopleid']


class CapabilityResource(resources.ModelResource, BaseFieldSet2):

    parent = fields.Field(
        column_name='parent',
        attribute='parent',
        widget=wg.ForeignKeyWidget(pm.Capability, 'capscode'))

    class Meta:
        model = Capability
        skip_unchanged = True
        report_skipped = True
        fields = ('id', 'capscode',  'capsname', 'cfor',
                  'parent', 'cuser', 'muser')

    def before_save_instance(self, instance, using_transactions, dry_run):
        super().before_save_instance(instance, using_transactions, dry_run)
        instance.capscode = instance.capscode.upper()


@admin.register(Capability)
class CapabilityAdmin(ImportExportModelAdmin):
    resource_class = CapabilityResource
    fields = ['capscode', 'capsname', 'cfor', 'parent']
    list_display = ['capscode', 'capsname', 'enable', 'cfor', 'parent',
                    'cdtz', 'mdtz', 'cuser', 'muser']
    list_display_links = ['capscode', 'capsname']

    def get_queryset(self, request):
        print(super(CapabilityAdmin, self).get_queryset(request))
        return super(CapabilityAdmin, self).get_queryset(request).select_related('cuser', 'muser')
