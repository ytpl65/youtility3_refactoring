import apps.core.utils as utils
from apps.onboarding.admin import BaseFieldSet2
from apps.onboarding import models as om
from apps.peoples import models as pm
from import_export import widgets as wg
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from django.db.models import Q
from .models import People,  Pgroup, Pgbelonging, Capability
from django.contrib import admin
import logging

log = logging.getLogger('__main__')

def save_people_passwd(user):
    log.info('Password is created by system... DONE')
    paswd = f'{user.loginid}@youtility' if not user.password else user.password
    user.set_password(paswd)
    
class TypeAssistFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.filter(
            Q(client__bucode__exact=row["Client"])
        )

class CustomFiedWidget(wg.Widget):
    def clean(self, value, row, *args, **kwargs):
        ic("calling")
        return value
    


def default_ta():
    return utils.get_or_create_none_typeassist()[0]

# Register your models here
class PeopleResource(resources.ModelResource):
    Client = fields.Field(
        column_name='Client',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default=utils.get_or_create_none_bv
    )
    BV = fields.Field(
        column_name='Site',
        attribute='bu',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default=utils.get_or_create_none_bv
    )
    
    Department = fields.Field(
        column_name='Department',
        attribute='department',
        widget = TypeAssistFKW(om.TypeAssist, 'tacode'),
        default=default_ta
    )
    Designation = fields.Field(
        column_name='Designation',
        attribute='designation',
        widget = TypeAssistFKW(om.TypeAssist, 'tacode'),
        default=default_ta
    )
    PeopleType = fields.Field(
        column_name='Employee Type',
        attribute='peopletype',
        widget = TypeAssistFKW(om.TypeAssist, 'tacode'),
        default=default_ta
    )
    WorkType = fields.Field(
        column_name='Work Type',
        attribute='worktype',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        default=default_ta
    )
    Reportto = fields.Field(
        column_name='Report To',
        attribute='reportto',
        widget = wg.ForeignKeyWidget(pm.People, 'peoplename'),
        default=utils.get_or_create_none_people
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
    
    date_of_release = fields.Field(
        column_name='Date of Release',
        attribute='dateofreport',
        widget = wg.DateWidget()
    )
    
    
    

    ID                 = fields.Field(attribute='id', column_name='ID')
    Code               = fields.Field(attribute='peoplecode', column_name='Code')
    deviceid           = fields.Field(attribute='deviceid', column_name='Device Id')
    Password           = fields.Field(attribute='password', column_name='Password', default=None)
    Name               = fields.Field(attribute='peoplename', column_name='Name')
    LoginId            = fields.Field(attribute='loginid', column_name='Login ID')
    MobNo              = fields.Field(attribute='mobno', column_name='Mob No')
    Email              = fields.Field(attribute='email', column_name='Email')
    Gender             = fields.Field(attribute='gender', column_name='Gender')
    Enable             = fields.Field(widget=wg.BooleanWidget(), attribute='enable', default=True)
    isemergencycontact = fields.Field(widget=wg.BooleanWidget(), default=False, column_name='Emergency Contact')
    alertmails         = fields.Field(widget=CustomFiedWidget(), default=False, column_name='Alert Emails')
    mobilecaps         = fields.Field(default='NONE', column_name='Mobile Capability')
    reportcaps         = fields.Field(default='NONE', column_name='Report Capability')
    webcaps            = fields.Field(default='NONE', column_name='Web Capability')
    currentaddr        = fields.Field(default='NONE', column_name='Current Address')
    permanentaddr      = fields.Field(default='NONE', column_name='Permanent Address')
    portletcaps        = fields.Field(default='NONE', column_name='Portlet Capability')
    blacklist          = fields.Field(widget=wg.BooleanWidget(), default=False, column_name='Blacklist')
    IsAdmin            = fields.Field(attribute='isadmin', column_name='Is Admin', widget=wg.BooleanWidget(), default=False)

    class Meta:
        model = pm.People
        skip_unchanged = True
        report_skipped = True
        import_id_fields = ('ID','Code', 'LoginId', 'Client')
        fields = [
            'ID', 'Code', 'Name', 'LoginId', 'Designation', 'Department', 'MobNo', 'Email', 'deviceid',
            'Site', 'DateOfJoin', 'date_of_release', 'DateOfBirth', 'Gender', 'PeopleType','WorkType', 'Enable',
            'IsAdmin', 'Client', 'Password', 'isemergencycontact', 'alertmails', 'mobilecaps', 'reportcaps', 'webcaps',
            'portletcaps', 'blacklist', 'currentaddr', 'permanentaddr', 'Reportto']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(PeopleResource, self).__init__(*args, **kwargs)
        
    def before_import_row(self, row, **kwargs):
        self._mobilecaps         = row["Mobile Capability"].split(",") if row.get('Mobile Capability') else [], 
        ic(self._mobilecaps, row['Mobile Capability'])
        self._reportcaps         = row["Report Capability"].split(",") if row.get('Report Capability') else []
        self._webcaps            = row["Web Capability"].split(",") if row.get('Web Capability') else []
        self._portletcaps        = row["Portlet Capability"].split(",") if row.get('Portlet Capability') else []
        self._alertmails         = row.get('Alert Emails') or False
        self._blacklist          = row.get('Blacklist') or False
        self._currentaddr        = row.get('Current Address', "")
        self._permanentaddr      = row.get('Permanent Address', "")
        self._isemergencycontact = row.get('Emergency Contact') or False

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.peoplecode   = instance.peoplecode.upper()
        instance.email        = instance.email.lower()
        instance.people_extras['mobilecapability']   = self._mobilecaps
        instance.people_extras['reportcapability']   = self._reportcaps
        instance.people_extras['webcapability']      = self._webcaps
        instance.people_extras['portletcapability']  = self._portletcaps
        instance.people_extras['blacklist']          = self._blacklist
        instance.people_extras['isemergencycontact'] = self._isemergencycontact
        instance.people_extras['alertmails']         = self._alertmails
        instance.people_extras['currentaddress']     = self._currentaddr
        instance.people_extras['permanentaddress']   = self._permanentaddr
        ic(self._portletcaps)
        utils.save_common_stuff(self.request, instance)
        save_people_passwd(instance)
    
    
    def skip_row(self, instance, original, row, import_validation_errors=None):
        return pm.People.objects.filter(
            peoplecode = instance.peoplecode,
            client_id = instance.client.id).exists()

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
        return pm.People.objects.select_related().all()

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

    def skip_row(self, instance, original, row, import_validation_errors=None):
        super().skip_row(instance, original, row, import_validation_errors=None)
        return Capability.objects.filter(capscode = instance.capscode, cfor = instance.cfor).exists()
    
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

