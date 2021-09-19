from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .forms import (BtForm, TypeAssistForm, BuPrefForm, SitePeopleForm,
ContractDetailForm, ContractForm)
from . models import TypeAssist, Bt 
<<<<<<< HEAD

class TypeAssistResource(resources.ModelResource):
    model = TypeAssist
    import_id_fields = ('taid',)
    fields = ('taid', 'tacode', 'taname', 'parent')
=======

class TypeAssistResource(resources.ModelResource):
    model = TypeAssist
    skip_unchanged = True
    report_skipped = True
    exclude = ('id')
    import_id_fields = ('taid', 'tacode', 'taname', 'parent', 'tatype')   
    #fields = ('taid', 'tacode', 'taname', 'parent', 'tatype')   

>>>>>>> 2a6630e5db63f4d43871c0904a0c63d2a6dfe88b

@admin.register(TypeAssist)
class TypeAssistAdmin(ImportExportModelAdmin):
    resource_class = TypeAssistResource
    fields = ('tacode', 'taname', 'tatype', 'parent', 'buid',)
    list_display = ('tacode', 'taname', 'tatype', 'parent',)
    list_display_links = ('tacode',)


@admin.register(Bt)
class BtAdmin(admin.ModelAdmin):
    fields = ('bucode', 'buname', 'butype', 'parent', 'gpslocation', 'identifier',
                'iswarehouse', 'enable', 'bu_preferences')
    exclude = ['bupath']
    list_display = ('bucode', 'buname', 'butype', 'parent', 'butree')
    list_display_links = ('bucode',)