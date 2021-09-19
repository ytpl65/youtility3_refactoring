from django.contrib import admin
from .models import People, PeopleEventlog, Pgroup, Pgbelonging, Capability
from import_export import resources
# Register your models here.

@admin.register(People)
class PeopleAdmin(admin.ModelAdmin):
    fields = ['peoplecode', 'peoplename', 'loginid', 'designation', 'department', 'mobno', 'email',
                    'reportto', 'dateofjoin', 'dateofreport', 'dateofbirth','gender', 'peopletype', 'isenable', 'isadmin', 'people_extras', 'clientid']
    
    list_display = ['peopleid','peoplecode', 'peoplename', 'loginid', 'designation', 'mobno', 'email',
                    'reportto', 'dateofjoin', 'gender', 'peopletype', 'isenable', 'isadmin', 'clientid']
    
    list_display_links = ['peoplecode', 'peoplename']


@admin.register(Pgroup)
class PgroupAdmin(admin.ModelAdmin):
    fields = ['groupid', 'groupname', 'enable', 'identifier', 'clientid', 'siteid']
    list_display = ['groupid', 'groupname', 'enable', 'identifier', 'clientid', 'siteid']
    list_display_links = ['groupname', 'enable', 'identifier']


@admin.register(Pgbelonging)
class PgbelongingAdmin(admin.ModelAdmin):
    fields = ['pgbid', 'groupid', 'peopleid', 'isgrouplead', 'assignsites', 'siteid', 'clientid']
    list_display = ['pgbid', 'groupid', 'peopleid', 'isgrouplead', 'assignsites', 'siteid']
    list_display_links = ['groupid', 'peopleid']


@admin.register(PeopleEventlog)
class PeopleEventlogAdmin(admin.ModelAdmin):
    fields = ['pelogid', 'peopleid', 'peventtype']

@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    fields = ['capscode', 'capsname', 'cfor', 'parent']

