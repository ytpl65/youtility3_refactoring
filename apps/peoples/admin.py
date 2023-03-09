import apps.core.utils as utils
from apps.onboarding.admin import BaseFieldSet2
from apps.onboarding import models as om
from apps.peoples import models as pm
from import_export import widgets as wg
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from .models import People,  Pgroup, Pgbelonging, Capability
from django.contrib import admin
import logging

log = logging.getLogger('__main__')

def save_people_passwd(user):
    log.info('Password is created by system... DONE')
    paswd = f'{user.loginid}@youtility'
    user.set_password(paswd)

# Register your models here
class PeopleResource(resources.ModelResource):
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
    
    Department = fields.Field(
        column_name='Department',
        attribute='department',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        default='NONE'
    )
    Designation = fields.Field(
        column_name='Designation',
        attribute='designation',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        default='NONE'
    )
    
    PeopleType = fields.Field(
        column_name='People Type',
        attribute='peopletype',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        default='NONE'
    )
    Reportto = fields.Field(
        column_name='Report To',
        attribute='reportto',
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode'),
        default='NONE'
    )
    DateOfBirth = fields.Field(
        column_name='Date of Birth',
        attribute='dateofbirth',
        widget = wg.DateWidget()
    )
    
    DateOfJoin = fields.Field(
        column_name='Date of Join',
        attribute='dateofjoin',
        widget = wg.DateWidget()
    )
    
    DateOfReport = fields.Field(
        column_name='Date of Report',
        attribute='dateofreport',
        widget = wg.DateWidget()
    )

    ID      = fields.Field(attribute='id')
    Code    = fields.Field(attribute='peoplecode', column_name='People Code')
    Name    = fields.Field(attribute='peoplename', column_name='People Name')
    LoginId = fields.Field(attribute='loginid', column_name='Login ID')
    MobNo   = fields.Field(attribute='mobno', column_name='Mob No')
    Email   = fields.Field(attribute='email', column_name='Email')
    Gender  = fields.Field(attribute='email')
    Enable  = fields.Field(widget=wg.BooleanWidget(), attribute='enable', default=True)
    IsAdmin = fields.Field(attribute='isadmin', column_name='Is Admin', widget=wg.BooleanWidget())

    class Meta:
        model = pm.People
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('ID','Code')
        fields = [
            'ID', 'Code', 'Name', 'LoginId', 'Designation', 'Department', 'MobNo', 'Email',
            'BV', 'DateOfJoin', 'DateOfReport', 'DateOfBirth', 'Gender', 'PeopleType', 'Enable',
            'IsAdmin', 'Client']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(PeopleResource, self).__init__(*args, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.peoplecode = instance.peoplecode.upper()
        utils.save_common_stuff(self.request, instance)
        save_people_passwd(instance)
    
    def skip_row(self, instance, original):
        return pm.People.objects.filter(peoplecode = instance.peoplecode).exists()

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

class PeopleGroupResource(resources.ModelResource):
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
    Identifier = fields.Field(
        attribute='identifier',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        default='PEOPLEGROUP'
    )
    ID = fields.Field(attribute='id')
    Enable = fields.Field(attribute='enable', column_name='Enable', widget=wg.BooleanWidget(), default=True)
    Name = fields.Field(attribute='groupname', column_name='Group Name')
    
    class Meta:
        model = pm.Pgroup
        skip_unchanged = True,
        import_id_fields = ('ID', 'Name')
        report_skipped = True,
        fields = ('ID', 'Client', 'BV', 'Identifier', 'Enable', 'Name')


class SiteGroupResource(resources.ModelResource):
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
    Identifier = fields.Field(
        attribute='identifier',
        widget=wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        default='SITEGROUP'
    )
    ID = fields.Field(attribute='id')
    Enable = fields.Field(attribute='enable', column_name='Enable', widget=wg.BooleanWidget(), default=True)
    Name = fields.Field(attribute='groupname', column_name='Group Name')
    
    class Meta:
        model = pm.Pgroup
        skip_unchanged = True
        import_id_fields = ('ID', 'Name')
        report_skipped = True,
        fields = ('ID', 'Client', 'BV', 'Identifier', 'Enable', 'Name')









class PgroupResource(resources.ModelResource, BaseFieldSet2):

    identifier = fields.Field(
        column_name='Identifier',
        attribute='identifier',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode')
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
        widget = wg.ForeignKeyWidget(pm.Pgroup, 'name')
    )
    people = fields.Field(
        column_name='people',
        attribute='people',
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode')
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

class CapabilityResource(resources.ModelResource):

    parent = fields.Field(
        column_name='Belongs To',
        attribute='parent',
        widget = wg.ForeignKeyWidget(pm.Capability, 'capscode'))

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

    ID   = fields.Field(attribute='id')
    Code = fields.Field(attribute='capscode')
    Name = fields.Field(attribute='capsname')
    cfor = fields.Field(attribute='cfor', column_name='Capability For')


    class Meta:
        model = Capability
        skip_unchanged = True
        import_id_fields = ('ID', 'Code', 'cfor',)
        report_skipped = True
        fields = ('ID', 'Code',  'Name', 'cfor',
                  'parent', 'Client', 'BV', 'tenant')


    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.is_superuser = kwargs.pop('is_superuser', None)
        super(CapabilityResource, self).__init__(*args, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.capscode = instance.capscode.upper()
        utils.save_common_stuff(self.request, instance, self.is_superuser)

    def skip_row(self, instance, original):
        return Capability.objects.filter(capscode = instance.capscode).exists()

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

