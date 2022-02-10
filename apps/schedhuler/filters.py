from cProfile import label
import django_filters as dfs
import apps.activity.models as am
from django.db.models import Q
import django_filters.widgets as wg
import django_select2.forms as s2forms

def assigned_to_qs(queryset, name, value):
        return queryset.filter(Q(aaatop__peoplename__icontains=value) | Q(groupid__groupname__icontains=value))
    
###################### JOB FILTER #########################
class JobFilter(dfs.FilterSet):
    class Meta:
        model  = am.Job
        fields = [
            'jobname',    'jobdesc',      'from_date',       'upto_date',  'cron',
            'identifier', 'planduration', 'gracetime',       'expirytime', 'parent',
            'assetid',    'priority',     'qsetid',          'groupid',    'gfid', 
            'parent',     'slno',         'clientid',        'buid',       'starttime', 
            'frequency',  'scantype',     'ticket_category', 'peopleid',   'shift',
            'endtime',    'ctzoffset',    
        ]
        
        
class JobneedFilter(dfs.FilterSet):
    class Meta:
        model = am.Jobneed
        fields = [
            'identifier', 'frequency',    'parent',         'jobdesc',   'assetid', 'ticket_category',
            'qsetid',     'peopleid',     'groupid',        'priority',  'scantype', 'ticketno',
            'jobstatus',  'plandatetime', 'expirydatetime', 'gracetime', 'starttime', 'cdtz',
            'endtime',    'performed_by', 'gpslocation',    'cuser',     'muser',     'raisedby',
            'buid',              
        ]
    
    
class SchdTourFilter(JobFilter):
    jobname      = dfs.CharFilter(field_name='jobname', lookup_expr='icontains', label='Name')
    assignedto   = dfs.CharFilter(method=assigned_to_qs, label='People/Group')
    planduration = dfs.CharFilter(field_name='planduration', lookup_expr='icontains', label='Duration')
    expirytime   = dfs.CharFilter(field_name='expirytime', lookup_expr='icontains', label='Exp Time')
    gracetime    = dfs.CharFilter(field_name='gracetime', lookup_expr='icontains', label='Grace Time')
    from_date    = dfs.DateTimeFilter(field_name='from_date', lookup_expr='icontains', label='From')
    upto_date    = dfs.DateTimeFilter(field_name='upto_date', lookup_expr='icontains', label='To')
    
    class Meta(JobFilter.Meta):
        exclude = ['endtime','cron','clientid','ticket_category','parent','slno','frequency','groupid','starttime','buid',
                   'priority','ctzoffset','gfid','identifier','peopleid','shift','jobdesc','scantype','assignedto']


class SchdExtTourFilter(SchdTourFilter):
    buid = dfs.CharFilter(field_name='buid__buname', lookup_expr='icontains', label= "BV")
    
    class Meta(SchdTourFilter.Meta):
        fields = ['jobname',  'buid', 'assignedto', 'planduration', 'expirytime', 'gracetime', 'from_date', 'upto_date']
        exclude = ['assetid']


class SchdTaskFilter(SchdTourFilter):
    assetid        = dfs.CharFilter(field_name='asset__assetname', lookup_expr='icontains', label= "Asset")
    class Meta(SchdTourFilter.Meta):
        fields = ['jobname',  'assetid', 'qsetid', 'assignedto', 'planduration', 'expirytime', 'gracetime', 'from_date', 'upto_date']
        
        
class InternalTourFilter(dfs.FilterSet):
    JOBSTATUSCHOICES = [
        ('ASSIGNED', 'Assigned'),
        ('AUTOCLOSED', 'Auto Closed'),
        ('COMPLETED', 'Completed'),
        ('INPROGRESS', 'Inprogress'),
        ('PARTIALLYCOMPLETED', 'Partially Completed')
    ]
    plandatetime   = dfs.DateFromToRangeFilter(widget=wg.RangeWidget(attrs={'placeholder': 'YYYY/MM/DD'}))
    jobdesc        = dfs.CharFilter(field_name='jobdesc', lookup_expr='icontains', label='Description')
    jobstatus      = dfs.ChoiceFilter(field_name='jobstatus', choices = JOBSTATUSCHOICES, label="Stauts", widget = s2forms.Select2Widget)
    assignedto     = dfs.CharFilter( method=assigned_to_qs, label='People/Group')
    gracetime      = dfs.CharFilter(field_name='gracetime', lookup_expr='icontains', label='Grace Time')
    performed_by   = dfs.CharFilter(field_name='performed_by', lookup_expr='icontains', label='Performed By')
    expirydatetime = dfs.DateTimeFilter(field_name='expirydatetime', label="Exp. Datetime")
    
    class Meta:
        model = am.Jobneed
        fields = [ 'plandatetime', 'jobdesc', 'jobstatus', 'assignedto', 'gracetime', 'performed_by', 'expirydatetime']

    def __init__(self, *args, **kwargs):
        super(InternalTourFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'radioselect', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            if visible.widget_type == 'checkbox':
                visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            if visible.widget_type in ['select2', 'modelselect2', 'select2multiple']:
                visible.field.widget.attrs['class'] = 'form-select'
                visible.field.widget.attrs['data-placeholder'] = 'Select an option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'


class TaskListJobneedFilter(InternalTourFilter):
    assetid = dfs.CharFilter(field_name='assetid__assetname', lookup_expr='icontains', label='Asset/Smartplace')
    qsetid = dfs.CharFilter(field_name='qsetid__qset_name', lookup_expr='icontains', label='QuestionSetz')
    buid = dfs.CharFilter(field_name= 'buid__buname', lookup_expr='icontains')
    jobdesc = dfs.CharFilter(field_name='jobdesc', lookup_expr='icontains', label='Description')


class TicketListFilter(JobneedFilter):
    TICKETSTATUS = [
        ("RESOLVED",  "Resolved"),
        ("OPEN",      "Open"),
        ("CANCELLED", "Cancelled"),
        ("ESCALATED", "Escalated"),
        ("NEW",       "New")
    ]
    cdtz            = dfs.DateTimeFilter(field_name='cdtz', lookup_expr='contains')
    ticketno        = dfs.NumberFilter(field_name='ticketno', lookup_expr='contains')
    assignedto      = dfs.CharFilter(method=assigned_to_qs, label='People/Group')
    performed_by    = dfs.CharFilter(field_name='performed_by__peoplename', lookup_expr='icontains')
    ticket_category = dfs.CharFilter(field_name='ticket_category__taname', lookup_expr='icontains')
    jobstatus       = dfs.ChoiceFilter(field_name='jobstatus', choices = TICKETSTATUS, label="Stauts", widget = s2forms.Select2Widget)
    cuser           = dfs.CharFilter(field_name='cuser__peoplename', lookup_expr='icontains')
    
    
    class Meta(JobneedFilter.Meta):
        fields = ['cdtz', 'cuser', 'ticketno', 'buid', 'assignedto', 'performed_by', 'ticket_category', 'jobstatus']
        
    def __init__(self, *args, **kwargs):
        super(TicketListFilter, self).__init__(*args, **kwargs)
        for visible in self.form.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'radioselect', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            if visible.widget_type == 'checkbox':
                visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            if visible.widget_type in ['select2', 'modelselect2', 'select2multiple']:
                visible.field.widget.attrs['class'] = 'form-select'
                visible.field.widget.attrs['data-placeholder'] = 'Select an option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'