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
from django.core.exceptions import ValidationError
import re
from math import isnan
from apps.core.widgets import EnabledTypeAssistWidget

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

def default_ta():
    return utils.get_or_create_none_typeassist()[0]


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

''''TaResource class provides functionalities for importing and validating data 
related to the om.TypeAssist model in a Django application. It ensures data integrity 
by cleaning, validating, and checking for uniqueness before saving the imported data.'''
class TaResource(resources.ModelResource):
    CLIENT = fields.Field(
        column_name='Client*',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default='NONE'
    )
    
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
        import_id_fields = ['ID']
        report_skipped = True
        fields = ('NAME', 'CODE', 'TYPE', 'CLIENT')

        
    def __init__(self, *args, **kwargs):
        super(TaResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):

        '''cleaning in sence Handles empty string,Removes extra spaces, 
        Converts to uppercase and replaces spaces with underscores (if code is True)'''
        row['Code*'] = clean_string(row.get('Code*', 'NONE'), code=True)
        row['Name*'] = clean_string(row.get('Name*', "NONE"))

        # Validates that required fields (Code*, Type*, and Name*) are not empty.
        if row['Code*'] in ['', None]: raise ValidationError("Code* is required field")
        if row['Type*'] in ['', None]: raise ValidationError("Type* is required field")
        if row['Name*'] in ['', None]: raise ValidationError("Name* is required field")
        
        ''' Validates the format of the Code* field using a regular expression.
         It ensures no spaces and only allows alphanumeric characters, underscores, and hyphens.'''
        regex, value = "^[a-zA-Z0-9\-_]*$", row['Code*']
        if " " in value: raise ValidationError("Please enter text without any spaces")
        if  not re.match(regex, value):
            raise ValidationError("Please enter valid text avoid any special characters except [_, -]")

        '''Checks for uniqueness of the record based on a combination of Code*, Type*, 
        and CLIENT* fields. It raises an error if a duplicate record is found.'''
        if om.TypeAssist.objects.select_related().filter(
            tacode=row['Code*'], tatype__tacode=row['Type*'],
            client__bucode = row['Client*']).exists():
            raise ValidationError(f"Record with these values already exist {', '.join(row.values())}")
        

        super().before_import_row(row, **kwargs)

    #saving the instance before saving it to the database
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        '''inserts data into the instance object before saving it to 
        the database of cuser, muser, cdtz, and mdtz fields.'''
        utils.save_common_stuff(self.request, instance, self.is_superuser)
        
    
    
        


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

