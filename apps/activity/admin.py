from unicodedata import category
from import_export import resources, fields
from import_export import widgets as wg
import apps.onboarding.models as om
import apps.activity.models as am
from apps.onboarding.admin import BaseFieldSet2

# Register your models here.

class QuestionResource(resources.ModelResource):
    Unit = fields.Field(
        column_name       = 'Unit',
        attribute         = 'unit',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )
    Category = fields.Field(
        column_name       = 'Category',
        attribute         = 'category',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )
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
    ID         = fields.Field(attribute='id')
    AlertON    = fields.Field(attribute='alerton', column_name='Alert On')
    Options    = fields.Field(attribute='options', column_name='Options')
    Name       = fields.Field(attribute='quesname')
    Type       = fields.Field(attribute='answertype')
    Min        = fields.Field(attribute='min')
    Max        = fields.Field(attribute='max')
    Enable     = fields.Field(attribute='enable')
    isworkflow = fields.Field(attribute='isworkflow', column_name="Is Work Flow")

    class Meta:
        model = am.Question
        skip_unchanged = True
        import_id_fields = ('ID', 'Name', 'Type', 'Client')
        report_skipped = True
        fields = ('ID', 'Name', 'Type',  'Unit', 'Options', 'BV', 'Enable',
                  'Client', 'Min', 'Max', 'AlertON', 'isworkflow', 'Category')

class AssetResource(resources.ModelResource):
    Client = fields.Field(
        column_name = 'Client',
        attribute   = 'client',
        widget      = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default     = 'NONE'
    )
    BV = fields.Field(
        column_name       = 'BV',
        attribute         = 'bu',
        widget            = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True,
        default           = 'NONE'
    )
    Unit = fields.Field(
        column_name       = 'Unit',
        attribute         = 'unit',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )
    Category = fields.Field(
        column_name       = 'Category',
        attribute         = 'category',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )
    Brand = fields.Field(
        column_name       = 'Brand',
        attribute         = 'brand',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )

    ServiceProvider = fields.Field(
        column_name       = 'Service Provider',
        attribute         = 'serv_prov',
        widget            = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True
    )

    SubCategory = fields.Field(
        column_name       = 'Sub Category',
        attribute         = 'subcategory',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )

    BelongsTo = fields.Field(
        column_name       = 'Belongs To',
        attribute         = 'parent',
        widget            = wg.ForeignKeyWidget(am.Asset, 'tacode'),
        saves_null_values = True
    )
    
    Type = fields.Field(
        column_name       = 'Asset Type',
        attribute         = 'type',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )
    Identifier    = fields.Field(attribute='identifier')
    ID            = fields.Field(attribute='id')
    Code          = fields.Field(attribute='assetcode')
    Name          = fields.Field(attribute='assetname')
    RunningStatus = fields.Field(attribute='runningstatus', column_name='Running Status')
    Capacity      = fields.Field(widget=wg.DecimalWidget(), column_name='Capacity', attribute='capacity')
    GPS           = fields.Field(attribute='gpslocation')
    
    
    class Meta:
        model = am.Asset
        skip_unchanged = True
        import_id_fields = ('ID', 'Code', 'Name', 'Client')
        report_skipped = True
        fields = ('ID', 'Code', 'Name',  'GPS', 'Identifier'
                  'RunningStatus', 'Capacity', 'BelongsTo', 'Type', 'Client', 'BV',
                  'Category', 'SubCategory', 'Brand', 'Unit', 'ServiceProvider')

