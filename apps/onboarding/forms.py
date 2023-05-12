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
from django.contrib.gis.geos import GEOSGeometry
from django.http import QueryDict
from apps.peoples.utils import create_caps_choices_for_clientform
import re
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
        fields = ['tacode' , 'taname', 'tatype', 'ctzoffset', 'enable']
        labels = {
                'tacode': 'Code',
                'taname': 'Name',
                'tatype': 'Type',
                'enable':'Enable'}
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
        self.fields['enable'].initial = True

    def is_valid(self) -> bool:

        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

    def clean_tatype(self):
        return self.cleaned_data.get('tatype')

    def clean_tacode(self):
        value = self.cleaned_data.get('tacode')
        regex = "^[a-zA-Z0-9\-_]*$"
        if " " in value: raise forms.ValidationError(self.error_msg['invalid_code'])
        if  not re.match(regex, value):
            raise forms.ValidationError(self.error_msg['invalid_code2'])
        if value.endswith('.'):
            raise forms.ValidationError(self.error_msg['invalid_code3'])
        return value.upper()

class TypeAssistForm(SuperTypeAssistForm): 
    required_css_class = "required"

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['enable'].initial = True
        ic(obm.TypeAssist.objects.filter(enable = True, client_id__in =  [S['client_id'], 1]))
        self.fields['tatype'].queryset = obm.TypeAssist.objects.filter((Q(cuser__is_superuser = True) | Q(client_id__in =  [S['client_id'], 1])), enable=True )
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result
    
    def clean(self):
        super().clean()
        ic(self.cleaned_data['tatype'])

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
        'invalid_latlng'  : "Please enter a correct gps coordinates.",
        'invalid_permissibledistance':"Please enter a correct value for Permissible Distance",
        'invalid_solid': "Please enter a correct value for Sol id",
    }
    parent = forms.ModelChoiceField(label='Belongs to', required = False, widget = s2forms.Select2Widget, queryset = obm.Bt.objects.all())
    controlroom = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, required=False, label='Control Room')
    permissibledistance = forms.IntegerField(required=False, label='Permissible Distance')
    address = forms.CharField(required=False, label='Address', max_length=500, widget=forms.Textarea(attrs={'rows': 2, 'cols': 15}))
    
    class Meta:
        model  = obm.Bt
        fields = ['bucode', 'buname', 'parent', 'butype', 'identifier', 'siteincharge',
                'iswarehouse', 'isserviceprovider', 'isvendor', 'enable', 'ctzoffset',
                'gpsenable', 'skipsiteaudit', 'enablesleepingguard', 'deviceevent', 'solid']

        labels = {
            'bucode'             : 'Code',
            'buname'             : 'Name',
            'butype'             : 'Site Type',
            'identifier'         : 'Type',
            'iswarehouse'        : 'Warehouse',
            'isenable'           : 'Enable',
            'isvendor'           : 'Vendor',
            'isserviceprovider' : 'Service Provider',
            'gpsenable'          : 'GPS Enable', 
            'skipsiteaudit'      : 'Skip Site Audit',
            'enablesleepingguard': 'Enable Sleeping Guard',
            'deviceevent'        : 'Device Event Log',
            'solid'        : 'Sol Id',
            'siteincharge':'Site Manager'   
        }

        widgets = { 
            'bucode'      : forms.TextInput(attrs={'style': 'text-transform:uppercase;', 'placeholder': 'Enter text without space & special characters'}),
            'buname'      : forms.TextInput(attrs={'placeholder': 'Name'}),
            'identifier'  : s2forms.Select2Widget,
            'butype'      : s2forms.Select2Widget}    

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.client = kwargs.pop('client', False)
        self.request = kwargs.pop('request', False)
        ic(self.request)
        S = self.request.session
        super().__init__(*args, **kwargs)
        if self.client:
            self.fields['identifier'].initial = obm.TypeAssist.objects.get(tacode='CLIENT').id
            self.fields['identifier'].required= True
        
        self.fields['siteincharge'].initial = 1
        #filters for dropdown fields
        self.fields['identifier'].queryset = obm.TypeAssist.objects.filter(Q(tacode='CLIENT') if self.client else Q(tatype__tacode="BVIDENTIFIER"))
        self.fields['butype'].queryset = obm.TypeAssist.objects.filter(tatype__tacode="SITETYPE", client_id = S['client_id'])
        qset = obm.Bt.objects.get_whole_tree(self.request.session['client_id'])
        self.fields['parent'].queryset = obm.Bt.objects.filter(id__in = qset)
        self.fields['controlroom'].choices = pm.People.objects.controlroomchoices(self.request)
        self.fields['siteincharge'].queryset = pm.People.objects.filter(Q(peoplecode ='NONE') | (Q(client_id = self.request.session['client_id']) & Q(enable=True) & Q(isverified=True)))
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result


    def clean(self):
        super().clean()
        
        from .utils import create_bv_reportting_heirarchy
        newcode = self.cleaned_data.get('bucode')
        newtype = self.cleaned_data.get('identifier')
        parent= self.cleaned_data.get('parent')
        instance = self.instance
        if newcode and newtype and instance:
            create_bv_reportting_heirarchy(instance, newcode, newtype, parent)
        if self.cleaned_data.get('gpslocation'):
            data = QueryDict(self.request.POST['formData'])
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        return self.cleaned_data


    def clean_bucode(self):
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        if value := self.cleaned_data.get('bucode'):
            regex = "^[a-zA-Z0-9\-_]*$"
            if " " in value: raise forms.ValidationError(self.error_msg['invalid_bucode'])
            if  not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_bucode2'])
            if value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_bucode3'])
            return value.upper()

    def clean_gpslocation(self, val):
        if gps := val:
            if gps == 'NONE': return GEOSGeometry(f'SRID=4326;POINT({0.0} {0.0})')
            regex = '^([-+]?)([\d]{1,2})(((\.)(\d+)(,)))(\s*)(([-+]?)([\d]{1,3})((\.)(\d+))?)$'
            gps = gps.replace('(', '').replace(')', '')
            if not re.match(regex, gps):
               raise forms.ValidationError(self.error_msg['invalid_latlng'])
            gps.replace(' ', '')
            lat, lng = gps.split(',')
            gps = GEOSGeometry(f'SRID=4326;POINT({lng} {lat})')
        return gps
    
    def clean_permissibledistance(self):
        if val := self.cleaned_data.get('permissibledistance'):
            regex = "^[0-9]*$"
            if not re.match(regex, str(val)):
                raise forms.ValidationError(self.error_msg['invalid_permissibledistance'])
            if val < 0:
                raise forms.ValidationError(self.error_msg['invalid_permissibledistance'])
        return val

    def clean_solid(self):
        if val:=self.cleaned_data.get('solid'):
            regex = "^[a-zA-Z0-9]*$"
            if not re.match(regex, str(val)):
                raise forms.ValidationError(self.error_msg['invalid_solid'])
        return val