class BtResource(resources.ModelResource):
    BelongsTo = fields.Field(
        column_name='Belongs To*',
        default=utils.get_or_create_none_bv,
        attribute='parent',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'))

    BuType = fields.Field(
        column_name='Site Type',
        default=default_ta,
        attribute='butype',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))

    tenant = fields.Field(
        column_name='Tenant',
        default=utils.get_or_create_none_tenant,
        attribute='tenant',
        widget = wg.ForeignKeyWidget(tm.Tenant, 'tenantname'))

    Identifier = fields.Field(
        column_name='Type*',
        attribute='identifier',
        default=default_ta,
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))
    
    Sitemanager = fields.Field(
        column_name='Site Manager*',
        attribute='siteincharge',
        default=utils.get_or_create_none_people,
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode'))
    
    ID      = fields.Field(attribute='id', column_name="ID")
    Code    = fields.Field(attribute='bucode', column_name='Code*')
    Name    = fields.Field(attribute='buname', column_name='Name*')
    GPS     = fields.Field(attribute='gpslocation', column_name='GPS Location', saves_null_values=True)
    Address = fields.Field(column_name='Address', widget=wg.CharWidget(), saves_null_values=True)
    State   = fields.Field(column_name='State', widget=wg.CharWidget(), saves_null_values=True)
    City    = fields.Field(column_name='City', widget=wg.CharWidget(), saves_null_values=True)
    Country = fields.Field(column_name='Country', widget=wg.CharWidget(), saves_null_values=True)
    SOLID   = fields.Field(attribute='solid', column_name='Sol Id', widget=wg.CharWidget())
    Enable  = fields.Field(attribute='enable', column_name='Enable', default=True)

    class Meta:
        model = om.Bt
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = (
            'Name', 'Code', 'BuType', 'SOLID', 
            'Enable', 'GPS', 'ID','Address', 'State',
            'City', 'Country',
            'Identifier', 'BelongsTo', 'tenant',)

    def __init__(self, *args, **kwargs):
        super(BtResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        
    
    def before_import_row(self, row, **kwargs):
        row['Code*'] = clean_string(row.get('Code*', 'NONE'), code=True)
        row['Name*'] = clean_string(row.get('Name*', "NONE"))
        self._gpslocation = clean_point_field(row['GPS Location'])
        self._solid = row['Sol Id']
        self._address = row['Address']
        self._state = row['State']
        self._city = row['City']
        self._country = row['Country']
        self._latlng = row['GPS Location']
        # check required fields
        if row['Code*'] in ['', None]: raise ValidationError("Code* is required field")
        if row['Type*'] in ['', None]: raise ValidationError("Type* is required field")
        if row['Name*'] in ['', None]: raise ValidationError("Name* is required field")
        if row['Belongs To*'] in ['', None]: raise ValidationError("Name* is required field")
        
        # code validation
        regex, value = "^[a-zA-Z0-9\-_]*$", row['Code*']
        if " " in value: raise ValidationError("Please enter text without any spaces")
        if  not re.match(regex, value):
            raise ValidationError("Please enter valid text avoid any special characters except [_, -]")
        
        # unique record check
        if om.Bt.objects.select_related().filter(
            bucode=row['Code*'], parent__bucode=row['Belongs To*'],
            identifier__tacode = row['Type*']).exists():
            raise ValidationError(f"Record with these values already exist {row.values()}")
        
        super().before_import_row(row, **kwargs)


    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.gpslocation = self._gpslocation
        instance.bupreferences['address'] = self._address
        instance.bupreferences['address2'] = {
            'city':self._city, 'country':self._country,
            'state':self._state, 'formattedAddress':self._address,
            'latlng':self._latlng}
        if self._solid and not (isinstance(self._solid, float) and isnan(self._solid)):
            instance.solid = int(self._solid)
        else:
            instance.solid = None
            
        utils.save_common_stuff(self.request, instance)

    def get_queryset(self):
        return om.Bt.objects.select_related().all()

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




        
class TaResourceUpdate(resources.ModelResource):
    CLIENT = fields.Field(
        column_name = 'Client',
        attribute ='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default = 'NONE'
    )
    
    TYPE = fields.Field(
        column_name = 'Type',
        attribute = 'tatype',
        default = om.TypeAssist, 
        widget = EnabledTypeAssistWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )

    CODE = fields.Field(attribute='tacode', column_name='Code')
    NAME = fields.Field(attribute='taname', column_name='Name')
    ID   = fields.Field(attribute='id', column_name='ID*')

    class Meta: 
        model = om.TypeAssist
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = ('ID','NAME', 'CODE', 'TYPE', 'CLIENT')

    def __init__(self, *args, **kwargs):
        super(TaResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):
        '''cleaning in sence Handles empty string,Removes extra spaces, 
        Converts to uppercase and replaces spaces with underscores (if code is True)'''
        if 'Code' in row:
            row['Code'] = clean_string(row.get('Code'), code=True)
        if 'Name' in row:
            row['Name'] = clean_string(row.get('Name'))

        # Validates that required fields (Code*, Type*, and Name*) are not empty.
        if 'Code' in row:
            if row['Code'] in ['', None]: raise ValidationError("Code is required field")
        if 'Type' in row:
            if row['Type'] in ['', None]: raise ValidationError("Type is required field")
        if 'Name' in row:
            if row['Name'] in ['', None]: raise ValidationError("Name is required field")
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        
        ''' Validates the format of the Code* field using a regular expression.
         It ensures no spaces and only allows alphanumeric characters, underscores, and hyphens.'''
        if 'Code' in row:
            regex, value = "^[a-zA-Z0-9\-_]*$", row['Code']
            if " " in value: raise ValidationError("Please enter text without any spaces")
            if not re.match(regex, value):
                raise ValidationError("Please enter valid text avoid any special characters except [_, -]")

        '''check record exists '''
        if not om.TypeAssist.objects.filter(id=row['ID*']).exists():    
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")

        super().before_import_row(row, **kwargs)

    #saving the instance before saving it to the database
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        '''inserts data into the instance object before saving it to 
        the database of cuser, muser, cdtz, and mdtz fields.'''
        utils.save_common_stuff(self.request, instance, self.is_superuser)

class BtResourceUpdate(resources.ModelResource):
    BelongsTo = fields.Field(
        column_name = 'Belongs To',
        default = utils.get_or_create_none_bv,
        attribute = 'parent',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'))

    BuType = fields.Field(
        column_name = 'Site Type',
        default = default_ta,
        attribute = 'butype',
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))

    Identifier = fields.Field(
        column_name = 'Type',
        attribute = 'identifier',
        default = default_ta,
        widget = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'))
    
    Sitemanager = fields.Field(
        column_name = 'Site Manager',
        attribute = 'siteincharge',
        default = utils.get_or_create_none_people,
        widget = wg.ForeignKeyWidget(pm.People, 'peoplecode'))
    
    ID      = fields.Field(attribute='id', column_name="ID*")
    Code    = fields.Field(attribute='bucode', column_name='Code')
    Name    = fields.Field(attribute='buname', column_name='Name')
    GPS     = fields.Field(attribute='gpslocation', column_name='GPS Location', saves_null_values=True)
    Address = fields.Field(column_name='Address', attribute = 'bupreferences.address', widget=wg.CharWidget(), saves_null_values=True)
    State   = fields.Field(column_name='State', attribute = 'bupreferences.address2.state', widget=wg.CharWidget(), saves_null_values=True)
    City    = fields.Field(column_name='City', attribute = 'bupreferences.address2.city', widget=wg.CharWidget(), saves_null_values=True)
    Country = fields.Field(column_name='Country', attribute = 'bupreferences.address2.country', widget=wg.CharWidget(), saves_null_values=True)
    SOLID   = fields.Field(attribute='solid', column_name='Sol Id', widget=wg.CharWidget())
    Enable  = fields.Field(attribute='enable', column_name='Enable', widget=wg.BooleanWidget(), default=True)

    class Meta:
        model = om.Bt
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = (
            'ID', 'Name', 'Code', 'BuType', 'SOLID', 'Enable', 'GPS', 'Address', 
            'State', 'City', 'Country', 'Identifier', 'BelongsTo')

    def __init__(self, *args, **kwargs):
        super(BtResourceUpdate, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        
    def before_import_row(self, row, **kwargs):
        if 'Code' in row:
            row['Code'] = clean_string(row.get('Code'), code=True)
        if 'Name' in row:
            row['Name'] = clean_string(row.get('Name'))
        self._gpslocation = clean_point_field(row['GPS Location'])
        if 'Sol Id' in row:
            self._solid = row['Sol Id']
        required_fields = ['Address', 'State', 'City', 'Country', 'GPS Location']
        present_fields = [field for field in required_fields if field in row]
        if len(present_fields) == len(required_fields):
            self._address = row['Address']
            self._state = row['State']
            self._city = row['City']
            self._country = row['Country']
            self._latlng = row['GPS Location']
        elif len(present_fields) > 0:
            raise ValidationError("To create a complete address, you need to provide the Address, State, City, Country, and GPS Location.")
        
        # check required fields
        if row.get('ID*') in ['', 'NONE', None] or (isinstance(row.get('ID*'), float) and isnan(row.get('ID*'))): raise ValidationError({'ID*':"This field is required"})
        if 'Code' in row:
            if row['Code'] in ['', None]: raise ValidationError("Code is required field")
        if 'Type' in row:
            if row['Type'] in ['', None]: raise ValidationError("Type is required field")
        if 'Name' in row:
            if row['Name'] in ['', None]: raise ValidationError("Name is required field")
        if 'Belongs To' in row:
            if row['Belongs To'] in ['', None]: raise ValidationError("Belongs To is required field")
        
        # code validation
        if 'Code' in row:
            regex, value = "^[a-zA-Z0-9\-_]*$", row['Code']
            if " " in value: raise ValidationError("Please enter text without any spaces")
            if  not re.match(regex, value):
                raise ValidationError("Please enter valid text avoid any special characters except [_, -]")
        
        # check record exists
        if not om.Bt.objects.filter(id=row['ID*']).exists():
            raise ValidationError(f"Record with these values not exist: ID - {row['ID*']}")
        
        super().before_import_row(row, **kwargs)

    def before_save_instance(self, instance, using_transactions, dry_run):
        instance.gpslocation = self._gpslocation
        instance.bupreferences['address'] = self._address
        instance.bupreferences['address2'] = {
            'city':self._city, 'country':self._country,
            'state':self._state, 'formattedAddress':self._address,
            'latlng':self._latlng}
        if self._solid and not (isinstance(self._solid, float) and isnan(self._solid)):
            instance.solid = int(self._solid)
        else:
            instance.solid = None
            
        utils.save_common_stuff(self.request, instance)
