from django.contrib import admin
from . models import TypeAssist

# Register your models here.
from .models import TypeAssist, Bt
# Register your models here.

@admin.register(TypeAssist)
class TypeAssistAdmin(admin.ModelAdmin):
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