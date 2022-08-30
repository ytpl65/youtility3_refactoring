################## Activity app - Forms ###################
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
import apps.activity.models as am
import apps.onboarding.models as om
from apps.core import utils as utils
import apps.activity.utils as ac_utils
import django_select2.forms as s2forms
import json

class QuestionForm(forms.ModelForm):
    required_css_class = "required"
    alertbelow         = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Below')
    alertabove = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Above')

    class Meta:
        model = am.Question
        fields = ['quesname', 'answertype', 'alerton', 'isworkflow',
                  'unit', 'category', 'options', 'isworkflow', 'min', 'max', 'ctzoffset']
        labels = {
            'quesname' : 'Name',
            'answertype': 'Type',
            'unit'      : 'Unit',
            'category'  : 'Category',
            'min'       : 'Min Value',
            'max'       : 'Max Value',
            'options'   : 'Options',
            'alerton'   : 'Alert On',
            'isworkflow': 'Is used in workflow?',
        }

        widgets = {
            'answertype': s2forms.Select2Widget,
            'category'  : s2forms.Select2Widget,
            'unit'      : s2forms.Select2Widget,
            'options'   : forms.Textarea(attrs={'rows': 3, 'cols': 40}),
            'alerton'   : s2forms.Select2MultipleWidget,
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        for k in self.fields.keys():
            if k in ['unit', 'min', 'max']:
                self.fields[k].required = True
            elif k in ['options', 'alerton']:
                self.fields[k].required = False
        if self.instance.id:
            ac_utils.initialize_alertbelow_alertabove(self.instance, self)
        utils.initailize_form_fields(self)

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data
        alertabove = alertbelow = None
        if data.get('answertype') and data['answertype'] not in (
            'NUMERIC',
            'DROPDOWN',
        ):
            cleaned_data['alerton'] = json.dumps([])
            cleaned_data['min']     = cleaned_data['max'] = 0.0
            cleaned_data['options'] = ""
        if data.get('alertbelow') and data.get('min'):
            print("inside alerbelowdata", data)
            alertbelow = ac_utils.validate_alertbelow(forms, data)
        if data.get('alertabove') and data.get('max'):
            print("inside alerabovedata", data)
            print("forms", data)
            alertabove = ac_utils.validate_alertabove(forms, data)
        print(alertabove, alertbelow)
        if alertabove and alertbelow:
            alerton = f'<{alertbelow}, >{alertabove}'
            cleaned_data['alerton'] = alerton

    def clean_alerton(self):
        print("alertbelow", self.cleaned_data.get('alertbelow'))
        print("alertabove", self.cleaned_data.get('alertabove'))
        val = self.cleaned_data.get('alerton')
        if val:
            return ac_utils.validate_alerton(forms, val)
        return val

    def clean_options(self):
        val = self.cleaned_data.get('options')
        if val:
            return ac_utils.validate_options(forms, val)
        return val

    def validate_unique(self) -> None:
        super().validate_unique()
        if not self.instance.id:
            try:
                am.Question.objects.get(
                    quesname__exact = self.instance.quesname,
                    answertype__iexact = self.instance.answertype,
                    client_id__exact = self.request.session['client_id'])
                msg = 'This type of Question is already exist!'
                raise forms.ValidationError(
                    message = msg, code="unique_constraint")
            except am.Question.DoesNotExist:
                pass
            except ValidationError as e:
                self._update_errors(e)

class MasterQsetForm(forms.ModelForm):
    required_css_class = "required"
    assetincludes = forms.MultipleChoiceField(
        required = True, label='Checkpoint', widget = s2forms.Select2MultipleWidget, choices = ac_utils.get_assetincludes_choices)

    class Meta:
        model = am.QuestionSet
        fields = ['qsetname', 'parent', 'enable', 'assetincludes', 'type', 'ctzoffset']

        labels = {
            'parent': 'Parent',
            'qsetname': 'Name', }
        widgets = {
            'parent': s2forms.Select2Widget()
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        super().__init__(*args, **kwargs)
        self.fields['type'].initial      = 'ASSET'
        self.fields['type'].widget.attrs = {"style": "display:none;"}
        utils.initailize_form_fields(self)

class QsetBelongingForm(forms.ModelForm):
    required_css_class = "required"
    alertbelow = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Below')
    alertabove = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Above')

    class Meta:
        model = am.QuestionSetBelonging
        fields = ['seqno', 'qset', 'question', 'answertype', 'min', 'max',
                  'alerton', 'options', 'ismandatory', 'ctzoffset']
        widgets = {
            'answertype': forms.TextInput(attrs={'readonly': 'readonly'}),
            'question'    : s2forms.Select2Widget,
            'alerton'   : s2forms.Select2MultipleWidget,
            'options'   : forms.Textarea(attrs={'rows': 3, 'cols': 40}),
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        super().__init__(*args, **kwargs)
        for k in self.fields.keys():
            if k in ['min', 'max']:
                self.fields[k].required = True
            elif k in ['options', 'alerton']:
                self.fields[k].required = False
        if self.instance.id:
            ac_utils.initialize_alertbelow_alertabove(self.instance, self)
        utils.initailize_form_fields(self)

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data
        alertabove = alertbelow = None
        if data.get('alertbelow') and data.get('min'):
            print("inside alerbelowdata", data)
            alertbelow = ac_utils.validate_alertbelow(forms, data)
        if data.get('alertabove') and data.get('max'):
            print("inside alerabovedata", data)
            print("forms", data)
            alertabove = ac_utils.validate_alertabove(forms, data)
        print(alertabove, alertbelow)
        if alertabove and alertbelow:
            alerton = f'<{alertbelow}, >{alertabove}'
            cleaned_data['alerton'] = alerton

    def clean_alerton(self):
        print("alertbelow", self.cleaned_data.get('alertbelow'))
        print("alertabove", self.cleaned_data.get('alertabove'))
        val = self.cleaned_data.get('alerton')
        if val:
            return ac_utils.validate_alerton(forms, val)
        return val

    def clean_options(self):
        val = self.cleaned_data.get('options')
        if val:
            return ac_utils.validate_options(forms, val)
        return val

    def validate_unique(self) -> None:
        super().validate_unique()
        if not self.instance.id:
            try:
                am.Question.objects.get(
                    ques_name__exact   = self.instance.quesname,
                    answertype__iexact = self.instance.answertype,
                    client_id__exact = self.request.session['client_id'])
                msg = 'This type of Question is already exist!'
                raise forms.ValidationError(
                    message = msg, code="unique_constraint")
            except am.Question.DoesNotExist:
                pass
            except ValidationError as e:
                self._update_errors(e)

class ChecklistForm(MasterQsetForm):

    class Meta(MasterQsetForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['type'].initial        = 'CHECKLIST'
        self.fields['assetincludes'].label = 'Checkpoints'
        self.fields['type'].widget.attrs   = {"style": "display:none;"}
        if self.instance.id:
            self.fields['assetincludes'].initial = self.instance.assetincludes.split(',')
        utils.initailize_form_fields(self)


class QuestionSetForm(MasterQsetForm):

    class Meta(MasterQsetForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['type'].initial          = 'QUESTIONSET'
        self.fields['assetincludes'].label   = 'Asset/Smartplace'
        self.fields['assetincludes'].choices = ac_utils.get_assetsmartplace_choices()
        self.fields['type'].widget.attrs     = {"style": "display:none;"}
        # if self.instance.id:
        #     ic(json.loads(
        #         self.instance.assetincludes))
        #     self.fields['assetincludes'].initial = json.loads(
        #         self.instance.assetincludes)
        utils.initailize_form_fields(self)



class AssetForm(forms.ModelForm):
    required_css_class = "required"
    SERVICE_CHOICES = [
        ('NONE', 'None'),
        ('AMC', 'AMC'),
        ('WARRANTY', 'Warranty'),
    ]

    tempcode       = forms.CharField(max_length = 100, label='Temporary Code', required = False)
    service        = forms.ChoiceField(choices = SERVICE_CHOICES, initial='NONE', required = False, label='Service')
    sfdate         = forms.DateField(required = False, label='Service From Date')
    stdate         = forms.DateField(required = False, label='Service To Datre')
    msn            = forms.CharField(required = False, max_length = 50,label='Manufacture Sr. No')
    yom            = forms.CharField(required = False, max_length = 50,label='Manufacture Date')
    bill_val       = forms.IntegerField(required = False, label='Bill Value')
    bill_date      = forms.DateField(required = False, label='Bill Date')
    purachase_date = forms.DateField(required = False, label='Purchase Date')
    inst_date      = forms.DateField(required = False, label='Installation Date')
    po_number      = forms.CharField(required = False, label='Purchase Order Number', max_length = 100)
    far_asset_id   = forms.CharField(required = False, label='FAR Asset Id', max_length = 100)
    invoice_date   = forms.DateField(required = False, label='Invoice Date')
    invoice_no     = forms.CharField( required = False, label='Invoice No.', max_length = 100)
    supplier       = forms.CharField(required = False, max_length = 50)
    meter          = forms.ChoiceField(choices=[], required = False, initial='NONE', label='Meter')
    model          = forms.CharField(label='Model', required = False, max_length = 100)
    gpslocation    = forms.CharField(label = 'GPS Location', required = True, initial='0.0,0.0')

    class Meta:
        model = am.Asset
        fields = ['assetcode', 'assetname', 'enable', 'runningstatus', 'type', 'parent',
                   'iscritical', 'category', 'subcategory', 'identifier',
                  'capacity', 'unit', 'brand', 'ctzoffset']

        widgets = {
            'runningstatus': s2forms.Select2Widget,
            'type'         : s2forms.Select2Widget,
            'parent'       : s2forms.Select2Widget,
            'assetcode'    : forms.TextInput(attrs={'style': 'text-transform:uppercase;', 'placeholder': 'Enter text without space & special characters'})
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['identifier'].initial = 'ASSET'
        self.fields['identifier'].widget.attrs = {"style": "display:none;"}
        utils.initailize_form_fields(self)

class SmartPlaceForm(AssetForm):
    required_css_class = "required"

    tempcode       = None
    service        = None
    sfdate         = None
    stdate         = None
    msn            = None
    yom            = None
    bill_val       = None
    bill_date      = None
    purachase_date = None
    inst_date      = None
    po_number      = None
    far_asset_id   = None
    invoice_date   = None
    invoice_no     = None
    supplier       = None
    meter          = None
    model          = None
    subcategory    = None
    category       = None
    unit           = None
    brand          = None

    class Meta(AssetForm.Meta):
        exclude = ['capacity']

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['identifier'].initial = 'SMARTPLACE'
        self.fields['identifier'].widget.attrs = {"style": "display:none;"}
        self.fields['parent'].queryset = am.Asset.objects.filter(
            Q(identifier='SMARTPLACE') & Q(enable = True) | Q(assetcode='NONE'))
        utils.initailize_form_fields(self)

class LocationForm(AssetForm):
    required_css_class = "required"

    tempcode       = None
    service        = None
    sfdate         = None
    stdate         = None
    msn            = None
    yom            = None
    bill_val       = None
    bill_date      = None
    purachase_date = None
    inst_date      = None
    po_number      = None
    far_asset_id   = None
    invoice_date   = None
    invoice_no     = None
    supplier       = None
    meter          = None
    model          = None
    subcategory    = None
    category       = None
    unit           = None
    brand          = None
    iscritical     = None

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['identifier'].initial = 'LOCATION'
        self.fields['identifier'].widget.attrs = {"style": "display:none;"}
        utils.initailize_form_fields(self)

class CheckpointForm(AssetForm):
    required_css_class = "required"

    tempcode       = None
    service        = None
    sfdate         = None
    stdate         = None
    msn            = None
    yom            = None
    bill_val       = None
    bill_date      = None
    purachase_date = None
    inst_date      = None
    po_number      = None
    far_asset_id   = None
    invoice_date   = None
    invoice_no     = None
    supplier       = None
    meter          = None
    model          = None
    subcategory    = None
    category       = None
    unit           = None
    brand          = None

    class Meta(AssetForm.Meta):
        exclude = ['capacity']

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['identifier'].initial = 'CHECKPOINT'
        self.fields['identifier'].widget.attrs = {"style": "display:none"}
        self.fields['parent'].queryset = am.Asset.objects.filter(
            Q(identifier='CHECKPOINT') & Q(enable = True) | Q(assetcode='NONE'))
        utils.initailize_form_fields(self)

class JobForm(forms.ModelForm):

    DURATION_CHOICES = [
        ('MIN', 'Minutes'),
        ('HRS', 'Hours'),
        ('WEEK', 'Week'),
        ('DAY', 'Day'), ]

    freq_duration = forms.ChoiceField(
        choices = DURATION_CHOICES, required = False, initial='MIN', widget = s2forms.Select2Widget)
    freq_duration2 = forms.ChoiceField(
        choices = DURATION_CHOICES, required = False, initial='MIN', widget = s2forms.Select2Widget)

    class Meta:
        model = am.Job
        fields = ['jobname', 'jobdesc', 'fromdate', 'uptodate', 'cron','sgroup',
                    'identifier', 'planduration', 'gracetime', 'expirytime',
                    'asset', 'priority', 'qset', 'pgroup', 'geofence', 'parent',
                     'seqno', 'client', 'bu', 'starttime', 'endtime', 'ctzoffset',
                    'frequency',  'scantype', 'ticketcategory', 'people', 'shift']

        labels = {
            'jobname'   : 'Name',         'jobdesc'     : 'Description',     'fromdate'      : 'Valid From',
            'uptodate' : 'Valid To',     'cron'        : 'Cron Expression', 'ticketcategory': 'Ticket Catgory',
            'grace_time': 'Grace Time',   'planduration': 'Plan Duration',   'scan_type'      : 'Scan Type',
            'priority'  : 'Priority',     'people'    : 'People',          'pgroup'        : 'Group',          
            'qset_id'   : 'Question Set', 'shift'       : "Shift",           'asset'        : 'Asset',
        }

        widgets = {
            'ticketcategory': s2forms.Select2Widget,
            'scantype'      : s2forms.Select2Widget,
            'shift'         : s2forms.Select2Widget,
            'pgroup'        : s2forms.Select2Widget,
            'asset'         : s2forms.Select2Widget,
            'priority'      : s2forms.Select2Widget,
            'jobdesc'       : forms.Textarea(attrs={'rows': 1, 'cols': 40}),
            'fromdate'      : forms.DateTimeInput,
            'uptodate'      : forms.DateTimeInput,
            'ctzoffset'     : forms.NumberInput(attrs={"style": "display:none;"}),
            'qset'          : s2forms.Select2Widget,
            'people'        : s2forms.Select2Widget,
            'bu'            : s2forms.Select2Widget,
        }

    def clean_from_date(self):
        if val := self.cleaned_data.get('fromdate'):
            return self._extracted_from_clean_upto_date_3(val)

    def clean_upto_date(self):
        if val := self.cleaned_data.get('uptodate'):
            return self._extracted_from_clean_upto_date_3(val)

    # TODO Rename this here and in `clean_from_date` and `clean_upto_date`
    @staticmethod
    def _extracted_from_clean_upto_date_3(val):
        val = utils.to_utc(val)
        ic('cleaned')
        return val

    @staticmethod
    def clean_slno():
        ic('cleaned')
        return -1

    def clean(self):
        cd = super().clean()
        ic('cleaned')
        self.instance.jobdesc = f'{cd.get("bu")} - {cd.get("jobname")}'

class JobNeedForm(forms.ModelForm):
    class Meta:
        model = am.Jobneed
        fields = ['identifier', 'frequency', 'parent', 'jobdesc', 'asset', 'ticketcategory',
                  'qset',  'people', 'pgroup', 'priority', 'scantype', 'multifactor',
                  'jobstatus', 'plandatetime', 'expirydatetime', 'gracetime', 'starttime',
                  'endtime', 'performedby', 'gpslocation', 'cuser', 'raisedby', 'remarks', 'ctzoffset']
        widgets = {
            'ticketcategory': s2forms.Select2Widget,
            'scantype'      : s2forms.Select2Widget,
            'pgroup'        : s2forms.Select2Widget,
            'people'        : s2forms.Select2Widget,
            'qset'          : s2forms.ModelSelect2Widget(model = am.QuestionSet, search_fields = ['qset_name__icontains']),
            'asset'         : s2forms.ModelSelect2Widget(model = am.Asset, search_fields = ['assetname__icontains']),
            'priority'      : s2forms.Select2Widget,
            'jobdesc'       : forms.Textarea(attrs={'rows': 1, 'cols': 40}),
            'remarks'       : forms.Textarea(attrs={'rows': 2, 'cols': 40}),
            'jobstatus'     : s2forms.Select2Widget,
            'performedby'   : s2forms.Select2Widget,
            'gpslocation'   : forms.TextInput
        }
        label = {
            'endtime': 'End Time'
        }

class AdhocTaskForm(JobNeedForm):
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    class Meta(JobNeedForm.Meta):
        labels = {
            'asset': 'Asset/SmartPlace',
            'starttime': 'Start Time',
            'plandatetime': 'Plan DateTime',
            'expirydatetime': 'Expity DateTime',
            'endtime': 'End Time',
            'gracetime': 'Grace Time',
            'jobstatus': 'Task Status',
            'scantype': 'ScanType',
            'gpslocation': 'GPS Location',
            'ticketcategory': 'Ticket Category',
            'performedby': 'Performed By',
            'people': 'People',
            'qset': 'Question Set',
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        from django.conf import settings
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['plandatetime'].input_formats  = settings.DATETIME_INPUT_FORMATS
        self.fields['expirydatetime'].input_formats  = settings.DATETIME_INPUT_FORMATS
        utils.initailize_form_fields(self)

class TicketForm(forms.ModelForm):
    class Meta:
        model = am.Ticket
        fields = ['ticketno', 'ticketdesc', 'assignedtopeople',
                  'assignedtogroup', 'priority', 'status', 'performedby', 'comments', 'ticketlog']
        labels = {
            'ticketno'  : 'Ticket No',
            'ticketdesc': 'Description',
            'assignedtopeople': 'People',
            'assignedtogroup': 'Group',
            'priority': 'Priority',
            'status': 'Status',
            'performedby': 'Performed By',
            'comments': 'comments',
            'ticketlog': 'ticketlog'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].queryset = om.TypeAssist.objects.filter(Q(tatype__tacode='TICKETSTATUS') )
        self.fields["priority"].queryset = om.TypeAssist.objects.filter(tatype__tacode='PRIORITY')
        utils.initailize_form_fields(self)

# create a ModelForm
class EscalationForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = am.EscalationMatrix
        fields = ['level', 'assignedfor',  'assignedperson', 'ctzoffset',
                  'assignedgroup', 'frequency', 'frequencyvalue', 'body']
        labels = {
            'level': 'Level',
            'assignedfor': 'Assigned To',
            'assignedperson': 'People',
            'assignedgroup': 'Group',
            'frequency': 'Frequency',
            'frequencyvalue': 'Value',
            'body': 'Body',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)



class WorkPermit(forms.ModelForm):
    required_css_class = "required"
    class Meta:
        model = am.WorkPermit
        fields = ['wptype', 'seqno']
        labels={
            'wptype':'Permit to work',
            'seqno':'Seq No'
        }
        widgets = {
            'wptype':s2forms.Select2Widget
        }
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['wptype'].queryset = am.QuestionSet.objects.filter(type='WORKPERMITTEMPLATE')
