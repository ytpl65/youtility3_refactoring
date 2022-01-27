from cProfile import label
import django_filters as dfs
import apps.activity.models as am
from django.db.models import Q
import django_filters.widgets as wg
import django_select2.forms as s2forms

def assigned_to_qs(queryset, name, value):
        return queryset.filter(Q(aaatop__peoplename__icontains=value) | Q(groupid__groupname__icontains=value))

class SchdTourFilter(dfs.FilterSet):
    jobname   = dfs.CharFilter(field_name='jobname', lookup_expr='icontains', label='Name')
    assignedto = dfs.CharFilter(method=assigned_to_qs, label='People/Group')
    planduration = dfs.CharFilter(field_name='planduration', lookup_expr='icontains', label='Duration')
    expirytime = dfs.CharFilter(field_name='expirytime', lookup_expr='icontains', label='Exp Time')
    gracetime = dfs.CharFilter(field_name='gracetime', lookup_expr='icontains', label='Grace Time')
    from_date = dfs.DateTimeFilter(field_name='from_date', lookup_expr='icontains', label='From')
    upto_date = dfs.DateTimeFilter(field_name='upto_date', lookup_expr='icontains', label='To')
    
    class Meta:
        model = am.Job
        fields = ['jobname', 'assignedto', 'planduration', 'expirytime', 'gracetime', 'from_date', 'upto_date']

class SchdExtTourFilter(SchdTourFilter):
    buid = dfs.CharFilter(field_name='buid__buname', lookup_expr='icontains', label= "BV")
    
    class Meta(SchdTourFilter.Meta):
        fields = ['jobname',  'buid', 'assignedto', 'planduration', 'expirytime', 'gracetime', 'from_date', 'upto_date']
        
        
    
        
class InternalTourFilter(dfs.FilterSet):
    JOBSTATUSCHOICES = [
        ('ASSIGNED', 'Assigned'),
        ('AUTOCLOSED', 'Auto Closed'),
        ('COMPLETED', 'Completed'),
        ('INPROGRESS', 'Inprogress'),
        ('PARTIALLYCOMPLETED', 'Partially Completed')
    ]
    plandatetime = dfs.DateFromToRangeFilter(widget=wg.RangeWidget(attrs={'placeholder': 'YYYY/MM/DD'}))
    jobdesc  = dfs.CharFilter(field_name='jobdesc', lookup_expr='icontains', label='Description')
    jobstatus    = dfs.ChoiceFilter(field_name='jobstatus', choices = JOBSTATUSCHOICES, label="Stauts", widget = s2forms.Select2Widget)
    assignedto   = dfs.CharFilter( method=assigned_to_qs, label='People/Group')
    gracetime    = dfs.CharFilter(field_name='gracetime', lookup_expr='icontains', label='Grace Time')
    performed_by = dfs.CharFilter(field_name='performed_by', lookup_expr='icontains', label='Performed By')
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