from django import forms
from apps.activity import models as am
from apps.onboarding import models as om
from apps.peoples import models as pm
from apps.core import utils
from django_select2 import forms as s2forms
from django.db.models import Q
from datetime import datetime, timedelta
from django.conf import settings

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




class ReportBuilderForm(forms.Form):
    model = forms.ChoiceField(label="Model", widget=s2forms.Select2Widget, help_text="Select a model where you want data from")
    columns = forms.MultipleChoiceField(label="Coumns", widget=s2forms.Select2MultipleWidget, help_text="Select columns required in the report")
    

class ReportForm(forms.Form):
    required_css_class = "required"
    report_templates = [
        ('', 'Select Report'),
        ('TaskSummary', 'Task Summary'),
        ('TourSummary', 'Tour Summary'),
        ('ListOfTasks', 'List of Tasks'),
        ('ListOfTours', 'List of Internal Tours'),
        ('PPMSummary', 'PPM Summary'),
        ('ListOfTickets', 'List of Tickets'),
        ('WorkOrderList', 'Work Order List'),
        ('SiteReport', 'Site Report'),
        ('PeopleQR', 'People-QR'),
        ('AssetQR', 'Asset-QR'),
        ('CheckpointQR', 'Checkpoint-QR'),
    ]
    download_or_send_options = [
        ('DOWNLOAD', 'Download'),
        ('SEND', 'Email'),
    ]
    format_types = [
        ('pdf', 'PDF'),
        ('xlsx', 'XLSX'),
        ('html', 'HTML'),
        ('json', 'JSON'),
        ('csv', 'CSV'),
    ]
    SIZES = [
        (120, 'Small'),
        (200, 'Medium'),
        (300, 'Large'), 
    ]
    
    People_or_Site_CHOICES = [('PEOPLE', 'People'), ('SITE', 'Site')]
    
    # data fields
    report_name     = forms.ChoiceField(label='Report Name', required=True, choices=report_templates, initial='TASK_SUMMARY')
    site            = forms.ChoiceField(label='Site', required = False, widget=s2forms.Select2Widget)
    sitegroup       = forms.ChoiceField(label="Site Group", required=False, widget=s2forms.Select2Widget)
    fromdate        = forms.DateField(label='From Date', required=False)
    fromdatetime    = forms.DateTimeField(label='From Date Time', required=False)
    uptodate        = forms.DateField(label='To Date', required=False)
    uptodatetime    = forms.DateTimeField(label='To Date Time', required=False)
    asset           = forms.CharField(label="Asset", widget=s2forms.Select2Widget, required=False)
    qset            = forms.CharField(label="Question Set", widget=s2forms.Select2Widget, required=False)
    assettype       = forms.ChoiceField(label="Asset Type", widget=s2forms.Select2Widget, required=False)
    checkpoint      = forms.CharField(label='Checkpoint', widget=s2forms.Select2Widget, required=False)
    checkpoint_type = forms.CharField(label='Checkpoint Type', widget=s2forms.Select2Widget, required=False)
    ticketcategory  = forms.CharField(label='Ticket Category', widget=s2forms.Select2MultipleWidget, required=False)
    peoplegroup     = forms.ChoiceField(label="People Group", widget=s2forms.Select2Widget, required=False, choices=[])
    people          = forms.ChoiceField(label="People", widget=s2forms.Select2Widget, required=False, choices=[])
    mult_people     = forms.MultipleChoiceField(label="People", widget=s2forms.Select2MultipleWidget, required=False, choices=[])
    qrsize          = forms.ChoiceField(label="QR Size", widget=s2forms.Select2Widget, choices=SIZES, initial=120, required=False)
    assetcategory   = forms.ChoiceField(label="Asset Category", widget=s2forms.Select2Widget, required=False)
    site_or_people  = forms.ChoiceField(label="Site/People", widget=s2forms.Select2Widget,choices=People_or_Site_CHOICES, required=False)
    
    #other form fields
    format      = forms.ChoiceField(widget=s2forms.Select2Widget, label="Format", required=True, choices=format_types, initial='PDF')
    export_type = forms.ChoiceField(widget=s2forms.Select2Widget, label='Get File with', required=True, choices=download_or_send_options, initial='DOWNLOAD')
    cc          = forms.MultipleChoiceField(label='CC', required=False, widget=s2forms.Select2MultipleWidget)
    to_addr     = forms.MultipleChoiceField(label="To", required=False, widget=s2forms.Select2MultipleWidget)
    preview     = forms.CharField(widget=forms.HiddenInput,required=False, initial="false")
    email_body  = forms.CharField(label='Email Body', max_length=500, required=False, widget=forms.Textarea(attrs={'rows':2}))
    ctzoffset   = forms.IntegerField(required=False)

    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['site'].choices = pm.Pgbelonging.objects.get_assigned_sites_to_people(S.get('_auth_user_id'), True)
        self.fields['sitegroup'].choices = [("", "")] + list(pm.Pgroup.objects.filter(
            identifier__tacode="SITEGROUP",
            bu_id__in = S['assignedsites'],
            enable=True).values_list('id', 'groupname'))
        self.fields['peoplegroup'].choices = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True, choices=True)
        self.fields['people'].choices = self.fields['mult_people'].choices = pm.People.objects.filter_for_dd_people_field(self.request, sitewise=True, choices=True)
        self.fields['assettype'].choices  = am.Asset.objects.asset_type_choices_for_report(self.request)
        self.fields['assetcategory'].choices = am.Asset.objects.asset_category_choices_for_report(self.request)
        self.fields['fromdate'].initial = self.get_default_range_of_dates()[0]
        self.fields['uptodate'].initial = self.get_default_range_of_dates()[1]
        self.fields['cc'].choices = pm.People.objects.filter(isverified=True, client_id = S['client_id']).values_list('email', 'peoplename')
        self.fields['to_addr'].choices = pm.People.objects.filter(isverified=True, client_id = S['client_id']).values_list('email', 'peoplename')
        utils.initailize_form_fields(self)
        
        
    def get_default_range_of_dates(self):
        today = datetime.now().date()
        first_day_of_month = today.replace(day=1)
        last_day_of_last_month = first_day_of_month - timedelta(days=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1)
        return first_day_of_last_month, last_day_of_last_month

    def clean(self):
        super().clean()
        cd = self.cleaned_data
        if cd['report_name'] == settings.KNOWAGE_REPORTS['SITEREPORT'] and cd.get('people') in ["", None] and cd.get('sitegroup') in ["", None]:
            raise forms.ValidationError(
                f"Both Site Group and People cannot be empty, when the report is {cd.get('report_name')}")
        
        # if cd.get('report_name') == settings.KNOWAGE_REPORTS['LISTOFTICKETS'] and cd.get('people') in ["", None] and cd.get('ticketcategory') in ["", None]:
        #     raise forms.ValidationError(
        #         f"Both Ticket Category and People cannot be empty, when the report is {cd.get('report_name')}")
        
        
        if cd.get("fromdate") and cd['fromdate'] > cd['uptodate']: self.add_error('fromdate', 'From date cannot be greater than To date')
        if cd.get('uptodate') and cd['uptodate'] > cd['fromdate'] + timedelta(days=31):
            err_msg = 'The difference between From date and To date should not be greater than 1 a month'
            self.add_error('fromdate', err_msg)
            self.add_error('uptodate', err_msg)
        if cd['format'] != 'pdf': self.cleaned_data['preview'] = "false"
        return self.cleaned_data
    
    def get_fields_report_map(self):
        '''
        a map of required fields for a type of report
        '''
        return {
            'Task Summary': ['id_site', 'id_fromdate', 'id_uptodate'],
            'Tour Summary': ['id_site', 'id_fromdate', 'id_uptodate'],
            'Work Order List': ['id_site', 'id_fromdate', 'id_uptodate'],
            'List of Tasks': ['id_site', 'id_fromdate', 'id_uptodate'],
            'List of Internal Tours':['id_site', 'id_fromdate', 'id_uptodate'],
            'PPM Summary': ['id_site', 'id_fromdate', 'id_uptodate'],
            'List of Tickets':['id_site', 'id_fromdate', 'id_uptodate'],
            'Site Report':['id_sitegroup', 'id_fromdate', 'id_uptodate'],
            'People-QR':[],#['id_site', 'id_mult_people', 'id_qrsize','id_site_or_people'],
            'Asset-QR':['id_site', 'id_asset','id_assettype', 'id_qrsize'],
            'Checkpoint-QR':['id_site', 'id_qrsize']
        }

    
    
