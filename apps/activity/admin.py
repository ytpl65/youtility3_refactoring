from import_export import resources, fields
from import_export import widgets as wg
import apps.onboarding.models as om
import apps.activity.models as am
from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from django.db.utils import IntegrityError
from apps.core import utils
from apps.service.validators import clean_code, clean_string, clean_point_field
from import_export.results import RowResult
import re
from django.core.exceptions import ValidationError
from django.apps import apps
from apps.core.widgets import BVForeignKeyWidget



# Register your models here.
def default_ta():
    return utils.get_or_create_none_typeassist()[0]

class QuestionResource(resources.ModelResource):
    Unit = fields.Field(
        column_name       = 'Unit',
        attribute         = 'unit',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default=default_ta
    )
    Category = fields.Field(
        column_name       = 'Category',
        attribute         = 'category',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default=default_ta
    )
    Client = fields.Field(
        column_name='Client*',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default=utils.get_or_create_none_bv
    )

    ID         = fields.Field(attribute='id', column_name='ID')
    AlertON    = fields.Field(attribute='alerton', column_name='Alert On', saves_null_values=True)
    ALERTABOVE = fields.Field(column_name='Alert Above', saves_null_values=True)
    ALERTBELOW = fields.Field(column_name='Alert Below', saves_null_values=True)
    Options    = fields.Field(attribute='options', column_name='Options', saves_null_values=True)
    Name       = fields.Field(attribute='quesname', column_name='Question Name*')
    Type       = fields.Field(attribute='answertype', column_name='Answer Type*')
    Min        = fields.Field(attribute='min', column_name='Min', saves_null_values=True)
    Max        = fields.Field(attribute='max', column_name='Max', saves_null_values=True)
    Enable     = fields.Field(attribute='enable', column_name='Enable', default=True, widget=wg.BooleanWidget())
    IsAvpt     = fields.Field(attribute='isavpt', column_name='Is AVPT', default=False, widget=wg.BooleanWidget())
    AttType    = fields.Field(attribute='avpttype', column_name='AVPT Type', saves_null_values=True)
    isworkflow = fields.Field(attribute='isworkflow', column_name='Is WorkFlow', default=False)
    
    
    class Meta:
        model = am.Question
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = ['Name', 'Type',  'Unit', 'Options',  'Enable', 'IsAvpt', 'AttType',
                  'ID', 'Client', 'Min', 'Max', 'AlertON', 'isworkflow', 'Category']
    
    
    def __init__(self, *args, **kwargs):
        super(QuestionResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.clean_question_name_and_answer_type(row)
        self.clean_numeric_and_rating_fields(row)
        self.validate_numeric_values(row)
        self.validate_options_values(row)
        self.set_alert_on_value(row)
        self.check_unique_record(row)
        super().before_import_row(row, **kwargs)
    
    def check_required_fields(self, row):
        ic(row)
        required_fields = ['Answer Type*', 'Question Name*',  'Client*']
        for field in required_fields:
            if row.get(field) in ['', None]:
                raise ValidationError({field : f"{field} is a required field"})
    
    def clean_question_name_and_answer_type(self, row):
        row['Question Name*'] = clean_string(row.get('Question Name*'))
        row['Answer Type*'] = clean_string(row.get('Answer Type*'), code=True)
    
    def clean_numeric_and_rating_fields(self, row):
        answer_type = row.get('Answer Type*')
        if answer_type in ['NUMERIC', 'RATING']:
            row['Options'] = None
            self.convert_to_float(row, 'Min')
            self.convert_to_float(row, 'Max')
            self.convert_to_float(row, 'Alert Below')
            self.convert_to_float(row, 'Alert Above')
    
    def convert_to_float(self, row, field):
        value = row.get(field)
        if value is not None:
            row[field] = float(value)
        elif field in ['Min', 'Max']: raise ValidationError(
            {field : f"{field} is required when Answer Type* is {row['Answer Type*']}"})

    def validate_numeric_values(self, row):
        min_value = row.get('Min')
        max_value = row.get('Max')
        alert_below = row.get('Alert Below')
        alert_above = row.get('Alert Above')

        if min_value and alert_below and float(min_value) > float(alert_below):
            raise ValidationError("Alert Below should be greater than Min")
        if max_value and alert_above and float(max_value) < float(alert_above):
            raise ValidationError("Alert Above should be smaller than Max")
        if alert_above and alert_below and float(alert_above) < float(alert_below):
            raise ValidationError('Alert Above should be greater than Alert Below')
    
    def validate_options_values(self, row):
        if row['Answer Type*'] in ['CHECKBOX', 'DROPDOWN']:
            if row.get('Options') is None: raise ValidationError(
                "Options is required when Answer Type* is in [DROPDOWN, CHECKBOX]")
            if row.get('Alert On') and row['Alert On'] not in row['Options']:
                raise ValidationError({"Alert On": "Alert On needs to be in Options"})

    def set_alert_on_value(self, row):
        if row.get('Answer Type*') == 'NUMERIC':
            alert_below = row.get('Alert Below')
            alert_above = row.get('Alert Above')
            if alert_above and alert_below:
                row['Alert On'] = f"<{alert_below}, >{alert_above}"
    
    def check_unique_record(self, row):
        if am.Question.objects.select_related().filter(
            quesname=row['Question Name*'], answertype=row['Answer Type*'],
            client__bucode=row['Client*']).exists():
            raise ValidationError(f"Record with these values already exists: {', '.join(row.values())}")



    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)


