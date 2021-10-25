from django.contrib import admin
from .models import People, PeopleEventlog, Pgroup, Pgbelonging, Capability
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export import widgets as wg
from apps.peoples import models as pm


from apps.onboarding.admin import TaResource

# Register your models here.


@admin.register(People)
class PeopleAdmin(admin.ModelAdmin):
    fields = ['peoplecode', 'peoplename', 'loginid', 'designation', 'department', 'mobno', 'email',
              'reportto', 'dateofjoin', 'dateofreport', 'dateofbirth', 'gender', 'peopletype', 'isenable', 'isadmin', 'people_extras', 'clientid']

    list_display = ['id', 'peoplecode', 'peoplename', 'loginid', 'designation', 'mobno', 'email',
                    'reportto', 'dateofjoin', 'gender', 'peopletype', 'isenable', 'isadmin', 'clientid']

    list_display_links = ['peoplecode', 'peoplename']


@admin.register(Pgroup)
class PgroupAdmin(admin.ModelAdmin):
    fields = ['id', 'groupname', 'enable',
              'identifier', 'clientid', 'siteid']
    list_display = ['id', 'groupname',
                    'enable', 'identifier', 'clientid', 'siteid']
    list_display_links = ['groupname', 'enable', 'identifier']


@admin.register(Pgbelonging)
class PgbelongingAdmin(admin.ModelAdmin):
    fields = ['id', 'groupid', 'peopleid',
              'isgrouplead', 'assignsites', 'siteid', 'clientid']
    list_display = ['id', 'groupid', 'peopleid',
                    'isgrouplead', 'assignsites', 'siteid']
    list_display_links = ['groupid', 'peopleid']


@admin.register(PeopleEventlog)
class PeopleEventlogAdmin(admin.ModelAdmin):
    fields = ['id', 'peopleid', 'peventtype']


class CapabilityResource(resources.ModelResource):
    cuser = fields.Field(
        column_name = 'cuser',
        attribute   = 'cuser',
        widget      = wg.ForeignKeyWidget(pm.People, 'peoplecode'))
    
    muser = fields.Field(
        column_name = 'muser',
        attribute   = 'muser',
        widget      = wg.ForeignKeyWidget(pm.People, 'peoplecode'))
    
    class Meta:
        model = Capability
        skip_unchanged = True
        report_skipped = True
        fields = ('id', 'capscode',  'capsname', 'cfor',
        'parent','cuser', 'muser')


@admin.register(Capability)
class CapabilityAdmin(ImportExportModelAdmin):
    resource_class      = CapabilityResource
    fields              = ['capscode', 'capsname', 'cfor', 'parent']
    list_display        = ['capscode', 'capsname', 'cfor', 'parent',
                        'cdtz', 'mdtz', 'cuser', 'muser']
    list_display_links  = ['capscode', 'capsname']


    def get_queryset(self, request):
        print(super(CapabilityAdmin,self).get_queryset(request))
        return super(CapabilityAdmin,self).get_queryset(request).select_related('cuser', 'muser')
