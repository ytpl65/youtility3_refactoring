from import_export import resources, fields
from import_export import widgets as wg
import apps.onboarding.models as om
import apps.activity.models as am
from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from django.db.utils import IntegrityError
from apps.core import utils
from import_export.results import RowResult



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
        column_name='Client',
        attribute='client',
        widget = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        default=utils.get_or_create_none_bv
    )

    ID      = fields.Field(attribute='id', column_name='ID')
    AlertON = fields.Field(attribute='alerton', column_name='Alert On')
    Options = fields.Field(attribute='options', column_name='Options')
    Name    = fields.Field(attribute='quesname', column_name='Name')
    Type    = fields.Field(attribute='answertype', column_name='Type')
    Min     = fields.Field(attribute='min', column_name='Min')
    Max     = fields.Field(attribute='max', column_name='Max')
    Enable  = fields.Field(attribute='enable', default=True)
    IsAvpt  = fields.Field(attribute='isavpt', column_name='Is AVPT', default=False, widget=wg.BooleanWidget())
    AttType = fields.Field(attribute='avpttype', column_name='AVPT Type', saves_null_values=True)

    class Meta:
        model = am.Question
        skip_unchanged = True
        import_id_fields = ('Name', 'Type', 'Client',)
        report_skipped = True
        fields = ['Name', 'Type',  'Unit', 'Options',  'Enable', 'IsAvpt', 'AttType',
                  'Client', 'Min', 'Max', 'AlertON', 'isworkflow', 'Category']
    
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(QuestionResource, self).__init__(*args, **kwargs)
    
    
    def before_save_instance(self, instance, using_transactions, dry_run):
        """
        Perform any necessary actions before saving the instance.
        Handle the IntegrityError exception explicitly.
        """
        try:
            utils.save_common_stuff(self.request, instance)
        except IntegrityError as e:
            pass


@admin.register(am.Question)
class QuestionAdmin(ImportExportModelAdmin):
    resource_class = QuestionResource
    list_display = ['id','quesname']
    
    def get_resource_kwargs(self, request, *args, **kwargs):
        return {'request': request}
    
    def get_queryset(self, request):
        return am.Question.objects.select_related().all()
    
    
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

