from import_export import resources, fields, widgets as wg
from apps.activity.models import Job
from import_export.admin import ImportExportModelAdmin
from django.db.models import Q
from django.contrib import admin
from apps.service.validators import (
    clean_array_string, clean_code, clean_point_field, clean_string, validate_cron
)
from django.core.exceptions import ValidationError
from apps.peoples import models as pm
from apps.onboarding import models as om
from apps.activity import models as am
from apps.core.widgets import BVForeignKeyWidget
from datetime import time

from apps.core import utils

def default_ta():
    return utils.get_or_create_none_typeassist()[0]

class PeopleFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return pm.People.objects.select_related().filter(
            client__bucode = row['Client*']
        )

class PgroupFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return pm.Pgroup.objects.select_related().filter(
            (Q(client__bucode = row['Client*']) & Q(enable=True)) | 
            Q(groupname='NONE')
        )
class QsetFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return am.QuestionSet.objects.select_related().filter(
            client__bucode = row['Client*'], enable=True
        )
class AssetFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return am.Asset.objects.select_related().filter(
            client__bucode = row['Client*'], enable=True
        )
class TktCategoryFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        return om.TypeAssist.objects.select_related().filter(
            tatype__tacode="NOTIFYCATEGORY"
        )
        
class ParentFKW(wg.ForeignKeyWidget):
    def get_queryset(self, value, row, *args, **kwargs):
        qset = am.Job.objects.select_related().filter(
            (Q(client__bucode = row['Client*']) & Q(enable=True)) |
            Q(jobname='NONE'), identifier='INTERNALTOUR'
        )
        print("possible job rows",qset.values_list("jobname", flat=True).order_by('-cdtz'))
        return qset

class BaseJobResource(resources.ModelResource):
    CLIENT      = fields.Field(attribute='client', column_name='Client*',widget=wg.ForeignKeyWidget(om.Bt, 'bucode'))
    SITE        = fields.Field(attribute='bu', column_name='Site*',widget=BVForeignKeyWidget(om.Bt, 'bucode'))
    NAME        = fields.Field(attribute='jobname', column_name='Name*')
    DESC        = fields.Field(attribute='jobdesc', column_name='Description*')
    QSET        = fields.Field(attribute='qset', column_name='Question Set/Checklist*', widget=QsetFKW(am.QuestionSet, 'qsetname'))
    ASSET       = fields.Field(attribute='asset', column_name='Asset*', widget=AssetFKW(am.Asset, 'assetcode'))
    PARENT      = fields.Field(attribute='parent', column_name='Belongs To*', widget=wg.ForeignKeyWidget(am.Job, 'jobname'), default=utils.get_or_create_none_job)
    PDURATION   = fields.Field(attribute='planduration', column_name='Plan Duration*')
    GRACETIME   = fields.Field(attribute='gracetime', column_name='Gracetime Before*')
    EXPTIME     = fields.Field(attribute='expirytime', column_name='Gracetime After*')
    CRON        = fields.Field(attribute='cron', column_name='Scheduler*')
    FROMDATE    = fields.Field(attribute='fromdate', column_name='From Date*', widget=wg.DateWidget())
    UPTODATE    = fields.Field(attribute='uptodate', column_name='Upto Date*', widget=wg.DateWidget())
    SCANTYPE    = fields.Field(attribute='scantype', column_name='Scan Type*', default='QR')
    TKTCATEGORY = fields.Field(attribute='ticketcategory', column_name='Notify Category*', widget=TktCategoryFKW(om.TypeAssist, 'tacode'), default=default_ta)
    PRIORITY    = fields.Field(attribute='priority', column_name='Priority*', default='LOW')
    PEOPLE      = fields.Field(attribute='people', column_name='People*', widget= PeopleFKW(pm.People, 'peoplecode'))
    PGROUP      = fields.Field(attribute='pgroup', column_name='Group Name*', widget=PgroupFKW(pm.Pgroup, 'groupname'))
    IDF         = fields.Field(attribute='identifier', column_name='Identifier*')
    STARTTIME   = fields.Field(attribute='starttime', column_name='Start Time', default=time(0,0,0))
    ENDTIME     = fields.Field(attribute='endtime', column_name='End Time', default=time(0,0,0))
    SEQNO       = fields.Field(attribute='seqno', column_name='Seq No', default=-1)
    ID          = fields.Field(attribute='id', column_name='ID')
    
    class Meta:
        model = Job
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
    

    
   


