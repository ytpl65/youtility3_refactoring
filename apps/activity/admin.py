from unicodedata import category
from import_export import resources, fields
from import_export import widgets as wg
import apps.onboarding.models as om
import apps.activity.models as am
from apps.onboarding.admin import BaseFieldSet2

# Register your models here.

class QuestionResource(BaseFieldSet2, resources.ModelResource):
    unit = fields.Field(
        column_name       = 'unit',
        attribute         = 'unit',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )
    category = fields.Field(
        column_name       = 'category',
        attribute         = 'category',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )

    class Meta:
        model = am.Question
        skip_unchanged = True
        import_id_fields = ('id', 'quesname', 'answertype', 'client')
        report_skipped = True
        fields = ('id', 'quesname', 'answertype',  'unit', 'options'
                  'client', 'min', 'max', 'alerton', 'isworkflow', 'enable', 'category')

class AssetResource(BaseFieldSet2, resources.ModelResource):
    unit = fields.Field(
        column_name       = 'unit',
        attribute         = 'unit',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )
    category = fields.Field(
        column_name       = 'category',
        attribute         = 'category',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )

    serv_prov = fields.Field(
        column_name       = 'serv_prov',
        attribute         = 'serv_prov',
        widget            = wg.ForeignKeyWidget(om.Bt, 'bucode'),
        saves_null_values = True
    )

    subcategory = fields.Field(
        column_name       = 'subcategory',
        attribute         = 'subcategory',
        widget            = wg.ForeignKeyWidget(om.TypeAssist, 'tacode'),
        saves_null_values = True
    )

    parent = fields.Field(
        column_name       = 'parent',
        attribute         = 'parent',
        widget            = wg.ForeignKeyWidget(am.Asset, 'tacode'),
        saves_null_values = True
    )
    type = fields.Field(
        column_name       = 'type',
        attribute         = 'type',
        widget            = wg.ForeignKeyWidget(am.Asset, 'tacode'),
        saves_null_values = True
    )

    class Meta:
        model = am.Asset
        skip_unchanged = True
        import_id_fields = ('id', 'assetcode', 'answertype', 'client')
        report_skipped = True
        fields = ('id', 'assetcode', 'assetname',  'gpslocation', 'identifier'
                  'runningstatus', 'capacity', 'parent', 'type', 'client', 'bu',
                  'category', 'subcategory', 'brand', 'unit', 'serv_prov')