@admin.register(am.Question)
class QuestionAdmin(ImportExportModelAdmin):
    resource_class = QuestionResource
    list_display = ['id','quesname']
    
    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}
    
    def get_queryset(self, request):
        return am.Question.objects.select_related().all()
    

class QuestionSetResource(resources.ModelResource):
    
    CLIENT = fields.Field(
        column_name='Client*',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default=utils.get_or_create_none_bv
    )
    BV = fields.Field(
        column_name='Site*',
        attribute='bu',
        widget = BVForeignKeyWidget(om.Bt, 'bucode'),
        default=utils.get_or_create_none_bv
    )
    
    BelongsTo = fields.Field(
        column_name='Belongs To*',
        default=utils.get_or_create_none_qset,
        attribute='parent',
        widget = wg.ForeignKeyWidget(am.QuestionSet, 'qsetname'))
    
    ID               = fields.Field(attribute='id', column_name='ID')
    SEQNO            = fields.Field(attribute='seqno', column_name="Seq No")
    QSETNAME         = fields.Field(attribute='qsetname', column_name='Question Set Name*')
    Type             = fields.Field(attribute='type', column_name='QuestionSet Type*')
    ASSETINCLUDES    = fields.Field(attribute='assetincludes', column_name='Asset Includes', default=[])
    SITEINCLUDES     = fields.Field(attribute='siteincludes', column_name='Site Includes', default=[])
    SITEGRPINCLUDES  = fields.Field(attribute='site_grp_includes', column_name='Site Group Includes', default=[])
    SITETYPEINCLUDES = fields.Field(attribute='site_type_includes', column_name='Site Type Includes', default=[])
    SHOWTOALLSITES   = fields.Field(attribute='show_to_all_sites', column_name='Show To All Sites', default=False)
    URL              = fields.Field(attribute='url', column_name='URL', default='NONE')
    
    class Meta:
        model = am.QuestionSet
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = ['Question Set Name*', 'ASSETINCLUDES', 'SITEINCLUDES', 'SITEGRPINCLUDES', 'SITETYPEINCLUDES', 
                  'SHOWTOALLSITES', 'URL', 'BV', 'CLIENT', 'Type', 'BelongsTo', 'SEQNO']

    def __init__(self, *args, **kwargs):
        super(QuestionSetResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.validate_row(row)
        self.unique_record_check(row)
        super().before_import_row(row, **kwargs)

    def check_required_fields(self, row):
        required_fields = ['QuestionSet Type*', 'Question Set Name*']
        for field in required_fields:
            if not row.get(field):
                raise ValidationError({field: f"{field} is a required field"})

        optional_fields = ['Site Group Includes', 'Site Includes', 'Asset Includes', 'Site Type Includes']
        if all(not row.get(field) for field in optional_fields):
            raise ValidationError("You should provide a value for at least one field from the following: "
                                "'Site Group Includes', 'Site Includes', 'Asset Includes', 'Site Type Includes'")
        
    def validate_row(self, row):
        models_mapping = {
            'Site Group Includes': ('peoples', 'Pgroup', 'groupname'),
            'Site Includes': ('onboarding', 'Bt', 'bucode'),
            'Asset Includes': ('activity', 'Asset', 'assetcode'),
            'Site Type Includes': ('onboarding', 'TypeAssist', 'tacode'),
        }

        for field, (app_name, model_name, lookup_field) in models_mapping.items():
            if field_value := row.get(field):
                model = apps.get_model(app_name, model_name)
                values = field_value.replace(" ", "").split(',')
                print("&&&&&&&&&&", values)
                count = model.objects.filter(**{f'{lookup_field}__in': values}).count()
                ic(count, len(values), values, model, field_value)
                if len(values) != count:
                    raise ValidationError({field: f"Some of the values specified in {field} do not exist in the system"})
                row[field] = values

    def unique_record_check(self, row):
        # unique record check
        if am.QuestionSet.objects.select_related().filter(
            qsetname=row['Question Set Name*'], type=row['QuestionSet Type*'],
            client__bucode = row['Client*'], parent__qsetname = row['Belongs To*'],
            bu__bucode=row['Site*']).exists():
            raise ValidationError(f"Record with these values already exist {row.values()}")

            
            
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)
        
class QsetFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.select_related('client', 'bu').filter(
            client__bucode__exact=row["Client*"],
            bu__bucode__exact=row['Site*']
            enable=True
        )

class QuesFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return self.model.objects.filter(
            client__bucode__exact=row["Client*"],
            enable=True            
        )

class QuestionSetBelongingResource(resources.ModelResource):
    Name = fields.Field(
        column_name       = 'Question Name*',
        attribute         = 'question',
        widget            = QuesFKW(am.Question, 'quesname'),
        saves_null_values = True,
        default=utils.get_or_create_none_question
    )
    QSET = fields.Field(
        column_name='Question Set*',
        attribute='qset',
        widget            = QsetFKW(am.QuestionSet, 'qsetname'),
        saves_null_values = True,
        default=utils.get_or_create_none_qset
        
    )
    
    CLIENT = fields.Field(
        column_name='Client*',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default=utils.get_or_create_none_bv
    )
    
    BV = fields.Field(
        column_name='Site*',
        attribute='bu',
        widget = BVForeignKeyWidget(om.Bt, 'bucode'),
        default=utils.get_or_create_none_bv
    )
    
    ANSTYPE     = fields.Field(attribute='answertype',column_name='Answer Type*')
    ID          = fields.Field(attribute='id', column_name='ID')
    SEQNO       = fields.Field(attribute='seqno', column_name='Seq No*')
    ISAVPT      = fields.Field(attribute='isavpt', column_name='Is AVPT', default=False)
    AVPTType    = fields.Field(attribute='avpttype', column_name='AVPT Type', saves_null_values=True)
    MIN         = fields.Field(attribute='min', column_name='Min')
    ALERTON     = fields.Field(attribute='alerton', column_name='Alert On')
    ALERTABOVE  = fields.Field(column_name='Alert Above', saves_null_values=True)
    ALERTBELOW  = fields.Field(column_name='Alert Below', saves_null_values=True)
    MAX         = fields.Field(attribute='max', column_name='Max')
    OPTIONS     = fields.Field(attribute='options', column_name='Options')
    ISMANDATORY = fields.Field(attribute='ismandatory', column_name='Is Mandatory', default=True)
    
    

    
    
    class Meta:
        model = am.QuestionSetBelonging
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = [
            'NAME', 'QSET', 'CLIENT', 'BV',   'OPTIONS',  'ISAVPT', 'AVPTType',
            'ID', 'MIN', 'MAX',  'ISMANDATORY', 'SEQNO', 'ANSTYPE', 'ALERTON']
        
    
    def __init__(self, *args, **kwargs):
        super(QuestionSetBelongingResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.clean_question_name_and_answer_type(row)
        self.clean_numeric_and_rating_fields(row)
        self.validate_numeric_values(row)
        self.validate_options_values(row)
        self.set_alert_on_value(row)
        self.check_unique_record(row)
        super().before_import_row(row, **kwargs)

    def check_required_fields(self, row):
        required_fields = ['Answer Type*', 'Question Name*', 'Question Set*', 'Client*', 'Site*']
        for field in required_fields:
            if row.get(field) in ['', None]:
                raise ValidationError(f"{field} is a required field")

    def clean_question_name_and_answer_type(self, row):
        row['Question Name*'] = clean_string(row.get('Question Name*'))
        row['Answer Type*'] = clean_string(row.get('Answer Type*'), code=True)

    def clean_numeric_and_rating_fields(self, row):
        answer_type = row.get('Answer Type*')
        if answer_type in ['NUMERIC', 'RATING']:
            row['Options'] = None
            self.convert_to_float(row, 'Min')
            self.convert_to_float(row, 'Max')
            self.convert_to_float(row, 'Alert Below')
            self.convert_to_float(row, 'Alert Above')

    def convert_to_float(self, row, field):
        value = row.get(field)
        if value is not None:
            row[field] = float(value)
        elif field in ['Min', 'Max']: raise ValidationError(f"{field} is required when Answer Type* is {row['Answer Type*']}")

    def validate_numeric_values(self, row):
        min_value = row.get('Min')
        max_value = row.get('Max')
        alert_below = row.get('Alert Below')
        alert_above = row.get('Alert Above')

        if min_value and alert_below and float(min_value) > float(alert_below):
            raise ValidationError("Min should be smaller than Alert Below")
        if max_value and alert_above and float(max_value) < float(alert_above):
            raise ValidationError("Max should be greater than Alert Above")
        if alert_above and alert_below and float(alert_above) < float(alert_below):
            raise ValidationError('Alert Above should be greater than Alert Below')

    def set_alert_on_value(self, row):
        if row.get('Answer Type*') == 'NUMERIC':
            alert_below = row.get('Alert Below')
            alert_above = row.get('Alert Above')
            if alert_above and alert_below:
                row['Alert On'] = f"<{alert_below}, >{alert_above}"

    def check_unique_record(self, row):
        if am.QuestionSetBelonging.objects.select_related().filter(
            qset__qsetname=row['Question Set*'], question__quesname=row['Question Name*'],
            client__bucode=row['Client*'], bu__bucode=row['Site*']).exists():
            raise ValidationError(f"Record with these values already exists: {row.values()}")

    def validate_options_values(self, row):
        if row['Answer Type*'] in ['CHECKBOX', 'DROPDOWN']:
            if row.get('Options') is None: raise ValidationError(
                "Options is required when Answer Type* is in [DROPDOWN, CHECKBOX]")
            if row.get('Alert On') and row['Alert On'] not in row['Options']:
                raise ValidationError("Alert On needs to be in Options")
            
 
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)
        
        
        
        
class AssetResource(resources.ModelResource):
    Client = fields.Field(
        column_name = 'Client*',
        attribute   = 'client',
        widget      = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default     = utils.get_or_create_none_bv
    )
    BV = fields.Field(
        column_name       = 'Site*',
        attribute         = 'bu',
        widget            = BVForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default           = utils.get_or_create_none_bv
    )
    Unit = fields.Field(
        column_name       = 'Unit',
        attribute         = 'unit',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = default_ta
    )
    Category = fields.Field(
        column_name       = 'Category',
        attribute         = 'category',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default=default_ta
    )
    Brand = fields.Field(
        column_name       = 'Brand',
        attribute         = 'brand',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default=default_ta
    )

    ServiceProvider = fields.Field(
        column_name       = 'Service Provider',
        attribute         = 'serv_prov',
        widget            = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default=utils.get_or_create_none_bv,
    )

    SubCategory = fields.Field(
        column_name       = 'Sub Category',
        attribute         = 'subcategory',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default=default_ta
    )

    BelongsTo = fields.Field(
        column_name       = 'Belongs To*',
        attribute         = 'parent',
        widget            = wg.ForeignKeyWidget(am.Asset, 'tacode'),
        saves_null_values = True,
        default=utils.get_or_create_none_asset
    )
    
    Type = fields.Field(
        column_name       = 'Asset Type',
        attribute         = 'type',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default=default_ta
    )
    Identifier    = fields.Field(attribute='identifier', column_name='Identifier*', default='ASSET')
    ID            = fields.Field(attribute='id')
    ENABLE        = fields.Field(attribute='id', column_name='Enable')
    is_critical   = fields.Field(attribute='iscritical', column_name='Is Critical', default=False, widget=wg.BooleanWidget())
    is_meter      = fields.Field(column_name='Is Meter', widget=wg.BooleanWidget(),  default=False)
    Code          = fields.Field(attribute='assetcode', column_name='Code*')
    Name          = fields.Field(attribute='assetname', column_name='Name*')
    RunningStatus = fields.Field(attribute='runningstatus', column_name='Running Status*')
    Capacity      = fields.Field(widget=wg.DecimalWidget(), column_name='Capacity', attribute='capacity', default=0.0)
    GPS           = fields.Field(attribute='gpslocation', column_name='GPS Location')
    is_nonengg_asset = fields.Field(column_name='Is Non Engg. Asset', default=False, widget=wg.BooleanWidget())
    supplier  = fields.Field( column_name='Supplier', default="")
    meter = fields.Field(column_name='Meter', default="")
    model = fields.Field(column_name='Model', default="")
    invoice_no = fields.Field(column_name='Invoice No', default="")
    invoice_date = fields.Field(column_name='Invoice Date', default="")
    service = fields.Field(column_name='Service', default="")
    sfdate = fields.Field(column_name='Service From Date', default="")
    stdate = fields.Field(column_name='Service To Date', default="")
    yom = fields.Field(column_name='Year of Manufacture', default="")
    msn = fields.Field(column_name='Manufactured Serial No', default="")
    bill_val = fields.Field(column_name='Bill Value', default="")
    bill_date = fields.Field(column_name='Bill Date', default="")
    purchase_date = fields.Field(column_name='Purchase Date', default="")
    inst_date = fields.Field(column_name='Installation Date', default="")
    po_number = fields.Field(column_name='PO Number', default="")
    far_asset_id = fields.Field(column_name='FAR Asset ID', default="")
    
    
    
    class Meta:
        model = am.Asset
        skip_unchanged = True
        import_id_fields = ('ID', 'Code', 'Name', 'Client')
        report_skipped = True
        fields = ('ID', 'Code', 'Name',  'GPS', 'Identifier' 'is_critical',
                  'RunningStatus', 'Capacity', 'BelongsTo', 'Type', 'Client', 'BV',
                  'Category', 'SubCategory', 'Brand', 'Unit', 'ServiceProvider',
                  'ENABLE', 'is_critical', 'is_meter', 'is_nonengg_asset', 'supplier',
                  'meter', 'model', 'invoice_no', 'invoice_date','service','sfdate',
                  'stdate', 'yom','msn', 'bill_val', 'bill_date', 'purchase_date',
                  'inst_date', 'po_number', 'far_asset_id'
                  )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    
    def before_import_row(self, row, row_number=None, **kwargs):
        self.validations(row)
        self.initialize_attributes(row)
    
    def initialize_attributes(self, row):
        attributes = [
            ('_ismeter', 'Is Meter', False),
            ('_is_nonengg_asset', 'Is Non Engg. Asset', False),
            ('_supplier', 'Supplier', ''),
            ('_meter', 'Meter', ''),
            ('_model', 'Model', ''),
            ('_invoice_no', 'Invoice No', ''),
            ('_invoice_date', 'Invoice Date', ''),
            ('_service', 'Service', ''),
            ('_sfdate', 'Service From Date', ''),
            ('_stdate', 'Service To Date', ''),
            ('_yom', 'Year of Manufacture', ''),
            ('_msn', 'Manufactured Serial No', ''),
            ('_bill_val', 'Bill Value', 0.0),
            ('_bill_date', 'Bill Date', ''),
            ('_purchase_date', 'Purchase Date', ''),
            ('_inst_date', 'Installation Date', ''),
            ('_po_number', 'PO Number', ''),
            ('_far_asset_id', 'FAR Asset ID', '')
        ]

        for attribute_name, key, default_value in attributes:
            setattr(self, attribute_name, row.get(key, default_value))

    
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        asset_json = instance.asset_json

        attributes = {
            'ismeter': self._ismeter,
            'tempcode': self._ismeter,  # I assume this is intentional, otherwise, replace with the correct value
            'is_nonengg_asset': self._is_nonengg_asset,
            'supplier': self._supplier,
            'service': self._service,
            'meter': self._meter,
            'model': self._model,
            'bill_val': self._bill_val,
            'invoice_date': self._invoice_date,
            'invoice_no': self._invoice_no,
            'msn': self._msn,
            'bill_date': self._bill_date,
            'purchase_date': self._purchase_date,  # I assume this is intentional, otherwise, replace with the correct value
            'inst_date': self._inst_date,
            'sfdate': self._sfdate,
            'stdate': self._po_number,
            'yom': self._yom,
            'po_number': self._po_number,
            'far_asset_id': self._far_asset_id
        }

        for key, value in attributes.items():
            asset_json[key] = value
        instance.asset_json.update(asset_json)
        utils.save_common_stuff(self.request, instance, self.is_superuser)
        
    def validations(self, row):
        row['Code*'] = clean_string(row.get('Code*'), code=True)
        row['Name*'] = clean_string(row.get('Name*'))
        row['GPS Location'] = clean_point_field(row.get('GPS Location'))
        
        #check required fields
        if row.get('Code*') in  ['', None]:raise ValidationError("Code* is required field")
        if row.get('Name*') in  ['', None]:raise ValidationError("Name* is required field")
        if row.get('Identifier*') in  ['', None]:raise ValidationError("Identifier* is required field")
        if row.get('Running Status*') in  ['', None]:raise ValidationError("Running Status* is required field")
        
        # code validation
        regex, value = "^[a-zA-Z0-9\-_]*$", row['Code*']
        if " " in value: raise ValidationError("Please enter text without any spaces")
        if  not re.match(regex, value):
            raise ValidationError("Please enter valid text avoid any special characters except [_, -]")

        # unique record check
        if am.Asset.objects.select_related().filter(
            assetcode=row['Code*'],
            bu__bucode=row['Site*'],
            client__bucode = row['Client*']).exists():
            raise ValidationError(f"Record with these values already exist {row.values()}")
        
        if row.get('Service'):
            obj = om.TypeAssist.objects.filter(
                tacode=row['Service'], client__bucode=row['Client*']).first()
            if not obj:
                raise ValidationError(f"Service {row['Service']} does not exist")
            else:
                row['Service'] = obj.id
        
        if row.get('Meter'):
            obj = om.TypeAssist.objects.filter(
                tacode=row['Meter'], client__bucode=row['Client*']).first()
            if not obj:
                raise ValidationError(f"Meter {row['Meter']} does not exist")
            else:
                row['Meter'] = obj.id
            


