from django.contrib import admin
from import_export import resources, fields
from import_export import widgets as wg
from import_export.admin import ImportExportModelAdmin

from apps.peoples import models as pm
from .forms import (BtForm, TypeAssistForm, BuPrefForm, SitePeopleForm,
                    ContractDetailForm, ContractForm)
from . models import TypeAssist, Bt


class TaResource(resources.ModelResource):
    cuser = fields.Field(
        column_name='cuser',
        attribute='cuser',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'))
    
    muser = fields.Field(
        column_name='muser',
        attribute='muser',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'))
    
    class Meta:
        model = TypeAssist
        skip_unchanged = True
        import_id_fields = ('id',)
        report_skipped = True
        fields = ('id', 'taname', 'tacode','tatype', 'parent', 'cuser', 'muser',)

from import_export.admin import ImportExportModelAdmin

class TaAdmin(ImportExportModelAdmin):
    resource_class = TaResource
    list_display = ('id', 'tacode', 'tatype', 'parent', 'cdtz', 'mdtz', 'cuser', 'muser')

admin.site.register(TypeAssist, TaAdmin)




class BtResource(resources.ModelResource):
    cuser = fields.Field(
        column_name='cuser',
        attribute='cuser',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'))
    
    muser = fields.Field(
        column_name='muser',
        attribute='muser',
        widget=wg.ForeignKeyWidget(pm.People, 'peoplecode'))


    class Meta:
        model = Bt
        skip_unchanged = True
        import_id_fields = ('id',)
        report_skipped = True
        fields = ('id', 'buname', 'bucode','butype', 'identifier', 'parent', 'cuser', 'muser',)




@admin.register(Bt)
class BtAdmin(ImportExportModelAdmin):
    form = BtForm
    resource_class  = BtResource
    fields = ('bucode',  'buname', 'butype', 'parent', 'gpslocation', 'identifier',
              'iswarehouse', 'enable', 'bu_preferences')
    exclude = ['bupath']
    list_display = ('bucode', 'id', 'buname', 'butype', 'identifier','parent', 'butree')
    list_display_links = ('bucode',)


