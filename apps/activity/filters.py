import django_filters
import apps.activity.models as am

class QuestionFilter(django_filters.FilterSet):
    ques_name   = django_filters.CharFilter(field_name='ques_name', lookup_expr='icontains', label='Name')
    answertype = django_filters.CharFilter(field_name='answertype', lookup_expr='icontains', label='Type')
    unit       = django_filters.CharFilter(field_name='unit__tacode', lookup_expr='icontains', label='Unit')
    isworkflow = django_filters.CharFilter(field_name='isworkflow', lookup_expr='icontains', label='Is WorkFlow')
    
    class Meta:
        model = am.Question
        fields = ['ques_name', 'answertype', 'unit', 'isworkflow']



class ChecklistFilter(django_filters.FilterSet):
    qset_name   = django_filters.CharFilter(field_name='qset_name', lookup_expr='icontains', label='Name')
    
    class Meta:
        model = am.QuestionSet
        fields = ['qset_name']
        

class CheckpointFilter(django_filters.FilterSet):
    assetcode   = django_filters.CharFilter(field_name='assetcode', lookup_expr='icontains', label='Code')
    assetname = django_filters.CharFilter(field_name='assetname', lookup_expr='icontains', label='Name')
    parent       = django_filters.CharFilter(field_name='parent__assetcode', lookup_expr='icontains', label='Belongs To')
    runningstatus = django_filters.CharFilter(field_name='runningstatus', lookup_expr='icontains', label='Status')
    enable = django_filters.CharFilter(field_name='enable', lookup_expr='icontains', label='Enable')
    gpslocation = django_filters.CharFilter(field_name='gpslocation', lookup_expr='icontains', label='GPS Location')
    
    class Meta:
        model = am.Question
        fields = ['assetcode', 'assetname', 'parent', 'runningstatus','enable', 'gpslocation']