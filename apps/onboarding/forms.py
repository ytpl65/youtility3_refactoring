# from standard library

# from django core
from django import forms
from django.db.models.query_utils import Q
from django.utils.translation import gettext_lazy as _
from apps.core import utils
# from thirdparty apps and packages
from icecream import ic
from django_select2 import forms as s2forms
# from this project
import apps.onboarding.models as obm # onboarding-models
from apps.peoples import models as pm # onboarding-utils

#========================================= BEGIN MODEL FORMS ======================================#

class SuperTypeAssistForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_code' : "(Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
    }
    class Meta:
        model  = obm.TypeAssist
        fields = ['tacode' , 'taname', 'tatype', 'ctzoffset']
        labels = {
                'tacode': 'Code',
                'taname': 'Name',
                'tatype': 'Type'}
        widgets = {
            'tatype':s2forms.Select2Widget,
            'tacode':forms.TextInput(attrs={'placeholder': 'Enter code without space and special characters', 'style': "text-transform: uppercase;"}),
            'taname':forms.TextInput(attrs={'placeholder': "Enter name"}),
            }

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.request = kwargs.pop('request', None)
        super(SuperTypeAssistForm, self).__init__(*args, **kwargs)
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:

        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

    def clean_tatype(self):
        return self.cleaned_data.get('tatype')

    def clean_tacode(self):
        import re
        value = self.cleaned_data.get('tacode')
        regex = "^[a-zA-Z0-9\-_]*$"
        if " " in value: raise forms.ValidationError(self.error_msg['invalid_code'])
        elif  not re.match(regex, value):
            raise forms.ValidationError(self.error_msg['invalid_code2'])
        elif value.endswith('.'):
            raise forms.ValidationError(self.error_msg['invalid_code3'])
        return value.upper()

class TypeAssistForm(SuperTypeAssistForm): 
    required_css_class = "required"

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

    def clean_tacode(self):
        super().clean_tacode()
        if val:= self.cleaned_data.get('tacode'):
            val = val.upper()
            if len(val)>25: raise forms.ValidationError("Max Length reached!!")
        return val



class BtForm(forms.ModelForm):  
    required_css_class = "required"
    error_msg = {
        'invalid_bucode'  : 'Spaces are not allowed in [Code]',
        'invalid_bucode2' : "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_bucode3' : "[Invalid code] Code should not endwith '.' ",
        'invalid_latlng'  : "Please enter a correct gps coordinates."
    }
    parent = forms.ModelChoiceField(label='Belongs to', required = False, widget = s2forms.Select2Widget, queryset = obm.Bt.objects.all())
    class Meta:
        model  = obm.Bt
        fields = ['bucode', 'buname', 'parent', 'butype', 'gpslocation', 'identifier',
                'iswarehouse', 'isserviceprovider', 'isvendor', 'enable', 'ctzoffset',
                'gpsenable', 'skipsiteaudit', 'enablesleepingguard', 'deviceevent']

        labels = {
            'bucode'             : 'Code',
            'buname'             : 'Name',
            'butype'             : 'Site Type',
            'identifier'         : 'Type',
            'iswarehouse'        : 'Warehouse',
            'gpslocation'        : 'GPS Location',
            'isenable'           : 'Enable',
            'isvendor'           : 'Vendor',
            'isserviceprovider' : 'Service Provider',
            'gpsenable'          : 'GPS Enable', 
            'skipsiteaudit'      : 'Skip Site Audit',
            'enablesleepingguard': 'Enable Sleeping Guard',
            'deviceevent'        : 'Device Event Log',
        }

        widgets = { 
            'bucode'      : forms.TextInput(attrs={'style': 'text-transform:uppercase;', 'placeholder': 'Enter text without space & special characters'}),
            'buname'      : forms.TextInput(attrs={'placeholder': 'Name'}),
            'identifier'      : s2forms.Select2Widget,
            'butype'      : s2forms.Select2Widget,
            'gpslocation' : forms.TextInput(attrs={'placeholder': 'GPS Location'}),}    

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.client = kwargs.pop('client', False)
        self.request = kwargs.pop('request', False)
        super().__init__(*args, **kwargs)
        if self.client:
            self.fields['identifier'].initial = obm.TypeAssist.objects.get(tacode='CLIENT').id
        self.fields['identifier'].queryset = obm.TypeAssist.objects.filter(Q(tacode='CLIENT') if self.client else Q(tatype__tacode="BVIDENTIFIER"))
        self.fields['identifier'].required= True
        self.fields['butype'].queryset = obm.TypeAssist.objects.filter(tatype__tacode="SITETYPE")
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result


    def clean(self):
        cleaned_data = super().clean()
        from .utils import create_bv_reportting_heirarchy
        newcode = cleaned_data.get('bucode')
        newtype = cleaned_data.get('identifier')
        parent= cleaned_data.get('parent')
        instance = self.instance
        ic(newcode, newtype, instance)
        ic(instance.bucode)
        if newcode and newtype and instance:
            ic(newcode)
            create_bv_reportting_heirarchy(instance, newcode, newtype, parent)


    def clean_bucode(self):
        import re
        ic(self.cleaned_data)
        if value := self.cleaned_data.get('bucode'):
            regex = "^[a-zA-Z0-9\-_]*$"
            if " " in value: raise forms.ValidationError(self.error_msg['invalid_bucode'])
            elif  not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_bucode2'])
            elif value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_bucode3'])
            return value.upper()

    def clean_gpslocation(self):
        import re
        if gps := self.cleaned_data.get('gpslocation'):
            regex = '^([-+]?)([\d]{1,2})(((\.)(\d+)(,)))(\s*)(([-+]?)([\d]{1,3})((\.)(\d+))?)$'
            if not re.match(regex, gps):
                raise forms.ValidationError(self.error_msg['invalid_latlng'])
            return gps

    def clean_buname(self):
        if val := self.cleaned_data.get('buname'):
            return val.upper()


