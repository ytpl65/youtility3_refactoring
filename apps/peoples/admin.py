from django.utils import timezone
import apps.peoples.utils as putils
import apps.core.utils as utils
from apps.onboarding.admin import BaseFieldSet1, BaseFieldSet2
from apps.onboarding import models as om
from apps.peoples import models as pm
from import_export import widgets as wg
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import People,  Pgroup, Pgbelonging, Capability
from django.contrib import admin
from multiprocessing.spawn import import_main_path
import logging

log = logging.getLogger('__main__')


def save_people_passwd(user):
    log.info('Password is created by system... DONE')
    paswd = f'{user.loginid}@youtility'
    user.set_password(paswd)


# Register your models here
class PeopleResource(resources.ModelResource, BaseFieldSet2):
    department = fields.Field(
        column_name='department',
        attribute='department',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        default='NONE'
    )
    designation = fields.Field(
        column_name='designation',
        attribute='designation',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        default='NONE'
    )
    peopletype = fields.Field(
        column_name='peopletype',
        attribute='peopletype',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        default='NONE'
    )
    reportto = fields.Field(
        column_name='reportto',
        attribute='reportto',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'),
        default='NONE'
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

    client = fields.Field(
        column_name='client',
        attribute='client',
        widget=wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    bu = fields.Field(
        column_name='bu',
        attribute='bu',
        widget=wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values=True,
        default='NONE'
    )

    class Meta:
        model = pm.People
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('id',)
        fields = [
            'id', 'peoplecode', 'peoplename', 'loginid', 'designation', 'department', 'mobno', 'email',
            'bu', 'dateofjoin', 'dateofreport', 'dateofbirth', 'gender', 'peopletype', 'enable',
            'isadmin', 'client', 'cdtz', 'mdtz']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(PeopleResource, self).__init__(*args, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.peoplecode = instance.peoplecode.upper()
        utils.save_common_stuff(self.request, instance)
        save_people_passwd(instance)


@admin.register(People)
class PeopleAdmin(ImportExportModelAdmin):
    resource_class = PeopleResource

    list_display = ['id', 'peoplecode', 'peoplename', 'loginid',  'mobno', 'email', 'password',
                    'gender', 'peopletype', 'isadmin', 'client', 'cuser', 'muser', 'cdtz', 'mdtz']

    list_display_links = ['peoplecode', 'peoplename']
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('loginid', 'password1', 'password2'),
        }),
    )
    fieldsets = (
        ('Create/Update People', {'fields':['peoplecode', 'peoplename', 'loginid',  'mobno', 'email',
              'bu', 'dateofjoin', 'dateofbirth', 'gender',  'enable', 'tenant',
              'isadmin', 'client']}),
        ('Add/Remove Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        })
    )

    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}

    def get_queryset(self, request):
        return pm.People.objects.select_related(
            'peopletype', 'cuser', 'muser', 'client', 'bu').all()


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
        fields = ['name', 'enable', 'identifier',
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
        widget=wg.ForeignKeyWidget(pm.Pgroup, 'name')
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
        import_id_fields = ('id', 'capscode', 'cfor',)
        report_skipped = True
        fields = ('id', 'capscode',  'capsname', 'cfor', 
                  'parent', 'cuser', 'muser', 'client', 'bu', 'tenant')



    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(CapabilityResource, self).__init__(*args, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.capscode = instance.capscode.upper()
        utils.save_common_stuff(self.request, instance)
    
    
    
    
@admin.register(Capability)
class CapabilityAdmin(ImportExportModelAdmin):
    resource_class = CapabilityResource
    fields = ['capscode', 'capsname', 'cfor', 'parent']
    list_display = ['capscode', 'capsname', 'enable', 'cfor', 'parent',
                    'cdtz', 'mdtz', 'cuser', 'muser']
    list_display_links = ['capscode', 'capsname']


    
    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}

    def get_queryset(self, request):
        return pm.Capability.objects.select_related(
            'parent', 'cuser', 'muser').all()