class TaskResource(BaseJobResource):
    IDF         = fields.Field(attribute='identifier', column_name='Identifier*', default='TASK')
    class Meta:
        model = Job
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = [
            'CLIENT', 'SITE', 'NAME', 'DESC', 'QSET', 'PDURATION', 'GRACETIME', 'EXPTIME',
            'CRON', 'FROMDATE', 'UPTODATE', 'SCANTYPE', 'TKTCATEGORY', 'PRIORITY', 'PEOPLE',
            'PGROUP', 'IDF', 'STARTTIME', 'ENDTIME', 'SEQNO', 'PARENT'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        self.ctzoffset = kwargs.pop('ctzoffset', -1)
        
    
    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.validate_row(row)
        self.unique_record_check(row)
        super().before_import_row(row, **kwargs)
        
    def check_required_fields(self, row):
        required_fields = [
            'Name*', 'Description*', 'From Date*', 'Upto Date*', 'Scheduler*',
            'Notify Category*', 'Plan Duration*', 'Gracetime Before*', 'Gracetime After*',
            'Question Set/Checklist*', 'Asset*', 'Priority*', 'People*', 'Group Name*', 'Belongs To*']
        ic(row.get('Plan Duration*'))
        for field in required_fields:
            if not row.get(field):
                raise ValidationError({field: f"{field} is a required field"})
    
    def validate_row(self, row):
        row['Name*'] = clean_string(row['Name*'])
        row['Description*'] = clean_string(row['Description*'])
        row['Plan Duration*'] = int(row['Plan Duration*'])
        row['Gracetime Before*'] = int(row['Gracetime Before*'])
        row['Gracetime After*'] = int(row['Gracetime After*'])
        # check valid cron
        if not validate_cron(row['Scheduler*']):
            raise ValidationError({
                'Scheduler*': "Invalid value or Problematic Cron Expression for scheduler"
            })
    
    def unique_record_check(self, row):
        if Job.objects.filter(
            jobname = row['Name*'], asset__assetcode = row['Asset*'], qset__qsetname = row['Question Set/Checklist*'],
            identifier = 'TASK', client__bucode = row['Client*']
        ).exists():
            raise ValidationError('Record Already with these values are already exist')
    
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser, self.ctzoffset)