class ShiftForm(forms.ModelForm):
    required_css_class = 'required'
    error_msg = {
        'invalid_code' : "Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
        'max_hrs_exceed': "Maximum hours in a shift cannot be greater than 12hrs",
        "min_hrs_required": "Minimum hours of a shift should be atleast 5hrs"
    }
    shiftduration = forms.CharField(widget = forms.TextInput(attrs={'readonly':True}), required = False)

    class Meta:
        model = obm.Shift
        fields = ['shiftname', 'starttime', 'endtime', 'ctzoffset',
        'nightshiftappicable', 'shiftduration', 'captchafreq']
        labels={
            'shiftname': 'Shift Name',
            'starttime': 'Start Time',
            'endtime': 'End Time',
            'capcthafreq': 'Captcha Frequency'
        }
        widgets ={
            'shiftname':forms.TextInput(attrs={'placeholder': "Enter shift name"}),
            'nightshiftappicable':forms.CheckboxInput(attrs={'onclick': "return false"})
        }

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['nightshiftappicable'].initial = False
        utils.initailize_form_fields(self)

    def clean_shiftname(self):
        if val := self.cleaned_data.get('shiftname'):
            return val.upper()

    def clean_shiftduration(self):
        if val := self.cleaned_data.get('shiftduration'):
            h, m = val.split(',')
            hrs = int(h.replace("Hrs", ""))
            mins = int(m.replace("min", ""))
            if hrs > 12:
                raise forms.ValidationError(self.error_msg['max_hrs_exceed'])
            elif hrs < 5:
                raise forms.ValidationError(self.error_msg['min_hrs_required'])
            return hrs*60+mins

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result



class SitePeopleForm(forms.ModelForm):
    required_css_class = 'required'
    error_msg = {
        'invalid_code' : "Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
    }
    class Meta:
        model = obm.SitePeople
        fields = ['contract', 'people', 'worktype', 'shift',
                 'reportto', 'webcapability', 'mobilecapability',
                'reportcapability', 'fromdt', 'uptodt', 'siteowner',
                'enable', 'enablesleepingguard', 'ctzoffset']

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)


class ContractForm(forms.ModelForm):
    class Meta:
        model = obm.Contract
        fields = []

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super(ContractForm, self).__init__(*args, **kwargs)
        utils.initailize_form_fields(self)


