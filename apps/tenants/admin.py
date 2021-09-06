from django.contrib import admin
from .models import Tenant

# Register your models here.
@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    fields = ('tenantname', 'subdomain_prefix')
    list_display = ('tenantname', 'subdomain_prefix', 'created_at')
    list_display_links =  ('tenantname', 'subdomain_prefix', 'created_at')