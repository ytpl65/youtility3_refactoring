from django import forms
from apps.activity import models as am
from apps.onboarding import models as om
from apps.peoples import models as pm
from apps.core import utils
from django_select2 import forms as s2forms
from django.db.models import Q

class MasterReportTemplate(forms.ModelForm):
    required_css_class = "required"
    showto_allsites    = forms.BooleanField(initial = False, required = False, label='Show to all sites')
    site_type_includes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label="Site Types", required=False)
    buincludes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label='Site Includes', required=False)
    site_grp_includes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label='Site groups', required=False)


    class Meta:
        model = am.QuestionSet
        fields = [
            'type',  'qsetname', 'buincludes', 'site_grp_includes', 
            'site_type_includes', 'enable', 'ctzoffset']
        labels = {
            'qsetname':'Template Name',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['site_type_includes'].choices = om.TypeAssist.objects.filter(Q(tatype__tacode = "SITETYPE") | Q(tacode='NONE')).values_list('id', 'taname')
        bulist = om.Bt.objects.get_all_sites_of_client(self.request.session['client_id']).values_list('id', flat=True)
        self.fields['buincludes'].choices = pm.Pgbelonging.objects.get_assigned_sites_to_people(self.request.user.id, makechoice=True)
        self.fields['site_grp_includes'].choices = pm.Pgroup.objects.filter(
            Q(groupname='NONE') |  Q(identifier__tacode='SITEGROUP') & Q(bu_id__in = bulist)).values_list('id', 'groupname')
        


class SiteReportTemplate(MasterReportTemplate):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['type'].initial = am.QuestionSet.Type.SITEREPORTTEMPLATE
        self.fields['type'].widget.attrs = {'style': 'display:none'}
        if not self.instance.id:
            self.fields['site_grp_includes'].initial = 1
            self.fields['site_type_includes'].initial = 1
            self.fields['buincludes'].initial = 1

class IncidentReportTemplate(MasterReportTemplate):
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].initial = am.QuestionSet.Type.INCIDENTREPORTTEMPLATE
        utils.initailize_form_fields(self)
        if not self.instance.id:
            self.fields['site_grp_includes'].initial = 1
            self.fields['site_type_includes'].initial = 1
            self.fields['buincludes'].initial = 1



class TestForm(forms.Form):
    firstname  = forms.CharField(max_length=10, required=False)
    lastname   = forms.CharField(max_length=10, required=True)
    middlename = forms.CharField(max_length=10, required=True)