class ContractDetailForm(forms.ModelForm):
    class Meta:
        model = obm.ContractDetail
        fields = []

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)


class GeoFenceForm(forms.ModelForm):
    class Meta:
        model = obm.GeofenceMaster
        fields = ['gfcode', 'gfname', 'alerttopeople',
                  'alerttogroup', 'alerttext', 'enable', 'ctzoffset']
        labels = {
            'gfcode': 'Code', 'gfname': 'Name', 'alerttopeople': 'Alert to People',
            'alerttogroup': 'Alert to Group', 'alerttext': 'Alert Text'
        }
        widgets = {
            'gfcode':forms.TextInput(attrs={'style': 'text-transform:uppercase;', 'placeholder': 'Enter text without space & special characters'})
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)

    def clean_gfcode(self):
        return val.upper() if (val := self.cleaned_data.get('gfcode')) else val
#========================================== END MODEL FORMS =======================================#

#========================================== START JSON FORMS =======================================#
class BuPrefForm(forms.Form):
    required_css_class = "required"

    mobilecapability        = forms.MultipleChoiceField(required = False, label="Mobile Capability", widget = s2forms.Select2MultipleWidget)
    webcapability           = forms.MultipleChoiceField(required = False, label="Web Capability", widget = s2forms.Select2MultipleWidget)
    reportcapability        = forms.MultipleChoiceField(required = False, label="Report Capability", widget = s2forms.Select2MultipleWidget)
    portletcapability       = forms.MultipleChoiceField(required = False, label="Portlet Capability", widget = s2forms.Select2MultipleWidget)
    validimei                = forms.CharField(max_length = 15, required = False,label="IMEI No.")
    validip                  = forms.CharField(max_length = 15, required = False, label="IP Address")
    usereliver               = forms.BooleanField(initial = False, required = False, label="Reliver needed?")
    malestrength             = forms.IntegerField(initial = 0, label="Male Strength")
    femalestrength           = forms.IntegerField(initial = 0, label="Female Strength")
    reliveronpeoplecount     = forms.IntegerField(initial = 0, label="Reliver On People Count")
    pvideolength             = forms.IntegerField(initial="10", label='Panic Video Length (sec)')
    guardstrenth             = forms.IntegerField(initial = 0)
    siteclosetime            = forms.TimeField(label="Site Close Time", required = False)
    tag                      = forms.CharField(max_length = 200, required = False)
    siteopentime             = forms.TimeField(required = False, label="Site Open Time")
    nearby_emergencycontacts = forms.CharField(max_length = 500, required = False)



    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result

class ClentForm(BuPrefForm):
    femalestrength = None
    guardstrenth = None
    malestrength = None

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.session = kwargs.pop('session', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        from apps.peoples.utils import get_caps_choices
        self.fields['webcapability'].choices = get_caps_choices(cfor = pm.Capability.Cfor.WEB)
        self.fields['mobilecapability'].choices = get_caps_choices(cfor = pm.Capability.Cfor.MOB)
        self.fields['reportcapability'].choices = get_caps_choices(cfor = pm.Capability.Cfor.REPORT)
        self.fields['portletcapability'].choices = get_caps_choices(cfor = pm.Capability.Cfor.PORTLET)


    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

#========================================== END JSON FORMS =======================================#

class ImportForm(forms.Form):
    TABLECHOICES = [
        ('PEOPLES', 'Peoples'),
        ('BU', 'Buisiness Units'),
        ('SHIFTS', 'Shifts'),
        ('ASSETS', 'Assets'),
        ('QUESTIONS', 'Questions'),
        ('PEOPLEGROUPS', 'People Groups'),
        ('SITEGROUPS', 'Site Groups'),
        ('TYPEASSISTS', 'TypeAssists'),
    ]

    importfile = forms.FileField(required = True, label='Import File', max_length = 50, allow_empty_file = False)
    table = forms.ChoiceField(required = True, choices = TABLECHOICES, label='Select Type of Data', initial='TYPEASSISTS')

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)