class LocationResource(resources.ModelResource):
    Client = fields.Field(
        column_name = 'Client*',
        attribute   = 'client',
        widget      = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default     = utils.get_or_create_none_bv
    )
    BV = fields.Field(
        column_name       = 'Site*',
        attribute         = 'bu',
        widget            = BVForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default           = utils.get_or_create_none_bv
    )
    
    PARENT = fields.Field(
        column_name       = 'Belongs To*',
        attribute         = 'parent',
        widget            = wg.ForeignKeyWidget(am.Location, 'loccode'),
        saves_null_values = True,
        default=utils.get_or_create_none_location
    )
    
    Type = fields.Field(
        column_name       = 'Type*',
        attribute         = 'type',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True,
        default=default_ta
    )
    
    ID = fields.Field(attribute='id')
    ENABLE = fields.Field(attribute='enable', column_name='Enable', default=True)
    CODE = fields.Field(attribute='loccode', column_name='Code*')
    NAME = fields.Field(attribute='locname', column_name='Name*')
    RS = fields.Field(attribute='locstatus',column_name='Status*')
    ISCRITICAL = fields.Field(attribute='iscritical', column_name='Is Critical', default=False)
    GPS = fields.Field(attribute='gpslocation', column_name='GPS Location')
    
    class Meta:
        model = am.Location
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = ['CODE', 'NAME', 'PARENT', 'RS', 'ISCRITICAL', 'GPS', 'CLIENT', 'BV']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
    
    def before_import_row(self, row, row_number=None, **kwargs):
        row['Code*'] = clean_string(row.get('Code*'), code=True)
        row['Name*'] = clean_string(row.get('Name*'))
        row['GPS Location'] = clean_point_field(row.get('GPS Location'))
        
        #check required fields
        if row.get('Code*') in  ['', None]:raise ValidationError("Code* is required field")
        if row.get('Name*') in  ['', None]:raise ValidationError("Name* is required field")
        if row.get('Type*') in  ['', None]:raise ValidationError("Type* is required field")
        if row.get('Status*') in  ['', None]:raise ValidationError("Status* is required field")
        
        # code validation
        regex, value = "^[a-zA-Z0-9\-_]*$", row['Code*']
        if " " in value: raise ValidationError("Please enter text without any spaces")
        if  not re.match(regex, value):
            raise ValidationError("Please enter valid text avoid any special characters except [_, -]")

        # unique record check
        if am.Location.objects.select_related().filter(
            loccode=row['Code*'],
            client__bucode = row['Client*']).exists():
            raise ValidationError(f"Record with these values already exist {row.values()}")
        super().before_import_row(row, row_number, **kwargs)
        
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)
