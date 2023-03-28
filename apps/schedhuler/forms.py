from django.conf import settings
from django import forms
from apps.activity.forms import JobForm, JobNeedForm
import apps.onboarding.utils as ob_utils    
from apps.core import utils
from django_select2 import forms as s2forms
from django.db.models import Q
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
        })

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['fromdate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['uptodate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['identifier'].widget.attrs  = {"style": "display:none"}
        self.fields['expirytime'].widget.attrs  = {"style": "display:none"}
        self.fields['starttime'].widget.attrs   = {"style": "display:none"}
        self.fields['endtime'].widget.attrs     = {"style": "display:none"}
        self.fields['frequency'].widget.attrs   = {"style": "display:none"}
        
        #filters for dropdowm fields
        self.fields['ticketcategory'].queryset = ob.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        self.fields['pgroup'].queryset = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True)
        self.fields['people'].queryset = pm.People.objects.filter_for_dd_people_field(self.request, sitewise=True)
        utils.initailize_form_fields(self)
        

    def clean(self):
        super().clean()
        cd = self.cleaned_data
        if cd['people'] is None and cd['pgroup'] is None:
            raise forms.ValidationError('Cannot be proceed assigned tour to either people or group.')
        self.cleaned_data = self.check_nones(self.cleaned_data)
        
    

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
    
    
    def check_nones(self, cd):
        fields = {
            'parent':'get_or_create_none_job',
            'people': 'get_or_create_none_people',
            'pgroup': 'get_or_create_none_pgroup',
            'asset' : 'get_or_create_none_asset'}
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd

    @staticmethod
    def clean_slno():
        return -1


        


class SchdChild_I_TourJobForm(JobForm): # job
    timeInChoices = [('MIN', 'Min'),('HRS', 'Hours')]

    # timeIn = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)

    class Meta(JobForm.Meta):
        fields =['qset', 'people', 'asset', 'expirytime', 'seqno']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['seqno'].widget.attrs = {'readonly':True}
        
        #filters for dropdown fields
        self.fields['qset'].queryset = am.QuestionSet.objects.get_proper_checklist_for_scheduling(self.request, ['CHECKLIST', 'QUESTIONSET'])
        self.fields['asset'].queryset = am.Asset.objects.filter(identifier__in = ['CHECKPOINT', "ASSET"], client_id = self.request.session['client_id'], enable=True)
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
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['plandatetime'].input_formats   = settings.DATETIME_INPUT_FORMATS
        self.fields['expirydatetime'].input_formats = settings.DATETIME_INPUT_FORMATS
        self.fields['identifier'].widget.attrs      = {"style": "display:none"}
        self.fields['starttime'].widget.attrs       = {"disabled": "disabled"}
        self.fields['endtime'].widget.attrs         = {"disabled": "disabled"}
        self.fields['performedby'].widget.attrs    = {"disabled": "disabled"}
        self.fields['qset'].label = 'Checklist'
        self.fields['asset'].label = 'Asset/Smartplace'
        
        self.fields['ticketcategory'].widget.queryset = ob.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
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

    @staticmethod
    def clean_frequency():
        return "NONE"

class Child_I_TourFormJobneed(JobNeedForm):# jobneed
    class Meta(JobNeedForm.Meta):
        fields =['qset', 'asset', 'plandatetime', 'expirydatetime', 'gracetime']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        #filters for dropdown fields
        self.fields['qset'].queryset = am.QuestionSet.objects.filter_for_dd_qset_field(self.request, ['CHECKLIST'], sitewise=True)
        self.fields['asset'].queryset = am.Asset.objects.filter_for_dd_asset_field(self.request, ['CHECKPOINT', 'ASSET'], sitewise=True)
        utils.initailize_form_fields(self)