class ShiftForm(forms.ModelForm):
    required_css_class = 'required'
    error_msg = {
        'invalid_code' : "Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
        'max_hrs_exceed': "Maximum hours in a shift cannot be greater than 12hrs",
        "min_hrs_required": "Minimum hours of a shift should be atleast 5hrs"
    }
    shiftduration = forms.CharField(widget = forms.TextInput(attrs={'readonly':True}), label="Duration", required = False)

    class Meta:
        model = obm.Shift
        fields = ['shiftname', 'starttime', 'endtime', 'ctzoffset',
        'nightshiftappicable', 'shiftduration', 'designation', 'captchafreq', 'peoplecount', ]
        labels={
            'shiftname'  : 'Shift Name',
            'starttime'  : 'Start Time',
            'endtime'    : 'End Time',
            'captchafreq': 'Captcha Frequency',
            'designation': "Designation",
            'peoplecount': "People Count",
        }
        widgets ={
            'shiftname':forms.TextInput(attrs={'placeholder': "Enter shift name"}),
            'nightshiftappicable':forms.CheckboxInput(attrs={'onclick': "return false"}),
            'designation': s2forms.Select2Widget
        }

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['nightshiftappicable'].initial = False
        
        self.fields['designation'].queryset = obm.TypeAssist.objects.filter(tatype__tacode='DESIGNATION', client_id__in = [S['client_id'], 1])
        utils.initailize_form_fields(self)

    def clean_shiftname(self):
        if val := self.cleaned_data.get('shiftname'):
            return val

    def clean_shiftduration(self):
        if val := self.cleaned_data.get('shiftduration'):
            h, m = val.split(',')
            hrs = int(h.replace("Hrs", ""))
            mins = int(m.replace("min", ""))
            if hrs > 12:
                raise forms.ValidationError(self.error_msg['max_hrs_exceed'])
            if hrs < 5:
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
    required_css_class = 'required'
    class Meta:
        model = obm.GeofenceMaster
        fields = ['gfcode', 'gfname', 'alerttopeople', 'bu',
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
        self.fields['alerttogroup'].required = True
        self.fields['bu'].queryset = obm.Bt.objects.filter(id__in = self.request.session['assignedsites'])
        self.fields['alerttopeople'].required = True
        self.fields['alerttext'].required = True
        self.fields['bu'].required = False
        utils.initailize_form_fields(self)

    def clean_gfcode(self):
        return val.upper() if (val := self.cleaned_data.get('gfcode')) else val
#========================================== END MODEL FORMS =======================================#

#========================================== START JSON FORMS =======================================#
class BuPrefForm(forms.Form):
    required_css_class = "required"

    mobilecapability         = forms.MultipleChoiceField(required = False, label="Mobile Capability", widget = s2forms.Select2MultipleWidget)
    webcapability            = forms.MultipleChoiceField(required = False, label="Web Capability", widget = s2forms.Select2MultipleWidget)
    reportcapability         = forms.MultipleChoiceField(required = False, label="Report Capability", widget = s2forms.Select2MultipleWidget)
    portletcapability        = forms.MultipleChoiceField(required = False, label="Portlet Capability", widget = s2forms.Select2MultipleWidget)
    validimei                = forms.CharField(max_length = 15, required = False,label="IMEI No.")
    validip                  = forms.CharField(max_length = 15, required = False, label="IP Address")
    usereliver               = forms.BooleanField(initial = False, required = False, label="Reliver needed?")
    malestrength             = forms.IntegerField(initial = 0, label="Male Strength")
    femalestrength           = forms.IntegerField(initial = 0, label="Female Strength")
    reliveronpeoplecount     = forms.IntegerField(initial = 0, label="Reliver On People Count", required=False)
    pvideolength             = forms.IntegerField(initial="10", label='Panic Video Length (sec)')
    guardstrenth             = forms.IntegerField(initial = 0)
    siteclosetime            = forms.TimeField(label="Site Close Time", required = False)
    tag                      = forms.CharField(max_length = 200, required = False)
    siteopentime             = forms.TimeField(required = False, label="Site Open Time")
    nearby_emergencycontacts = forms.CharField(max_length = 500, required = False)
    ispermitneeded = forms.BooleanField(initial = False, required=False)



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
        web, mob, portlet, report = create_caps_choices_for_clientform()
        ic(web)
        self.fields['webcapability'].choices = web
        self.fields['mobilecapability'].choices = mob
        self.fields['reportcapability'].choices = report
        self.fields['portletcapability'].choices = portlet
    
    def clean(self):
        ic("called")
        cleaned_data = super().clean()
        if not cleaned_data.get('mobilecapability') and not cleaned_data.get('webcapability'):
            msg = "Please select atleast one capability"
            self.add_error("mobilecapability", msg)
            self.add_error("webcapability", msg)
        #if usereliver is checked then reliveronpeoplecount should be greater than 0
        if cleaned_data.get('usereliver') and cleaned_data.get('reliveronpeoplecount') <= 0:
            ic(cleaned_data.get('usereliver'), cleaned_data.get('reliveronpeoplecount'))
            self.add_error('reliveronpeoplecount', "Reliver on people count should be greater than 0")
    
    
    def clean_validip(self):
        if val := self.cleaned_data.get('validip'):
            #check if ip is valid
            text = val.split('.')
            if len(text) != 4:
                raise forms.ValidationError("Invalid IP Address")
        return val
    
    def clean_validimei(self):
        if val := self.cleaned_data.get('validimei'):
            #check if imei is valid
            if  not utils.isValidEMEI(val):
                raise forms.ValidationError("Invalid IMEI No.")
        return val

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

#========================================== END JSON FORMS =======================================#

class ImportForm(forms.Form):
    TABLECHOICES = [
        ('PEOPLE', 'People'),
        ('BU', 'Business Unit'),
        ('SHIFT', 'Shift'),
        ('ASSET', 'Asset'),
        ('QUESTION', 'Question'),
        ('PEOPLEGROUP', 'People Group'),
        ('SITEGROUP', 'Site Group'),
        ('TYPEASSIST', 'TypeAssist'),
        ('CAPABILITY', 'Capability'),
    ]
    importfile = forms.FileField(required = True, label='Import File', max_length = 50, allow_empty_file = False)
    table = forms.ChoiceField(required = True, choices = TABLECHOICES, label='Select Type of Data', initial='TYPEASSISTS', widget=s2forms.Select2Widget)

    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)


