from cProfile import label
from datetime import time
from django.conf import settings
from apps.activity.forms import JobForm, JobNeedForm
from django import forms
from django.utils.timezone import utc
import apps.onboarding.utils as ob_utils
import apps.schedhuler.utils as sd_utils
from django_select2 import forms as s2forms
import apps.activity.models as am
import apps.onboarding.models as ob
import pytz

class SchdInternalTourForm(JobForm):
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices=ASSIGNTO_CHOICES, initial="PEOPLE")
    required_css_class = "required"
    


    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super(SchdInternalTourForm, self).__init__(*args, **kwargs)
        self.fields['from_date'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['upto_date'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['identifier'].widget.attrs  = {"style":"display:none"}
        self.fields['expirytime'].widget.attrs  = {"style":"display:none"}
        self.fields['starttime'].widget.attrs   = {"style":"display:none"}
        self.fields['endtime'].widget.attrs     = {"style":"display:none"}
        self.fields['frequency'].widget.attrs   = {"style":"display:none"}
        self.fields['ticket_category'].queryset = ob.TypeAssist.objects.filter(tatype__tacode="TICKETCATEGORY")
        ob_utils.initailize_form_fields(self)
        

    
    def clean_from_date(self):
        val = self.cleaned_data.get('from_date')
        if val:
            val =  ob_utils.to_utc(val)
            return val
    
    def clean_upto_date(self):
        val = self.cleaned_data.get('upto_date')
        if val:
            val =  ob_utils.to_utc(val)
            return val

    def clean_frequency(self):
        return 'NONE'
    
    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super(SchdInternalTourForm, self).is_valid()
        ob_utils.apply_error_classes(self)
        return result 
    
        
    def clean_slno(self):
        return -1
    
    def clean(self):
        super().clean()
        self.instance.jobdesc = f'{self.instance.buid.buname} - {self.instance.jobname}'
    


class SchdChildInternalTourForm(JobForm): #job
    timeInChoices = [('MIN', 'Min'),('HRS', 'Hours')]
    
    #timeIn = forms.ChoiceField(choices=timeInChoices, initial='MIN', widget=s2forms.Select2Widget)


    class Meta(JobForm.Meta):
        fields =['qsetid', 'peopleid', 'assetid', 'expirytime', 'slno']
    
    def __init__(self, *args, **kwargs):
        super(SchdChildInternalTourForm, self).__init__(*args, **kwargs)
        self.fields['slno'].widget.attrs = {'readonly':True}
        ob_utils.initailize_form_fields(self)



    

class InternalTourForm(JobNeedForm): #jobneed
    timeInChoices      = [('MIN', 'Min'),('HRS', 'Hour'), ('DAY', 'Day'), ('WEEK', 'Week')]
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices=ASSIGNTO_CHOICES, initial="PEOPLE")
    timeIn             = forms.ChoiceField(choices=timeInChoices, initial='MIN', widget=s2forms.Select2Widget)
    required_css_class = "required"
    
    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super(InternalTourForm, self).is_valid()
        ob_utils.apply_error_classes(self)
        return result
    
    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super(InternalTourForm, self).__init__(*args, **kwargs)
        self.fields['plandatetime'].input_formats   = settings.DATETIME_INPUT_FORMATS
        self.fields['expirydatetime'].input_formats = settings.DATETIME_INPUT_FORMATS
        self.fields['identifier'].widget.attrs      = {"style":"display:none"}
        self.fields['starttime'].widget.attrs       = {"disabled":"disabled"}
        self.fields['endtime'].widget.attrs         = {"disabled":"disabled"}
        self.fields['performed_by'].widget.attrs    = {"disabled":"disabled"}
        self.fields['ticket_category'].queryset     = ob.TypeAssist.objects.filter(tatype__tacode="TICKETCATEGORY")
        ob_utils.initailize_form_fields(self)
        
        
    def clean_plandatetime(self):
        val = self.cleaned_data.get('plandatetime')
        if val:
            val =  ob_utils.to_utc(val)
            return val
    
    def clean_expirydatetime(self):
        val = self.cleaned_data.get('plandatetime')
        if val:
            val =  ob_utils.to_utc(val)
            return val
        
    def clean_starttime(self):
        val = self.cleaned_data.get('starttime')
        if val:
            val =  ob_utils.to_utc(val)
            return val
    
    def clean_endtime(self):
        val = self.cleaned_data.get('endtime')
        if val:
            val =  ob_utils.to_utc(val)
            return val
        
    def clean_frequency(self):
        return "NONE"
    
class ChildInternalTourForm(JobNeedForm):#jobneed
    class Meta(JobNeedForm.Meta):
        fields =['qsetid', 'assetid', 'plandatetime', 'expirydatetime', 'gracetime']
        
    def __init__(self, *args, **kwargs):
        super(ChildInternalTourForm, self).__init__(*args, **kwargs)
        ob_utils.initailize_form_fields(self)
        
        
class ExternalSchdTourForm(JobForm):
    timeInChoices = [('MIN', 'Min'),('HRS', 'Hours')]
    
    class Meta(JobForm.Meta):
        JobForm.Meta.labels.update({'buid':'Cluster'})
        exclude = ['jobdesc']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super(ExternalSchdTourForm, self).__init__(*args, **kwargs)
        self.fields['from_date'].input_formats = settings.DATETIME_INPUT_FORMATS
        self.fields['upto_date'].input_formats = settings.DATETIME_INPUT_FORMATS
        self.fields['ticket_category'].initial = ob.TypeAssist.objects.get(tacode='AUTOCLOSED')
        ob_utils.initailize_form_fields(self)
        
    def clean_from_date(self):
        val = self.cleaned_data.get('from_date')
        if val:
            val =  ob_utils.to_utc(val)
            return val
    
    def clean_upto_date(self):
        val = self.cleaned_data.get('upto_date')
        if val:
            val =  ob_utils.to_utc(val)
            return val

    def clean_slno(self):
        return -1

    def clean(self):
        cd = super().clean()
        self.instance.jobdesc = f'{cd.get("buid")} - {cd.get("jobname")}'
        
        

    

class EditAssignedSiteForm(forms.Form):
    br_time   = forms.IntegerField(max_value=30, min_value=0, label="Breaktime", required=True)
    checklist = forms.ChoiceField(
        widget = s2forms.Select2Widget,
        label  = "Checklist", required = True,
        choices = am.QuestionSet.objects.all().values_list('id', 'qset_name')
    )

    def __init__(self, *args, **kwargs):
        super(EditAssignedSiteForm, self).__init__(*args, **kwargs)
        ob_utils.initailize_form_fields(self)