from django import forms
from apps.activity import models as am
from apps.onboarding import models as om
from apps.peoples import models as pm
from apps.core import utils
from django_select2 import forms as s2forms


class MasterReportTemplate(forms.ModelForm):
    required_css_class = "required"
    showto_allsites    = forms.BooleanField(initial = False, required = False, label='Show to all sites')
    buincludes         = forms.MultipleChoiceField(widget = s2forms.Select2MultipleWidget, label='Buisiness Units')
    site_type_includes = forms.MultipleChoiceField(widget = s2forms.Select2MultipleWidget, label='Sitetype')
    site_grp_includes  = forms.MultipleChoiceField(widget = s2forms.Select2MultipleWidget, label='Sitegroup')

    class Meta:
        model = am.QuestionSet
        fields = [
            'type',  'qsetname', 'buincludes', 'site_grp_includes', 
            'site_type_includes', 'enable', 'ctzoffset']


class SiteReportTemplate(MasterReportTemplate):

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['site_type_includes'].widget.choices = om.Bt.objects.filter(butype__tacode = "BVTYPE").values_list('id', 'buname')
        bulist = om.Bt.objects.get_bu_list_ids(self.request.session['client_id'])
        self.fields['buincludes'].widget.choices = om.Bt.objects.filter(id__in = bulist).values_list('id', 'buname')
        self.fields['site_grp_includes'].widget.choices = pm.Pgroup.objects.filter(
            identifier__tacode='SITEGROUP', bu_id__in = bulist).values_list('id', 'groupname')
        self.fields['type'].widget.attrs = {'style': 'display:none'}
        self.fields['type'].initial = am.QuestionSet.Type.SITEREPORTTEMPLATE


class IncidentReportTemplate(MasterReportTemplate):
    class Meta(MasterReportTemplate.Meta):
        exclude = ['showto_allsites', 'site_grp_includes', 'site_type_includes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['site_type_includes'].queryset = om.TypeAssist.objects.filter(
            tatype__tacode='SITETYPE')
        self.fields['type'].widget.attrs = {'style': 'display:none'}
        self.fields['type'].initial = am.QuestionSet.Type.INCIDENTREPORTTEMPLATE
        utils.initailize_form_fields(self)
