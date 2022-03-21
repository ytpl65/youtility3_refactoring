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


def save_people_passwd( user):
    log.info('Password is created by system... DONE')
    paswd = user.loginid + '@' + 'youtility'
    user.set_password(paswd)
    
def save_other_stuff(request, user):
    user.cuser.id = user.muser.id = request.session('_auth_user_id')



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
        widget=wg.DateWidget()
    )
    dateofjoin = fields.Field(
        column_name='dateofjoin',
        attribute='dateofjoin',
        widget=wg.DateWidget()
    )
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
    
    client = fields.Field(
        column_name='client',
        attribute='client',
        widget=wg.ForeignKeyWidget(om.Bt, 'bucode')
    )
    bu = fields.Field(
        column_name='bu',
        attribute='bu',
        widget=wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values=True
    )

    class Meta:
        model = pm.People
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('id',)
        fields = ['id', 'peoplecode', 'peoplename', 'loginid', 'designation', 'department', 'mobno', 'email',
                  'bu', 'dateofjoin', 'dateofreport', 'dateofbirth', 'gender', 'peopletype', 'enable',
                  'isadmin', 'shift', 'client', 'cuser', 'muser']

    def before_save_instance(self, instance, using_transactions, dry_run):
        super().before_save_instance(instance, using_transactions, dry_run)
        instance.peoplecode = instance.peoplecode.upper()
        save_people_passwd(instance)
       # save_other_stuff(self.request, instance)
        
    


@admin.register(People)
class PeopleAdmin(ImportExportModelAdmin):
    resource_class = PeopleResource
    fields = ['peoplecode', 'peoplename', 'loginid', 'designation', 'department', 'mobno', 'email',
              'bu', 'dateofjoin', 'dateofreport', 'dateofbirth', 'gender', 'peopletype', 'enable',
              'isadmin', 'people_extras', 'client', ]

    list_display = ['id', 'peoplecode', 'peoplename', 'loginid',  'mobno', 'email','password',
                     'gender', 'peopletype', 'isadmin', 'client']

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
                  'bu', 'client', 'cuser', 'muser']


@admin.register(Pgroup)
class PgroupAdmin(ImportExportModelAdmin):
    resource_class = PgroupResource
    fields = ['groupname', 'enable',
              'identifier', 'client', 'bu']
    list_display = ['id', 'groupname',
                    'enable', 'identifier', 'client', 'bu']
    list_display_links = ['groupname', 'enable', 'identifier']


class PgbelongingResource(resources.ModelResource, BaseFieldSet2):
    pgroup = fields.Field(
        column_name='pgroup',
        attribute='pgroup',
        widget=wg.ForeignKeyWidget(pm.Pgroup, 'groupname')
    )
    people = fields.Field(
        column_name='people',
        attribute='people',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode')
    )

    class Meta:
        model = pm.Pgbelonging
        skip_unchanged = True
        report_skipped = True
        fields = ['pgroup', 'people', 'isgrouplead',
                  'assignsites', 'client', 'bu', 'cuser', 'muser']


@admin.register(Pgbelonging)
class PgbelongingAdmin(ImportExportModelAdmin):
    resource_class = PgbelongingResource
    fields = ['id', 'pgroup', 'people',
              'isgrouplead', 'assignsites', 'bu', 'client']
    list_display = ['id', 'pgroup', 'people',
                    'isgrouplead', 'assignsites', 'bu']
    list_display_links = ['pgroup', 'people']


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
