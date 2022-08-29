from django.conf import settings
from django import forms
from apps.activity.forms import JobForm, JobNeedForm
import apps.onboarding.utils as ob_utils
from apps.core import utils
from django_select2 import forms as s2forms
import apps.activity.models as am
import apps.peoples.models as pm
import apps.onboarding.models as ob

class Schd_I_TourJobForm(JobForm):
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    required_css_class = "required"

    class Meta(JobForm.Meta):
        exclude = ['shift']
        JobForm.Meta.widgets.update({
            'identifier':forms.TextInput(attrs={'style': 'display:none;'}),
            'starttime':forms.TextInput(attrs={'style': 'display:none;'}),
            'endtime':forms.TextInput(attrs={'style': 'display:none;'}),
            'frequency':forms.TextInput(attrs={'style': 'display:none;'}),
            'jobname':forms.TextInput(attrs={'placeholder': 'Enter Route Plan Name:'}),
        })

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['fromdate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['uptodate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['identifier'].widget.attrs  = {"style": "display:none"}
        self.fields['expirytime'].widget.attrs  = {"style": "display:none"}
        self.fields['starttime'].widget.attrs   = {"style": "display:none"}
        self.fields['endtime'].widget.attrs     = {"style": "display:none"}
        self.fields['frequency'].widget.attrs   = {"style": "display:none"}
        self.fields['ticketcategory'].queryset = ob.TypeAssist.objects.filter(tatype__tacode="TICKETCATEGORY")
        utils.initailize_form_fields(self)


    def clean_from_date(self):
        if val := self.cleaned_data.get('fromdate'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_upto_date(self):
        if val := self.cleaned_data.get('uptodate'):
            val =  ob_utils.to_utc(val)
            return val

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super(Schd_I_TourJobForm, self).is_valid()
        utils.apply_error_classes(self)
        return result 

    def clean_slno(self):
        return -1

    def clean(self):
        super().clean()
        bu = ob.Bt.objects.get(id = self.request.session['bu_id'])
        self.instance.jobdesc = f'{bu.buname} - {self.instance.jobname}'


class SchdChild_I_TourJobForm(JobForm): # job
    timeInChoices = [('MIN', 'Min'),('HRS', 'Hours')]

    # timeIn = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)

    class Meta(JobForm.Meta):
        fields =['qset', 'people', 'asset', 'expirytime', 'seqno']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['seqno'].widget.attrs = {'readonly':True}
        utils.initailize_form_fields(self)



class I_TourFormJobneed(JobNeedForm): # jobneed
    timeInChoices      = [('MIN', 'Min'),('HRS', 'Hour'), ('DAY', 'Day'), ('WEEK', 'Week')]
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    timeIn             = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    required_css_class = "required"


    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['plandatetime'].input_formats   = settings.DATETIME_INPUT_FORMATS
        self.fields['expirydatetime'].input_formats = settings.DATETIME_INPUT_FORMATS
        self.fields['identifier'].widget.attrs      = {"style": "display:none"}
        self.fields['starttime'].widget.attrs       = {"disabled": "disabled"}
        self.fields['endtime'].widget.attrs         = {"disabled": "disabled"}
        self.fields['performedby'].widget.attrs    = {"disabled": "disabled"}
        self.fields['qset'].label = 'QuestionSet'
        self.fields['asset'].label = 'Asset/Smartplace'
        self.fields['ticketcategory'].queryset     = ob.TypeAssist.objects.filter(tatype__tacode="TICKETCATEGORY")
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super(I_TourFormJobneed, self).is_valid()
        ob_utils.apply_error_classes(self)
        return result

    def clean_plandatetime(self):
        if val := self.cleaned_data.get('plandatetime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_expirydatetime(self):
        if val := self.cleaned_data.get('plandatetime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_starttime(self):
        if val := self.cleaned_data.get('starttime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_endtime(self):
        if val := self.cleaned_data.get('endtime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_frequency(self):
        return "NONE"

class Child_I_TourFormJobneed(JobNeedForm):# jobneed
    class Meta(JobNeedForm.Meta):
        fields =['qset', 'asset', 'plandatetime', 'expirydatetime', 'gracetime']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)


class TaskFormJobneed(I_TourFormJobneed):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['jobdesc'].required = True
        utils.initailize_form_fields(self)
        if not self.instance.id:
            ic('iside')
            self.fields['asset'].queryset = am.Asset.objects.filter(identifier__in = ['Asset', 'Smartplace'])
            self.fields['qset'].queryset = am.QuestionSet.objects.filter(type = ['QUESTIONSET'])



class Schd_E_TourJobForm(JobForm):
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    timeInChoices = [('MIN', 'Min'),('HRS', 'Hours')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    israndom = forms.BooleanField(initial=False, label="Is Random Tour", required=False)
    tourfrequency = forms.IntegerField(min_value=1, max_value=3, initial=1, label='Frequency', required=False)
    breaktime = forms.IntegerField(label='Frequency', required=False)
    required_css_class = "required"


    class Meta(JobForm.Meta):
        JobForm.Meta.labels.update({
            'sgroup':'SiteGroup'
            }) 
        JobForm.Meta.widgets.update(
            {'identifier':forms.TextInput(attrs={'style': 'display:none;'}),
            'starttime':forms.TextInput(attrs={'style': 'display:none;'}),
            'endtime':forms.TextInput(attrs={'style': 'display:none;'}),
            'frequency':forms.TextInput(attrs={'style': 'display:none;'}),
            'priority':forms.TextInput(attrs={'style': 'display:none;'}),
            'seqno':forms.TextInput(attrs={'style': 'display:none;'}),
            'scantype':forms.TextInput(attrs={'style': 'display:none;'}),
            'ticketcategory':forms.TextInput(attrs={'style': 'display:none;'}),
            'jobname':forms.TextInput(attrs={'placeholder': 'Enter Route Plan Name:'})}
        )
        exclude = ['jobdesc']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['israndom'].widget.attrs['class'] = 'btdeciders'
        self.fields['tourfrequency'].widget.attrs['class'] = 'btdeciders'
        self.fields['fromdate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['uptodate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['ticketcategory'].initial  = ob.TypeAssist.objects.get(tacode='AUTOCLOSED')
        self.fields['sgroup'].queryset  = pm.Pgroup.objects.filter(identifier__tacode="SITEGROUP")
        self.fields['identifier'].widget.attrs = {"style": "display:none"}
        self.fields['expirytime'].widget.attrs = {"style": "display:none"}
        self.fields['starttime'].widget.attrs  = {"style": "display:none"}
        self.fields['endtime'].widget.attrs    = {"style": "display:none"}
        self.fields['frequency'].widget.attrs  = {"style": "display:none"}
        self.fields['priority'].widget.attrs   = {"style": "display:none"}
        self.fields['scantype'].widget.attrs   = {"style": "display:none"}
        self.fields['seqno'].widget.attrs      = {"style": "display:none"}
        utils.initailize_form_fields(self)




class EditAssignedSiteForm(forms.Form):
    br_time   = forms.IntegerField(max_value = 30, min_value = 0, label="Breaktime", required = True)
    checklist = forms.ChoiceField(
        widget  = s2forms.Select2Widget,
        label   = "Checklist",           required = True,
        choices = []
    )

    def __init__(self, *args, **kwargs):
        super(EditAssignedSiteForm, self).__init__(*args, **kwargs)
        self.fields['checklist'].choices = am.QuestionSet.objects.all().values_list('id', 'qsetname')
        utils.initailize_form_fields(self)

class SchdTaskFormJob(JobForm):
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    timeInChoices      = [('MIN', 'Min'),('HRS', 'Hour'), ('DAY', 'Day')]
    required_css_class = "required"

    planduration_type  = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    gracetime_type     = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    expirytime_type    = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")

    class Meta(JobForm.Meta):
        exclude = ['shift']
        JobForm.Meta.widgets.update({
            'identifier':forms.TextInput(attrs={'style': 'display:none;'}),
            'starttime':forms.TextInput(attrs={'style': 'display:none;'}),
            'endtime':forms.TextInput(attrs={'style': 'display:none;'}),
            'frequency':forms.TextInput(attrs={'style': 'display:none;'}),
        })

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(SchdTaskFormJob, self).__init__(*args, **kwargs)
        self.fields['fromdate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['uptodate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['jobdesc'].required        = False
        self.fields['identifier'].widget.attrs = {"style": "display:none"}
        self.fields['starttime'].widget.attrs  = {"style": "display:none"}
        self.fields['endtime'].widget.attrs    = {"style": "display:none"}
        self.fields['frequency'].widget.attrs  = {"style": "display:none"}
        self.fields['expirytime'].label        = 'Grace Time After'
        self.fields['gracetime'].label         = 'Grace Time Before'
        self.fields['ticketcategory'].queryset = ob.TypeAssist.objects.filter(tatype__tacode="TICKETCATEGORY")
        utils.initailize_form_fields(self)

    def clean(self):
        cd          = self.cleaned_data
        times_names = ['planduration', 'expirytime', 'gracetime']
        types_names = ['planduration_type', 'expirytime', 'gracetime']

        times = [cd.get(time) for time in times_names]
        types = [cd.get(type) for type in types_names]
        for time, type in zip(times, types):
            self.cleaned_data[time] = self.convertto_mins(type, time)

    def convertto_mins(self, _type, _time):
        if _type == 'HOURS':
            return _time * 60
        elif _type == 'DAYS':
            return _time * 24 * 60
        else:
            return _time            



class TicketForm(JobNeedForm):
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    required_css_class = "required"

    class Meta(JobNeedForm.Meta):
        JobNeedForm.Meta.widgets.update({
            'scantype'   : forms.TextInput(attrs={'style': 'display:none'}),
            'frequency'  : forms.TextInput(attrs={'style': 'display:none'}),
            'starttime'  : forms.TextInput(attrs={'style': 'display:none'}),
            'endtime'    : forms.TextInput(attrs={'style': 'display:none'}),
            'identifier' : forms.TextInput(attrs={'style': 'display:none'}),
            'cuser'      : s2forms.Select2Widget(attrs={'disabled': 'readonly'}),
        })

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super(TicketForm, self).__init__(*args, **kwargs)
        self.fields['plandatetime'].input_formats   = settings.DATETIME_INPUT_FORMATS
        self.fields['expirydatetime'].input_formats = settings.DATETIME_INPUT_FORMATS
        if not self.instance.id:
            self.fields['jobstatus'].widget.attrs = {'disabled': 'readonly'}
            self.fields['ticketno'].widget.attrs  = {'disabled': 'disabled', 'readonly': 'readonly'}
        self.fields['cuser'].required = False
        self.fields['asset'].label = 'Location'
        self.fields['ticketcategory'].queryset     = ob.TypeAssist.objects.filter(tatype__tacode="TICKETCATEGORY")
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super(I_TourFormJobneed, self).is_valid()
        ob_utils.apply_error_classes(self)
        return result

    def clean_plandatetime(self):
        if val := self.cleaned_data.get('plandatetime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_expirydatetime(self):
        if val := self.cleaned_data.get('plandatetime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_starttime(self):
        if val := self.cleaned_data.get('starttime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_endtime(self):
        if val := self.cleaned_data.get('endtime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_frequency(self):
        return "NONE"


class E_TourFormJobneed(JobNeedForm):
    timeInChoices      = [('MIN', 'Min'),('HRS', 'Hour'), ('DAY', 'Day'), ('WEEK', 'Week')]
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    timeIn             = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    required_css_class = "required"
    
    
    def __init__(self, *args, **kwargs):
        '''Initializes form add attributes and classes here'''
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['plandatetime'].input_formats   = settings.DATETIME_INPUT_FORMATS
        self.fields['expirydatetime'].input_formats = settings.DATETIME_INPUT_FORMATS
        self.fields['identifier'].widget.attrs      = {"style": "display:none"}
        self.fields['starttime'].widget.attrs       = {"disabled": "disabled"}
        self.fields['endtime'].widget.attrs         = {"disabled": "disabled"}
        self.fields['endtime'].label                = 'End Time'
        self.fields['performedby'].widget.attrs     = {"disabled": "disabled"}
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super(I_TourFormJobneed, self).is_valid()
        ob_utils.apply_error_classes(self)
        return result
    
    def clean_plandatetime(self):
        if val := self.cleaned_data.get('plandatetime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_expirydatetime(self):
        if val := self.cleaned_data.get('plandatetime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_starttime(self):
        if val := self.cleaned_data.get('starttime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_endtime(self):
        if val := self.cleaned_data.get('endtime'):
            val =  ob_utils.to_utc(val)
            return val

    def clean_frequency(self):
        return "NONE"