class TourResource(resources.ModelResource):
    CLIENT      = fields.Field(attribute='client', column_name='Client*',widget=wg.ForeignKeyWidget(om.Bt, 'bucode'), default=utils.get_or_create_none_bv)
    SITE        = fields.Field(attribute='bu', column_name='Site*',widget=BVForeignKeyWidget(om.Bt, 'bucode'))
    NAME        = fields.Field(attribute='jobname', column_name='Name*')
    DESC        = fields.Field(attribute='jobdesc', column_name='Description*')
    QSET        = fields.Field(attribute='qset', column_name='Question Set/Checklist*', widget=QsetFKW(am.QuestionSet, 'qsetname'))
    ASSET       = fields.Field(attribute='asset', column_name='Asset*', widget=AssetFKW(am.Asset, 'assetcode'))
    PARENT      = fields.Field(attribute='parent', column_name='Belongs To*', widget=wg.ForeignKeyWidget(am.Job, 'jobname'), default=utils.get_or_create_none_job)
    PDURATION   = fields.Field(attribute='planduration', column_name='Plan Duration*')
    GRACETIME   = fields.Field(attribute='gracetime', column_name='Gracetime Before*')
    EXPTIME     = fields.Field(attribute='expirytime', column_name='Gracetime After*')
    CRON        = fields.Field(attribute='cron', column_name='Scheduler*')
    FROMDATE    = fields.Field(attribute='fromdate', column_name='From Date*', widget=wg.DateWidget())
    UPTODATE    = fields.Field(attribute='uptodate', column_name='Upto Date*', widget=wg.DateWidget())
    SCANTYPE    = fields.Field(attribute='scantype', column_name='Scan Type*', default='QR')
    TKTCATEGORY = fields.Field(attribute='ticketcategory', column_name='Notify Category*', widget=TktCategoryFKW(om.TypeAssist, 'tacode'), default=default_ta)
    PRIORITY    = fields.Field(attribute='priority', column_name='Priority*', default='LOW')
    PEOPLE      = fields.Field(attribute='people', column_name='People*', widget= PeopleFKW(pm.People, 'peoplecode'))
    PGROUP      = fields.Field(attribute='pgroup', column_name='Group Name*', widget=PgroupFKW(pm.Pgroup, 'groupname'))
    IDF         = fields.Field(attribute='identifier', column_name='Identifier*', default='INTERNALTOUR')
    STARTTIME   = fields.Field(attribute='starttime', column_name='Start Time', default=time(0,0,0))
    ENDTIME     = fields.Field(attribute='endtime', column_name='End Time', default=time(0,0,0))
    SEQNO       = fields.Field(attribute='seqno', column_name='Seq No', default=-1)
    ID          = fields.Field(attribute='id', column_name='ID')

    class Meta:
        model = am.Job
        skip_unchanged = True
        import_id_fields = ['ID']
        report_skipped = True
        fields = [
            'CLIENT', 'SITE', 'NAME', 'DESC', 'QSET', 'PDURATION', 'GRACETIME', 'EXPTIME',
            'CRON', 'FROMDATE', 'UPTODATE', 'SCANTYPE', 'TKTCATEGORY', 'PRIORITY', 'PEOPLE',
            'PGROUP', 'IDF', 'STARTTIME', 'ENDTIME', 'SEQNO', 'PARENT', 'ASSET'
        ]
    
    def __init__(self, *args, **kwargs):
        super(TourResource, self).__init__(*args, **kwargs)
        self.is_superuser = kwargs.pop('is_superuser', None)
        self.request = kwargs.pop('request', None)
        self.ctzoffset = kwargs.pop('ctzoffset', -1)
        
    
    def before_import_row(self, row, row_number, **kwargs):
        self.check_required_fields(row)
        self.validate_row(row)
        self.unique_record_check(row)
        super().before_import_row(row, **kwargs)
        
    def check_required_fields(self, row):
        required_fields = [
            'Name*', 'Description*', 'From Date*', 'Upto Date*', 'Scheduler*',
            'Notify Category*', 'Plan Duration*', 'Expiry Time*', 'Gracetime*', 'Seq No*',
            'Question Set/Checklist*', 'Asset*', 'Priority*', 'People*', 'Group Name*', 'Belongs To*']
        for field in required_fields:
            if not row.get(field):
                raise ValidationError({field: f"{field} is a required field"})
    
    def validate_row(self, row):
        row['Name*'] = clean_string(row['Name*'])
        row['Description*'] = clean_string(row['Description*'])
        row['Plan Duration*'] = int(row['Plan Duration*'])
        row['Gracetime*'] = int(row['Gracetime*'])
        row['Expiry Time*'] = int(row['Expiry Time*'])
        row['Seq No*'] = int(row['Seq No*'])
        # check valid cron
        if not validate_cron(row['Scheduler*']):
            raise ValidationError({
                'Scheduler*': "Invalid value or Problematic Cron Expression for scheduler"
            })
    
    def unique_record_check(self, row):
        if Job.objects.filter(
            jobname = row['Name*'], asset__assetcode = row['Asset*'], qset__qsetname = row['Question Set/Checklist*'],
            identifier = 'INTERNALTOUR', client__bucode = row['Client*']
        ).exists():
            raise ValidationError('Record Already with these values are already exist')
    
    def before_save_instance(self, instance, using_transactions, dry_run=False):
        utils.save_common_stuff(self.request, instance, self.is_superuser)