class TaskFormJobneed(I_TourFormJobneed):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = kwargs.pop('request', None)
        S = self.request.session
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
            'sgroup':'Route Name'
            }) 
        JobForm.Meta.widgets.update(
            {'identifier':forms.TextInput(attrs={'style': 'display:none;'}),
            'starttime':forms.TextInput(attrs={'style': 'display:none;'}),
            'endtime':forms.TextInput(attrs={'style': 'display:none;'}),
            'frequency':forms.TextInput(attrs={'style': 'display:none;'}),
            'priority':forms.TextInput(attrs={'style': 'display:none;'}),
            'seqno':forms.TextInput(attrs={'style': 'display:none;'}),
            'ticketcategory':forms.TextInput(attrs={'style': 'display:none;'}),
            }
        )
        exclude = ['jobdesc']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['israndom'].widget.attrs['class'] = 'btdeciders'
        self.fields['tourfrequency'].widget.attrs['class'] = 'btdeciders'
        self.fields['fromdate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['uptodate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['ticketcategory'].initial  = ob.TypeAssist.objects.get(tacode='AUTOCLOSED')
        self.fields['sgroup'].required  = True
        self.fields['identifier'].widget.attrs = {"style": "display:none"}
        self.fields['expirytime'].widget.attrs = {"style": "display:none"}
        self.fields['starttime'].widget.attrs  = {"style": "display:none"}
        self.fields['endtime'].widget.attrs    = {"style": "display:none"}
        self.fields['frequency'].widget.attrs  = {"style": "display:none"}
        self.fields['priority'].widget.attrs   = {"style": "display:none"}
        self.fields['scantype'].widget.attrs   = {"style": "display:none"}
        self.fields['seqno'].widget.attrs      = {"style": "display:none"}
        
        #filters for dropdown fields
        self.fields['qset'].queryset  = am.QuestionSet.objects.get_proper_checklist_for_scheduling(self.request, ['RPCHECKLIST'])
        self.fields['ticketcategory'].queryset  = ob.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request)
        self.fields['sgroup'].queryset  = pm.Pgroup.objects.filter(identifier__tacode="SITEGROUP", bu_id__in = S['assignedsites'], enable=True)
        self.fields['people'].queryset  = pm.People.objects.filter_for_dd_people_field(self.request)
        self.fields['pgroup'].queryset = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request)

        utils.initailize_form_fields(self)
        
    def clean(self):
        super().clean()
        cd = self.cleaned_data
        if cd['people'] is None and cd['pgroup'] is None:
            raise forms.ValidationError('Cannot be proceed assigned tour to either people or group.')
        
        
    def clean_cron(self):
        if val := self.cleaned_data.get('cron'):
            return val
        raise forms.ValidationError("Invalid Cron")




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
    timeInChoices      = [('MINS', 'Min'),('HRS', 'Hour'), ('DAYS', 'Day')]
    required_css_class = "required"

    planduration_type  = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    gracetime_type     = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    expirytime_type    = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")

    class Meta(JobForm.Meta):
        exclude = ['shift'] 
        JobForm.Meta.widgets.update({
            'identifier'    : forms.TextInput(attrs={'style': 'display:none;'}),
            'starttime'     : forms.TextInput(attrs={'style': 'display:none;'}),
            'endtime'       : forms.TextInput(attrs={'style': 'display:none;'}),
            'frequency'     : forms.TextInput(attrs={'style': 'display:none;'}),
            'ticketcategory': s2forms.Select2Widget,
            'scantype'      : s2forms.Select2Widget,
            'priority'      : s2forms.Select2Widget,
        })

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super(SchdTaskFormJob, self).__init__(*args, **kwargs)
        self.fields['fromdate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['uptodate'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['jobdesc'].required        = False
        self.fields['identifier'].widget.attrs = {"style": "display:none"}
        self.fields['starttime'].widget.attrs  = {"style": "display:none"}
        self.fields['endtime'].widget.attrs    = {"style": "display:none"}
        self.fields['frequency'].widget.attrs  = {"style": "display:none"}
        self.fields['expirytime'].label        = 'Grace Time (After)'
        self.fields['gracetime'].label         = 'Grace Time (Before)'
        
        #filters for dropdown fields
        self.fields['ticketcategory'].queryset = ob.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        self.fields['qset'].queryset = am.QuestionSet.objects.filter_for_dd_qset_field(self.request, ['CHECKLIST'], sitewise=True)
        self.fields['asset'].queryset = am.Asset.objects.filter_for_dd_asset_field(self.request, identifiers =["ASSET", 'CHECKPOINT'], sitewise=True)
        self.fields['pgroup'].queryset = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True)
        self.fields['people'].queryset = pm.People.objects.filter_for_dd_people_field(self.request, sitewise=True)
        utils.initailize_form_fields(self)

    def clean(self):
        cd          = self.cleaned_data
        times_names = ['planduration', 'expirytime', 'gracetime']
        types_names = ['planduration_type', 'expirytime_type', 'gracetime_type']
        self.cleaned_data = self.check_nones(self.cleaned_data)
        
        times = [cd.get(time) for time in times_names]
        types = [cd.get(type) for type in types_names]
        for time, type, name in zip(times, types, times_names):
            self.cleaned_data[name] = self.convertto_mins(type, time)

    @staticmethod
    def convertto_mins(_type, _time):
        if _type == 'HRS':
            return _time * 60
        return _time * 24 * 60 if _type == 'DAYS' else _time
    
    def check_nones(self, cd):
        fields = {
            'parent':'get_or_create_none_job',
            'people': 'get_or_create_none_people',
            'pgroup': 'get_or_create_none_pgroup',
            'asset' : 'get_or_create_none_asset'}
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd      
       



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
        S = self.request.session
        super(TicketForm, self).__init__(*args, **kwargs)
        self.fields['plandatetime'].input_formats   = settings.DATETIME_INPUT_FORMATS
        self.fields['expirydatetime'].input_formats = settings.DATETIME_INPUT_FORMATS
        if not self.instance.id:
            self.fields['jobstatus'].widget.attrs = {'disabled': 'readonly'}
            self.fields['ticketno'].widget.attrs  = {'disabled': 'disabled', 'readonly': 'readonly'}
        self.fields['cuser'].required = False
        self.fields['asset'].label = 'Location'
        
        #filters for dropdown fields
        self.fields['ticketcategory'].queryset     = ob.TypeAssist.objects.filter(tatype__tacode="TICKETCATEGORY", client_id = S['client_id'], bu_id = S['bu_id'], enable=True)
        self.fields['assignedtopeople'].queryset = pm.People.objects.filter_for_dd_people_field(self.request, sitewise=True)
        self.fields['assignedtogroup'].queryset = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True)
        self.fields['location'].queryset = am.Location.objects.filter_for_dd_location_field(self.request, sitewise=True)
        self.fields['asset'].queryset = am.Asset.objects.filter_for_dd_asset_field(self.request, ['ASSET', 'CHECKPOINT'], sitewise=True)
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

    @staticmethod
    def clean_frequency():
        return "NONE"


class E_TourFormJobneed(JobNeedForm):
    timeInChoices      = [('MIN', 'Min'),('HRS', 'Hour'), ('DAY', 'Day'), ('WEEK', 'Week')]
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    timeIn             = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    required_css_class = "required"
    
    
    def __init__(self, *args, **kwargs):
    #     '''Initializes form add attributes and classes here'''
        super(JobNeedForm, self).__init__(*args, **kwargs)
        self.fields['endtime'].label = "End Time"
        for k in ['scantype', 'starttime', 'endtime']:
            self.fields[k].widget.attrs.pop('style')
            if k in ['starttime', 'endtime']:
                self.fields[k].widget.attrs.update({'disabled':True})
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

    @staticmethod
    def clean_frequency():
        return "NONE"
