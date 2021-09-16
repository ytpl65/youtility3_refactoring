#from standard library

#from django core
from apps.onboarding.utils import get_webcaps_choices
from django import forms
from django.forms import widgets
from django.utils.translation import gettext_lazy as _

#from thirdparty apps and packages
from icecream import ic

#from this project
from apps.onboarding.models import Bt, Contract, ContractDetail, Shift, SitePeople, TypeAssist


#========================================= BEGIN MODEL FORMS ======================================#

class TypeAssistForm(forms.ModelForm): 
    required_css_class = "required"
    error_msg = {
        'invalid_code' : "Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
    }
    tatype = forms.ModelChoiceField(queryset=TypeAssist.objects.filter(parent__tacode='NONE'))
    
    class Meta:
        model  = TypeAssist
        fields = ['tacode' ,'taname',  'parent', 'tatype']
        labels = {
                'tacode': 'Code',
                'tatype': 'Type',
                'taname': 'Name',
                'parent': 'Parent'}
        widgets =  {
            'tacode':forms.TextInput(
                attrs={'placeholder':"Code", 'style':"  text-transform: uppercase;"}
                ),
            'taname':forms.TextInput(attrs={'placeholder':"Enter name"})}

    
    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super(TypeAssistForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select']:
                visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                 visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type == 'select':
                visible.field.widget.attrs['class']            = 'form-select'
                visible.field.widget.attrs['data-control']     = 'select2'
                visible.field.widget.attrs['data-placeholder'] = 'Select an option'

    
    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result

    def clean_tatype(self):
        val = self.cleaned_data.get('tatype')
        return val
    
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
    
    def clean_taname(self):
        val = self.cleaned_data.get('taname')
        if val: return val.upper()

    

class BtForm(forms.ModelForm):  
    required_css_class = "required"
    error_msg = {
        'invalid_bucode'  : 'Spaces are not allowed in [Code]',
        'invalid_bucode2' : "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_bucode3' : "[Invalid code] Code should not endwith '.' ",
        'invalid_latlng'  : "Please enter a correct gps coordinates."
    }
    parent = forms.ModelChoiceField(label='Belongs to', required=True, queryset=Bt.objects.all())
    class Meta:
        model  = Bt
        fields = ['bucode', 'buname', 'parent', 'butype', 'gpslocation',
                'iswarehouse', 'is_serviceprovider', 'isvendor', 'enable',
                'gpsenable', 'skipsiteaudit', 'enablesleepingguard', 'deviceevent']
        
        labels = {
            'bucode'             : 'Code',
            'buname'             : 'Name',
            'butype'             : 'Type',
            'iswarehouse'        : 'Warehouse',
            'gpslocation'        : 'GPS Location',
            'isenable'           : 'Enable',
            'isvendor'           : 'Vendor',
            'is_serviceprovider' : 'Service Provider',
            'gpsenable'          : 'GPS Enable', 
            'skipsiteaudit'      : 'Skip Site Audit',
            'enablesleepingguard': 'Enable Sleeping Guard',
            'deviceevent'        : 'Device Event Log',
        }
        
        widgets = { 
            'bucode'      : forms.TextInput(attrs={'style':'text-transform:uppercase;', 'placeholder':'Code'}),
            'buname'      : forms.TextInput(attrs={'placeholder':'Name'}),
            'butype'      : forms.Select(attrs={'placeholder':'Type'}),
            'gpslocation' : forms.TextInput(attrs={'placeholder':'GPS Location'}),}    
    
    
    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super(BtForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                 visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type in ['select', 'selectmultiple']:
                visible.field.widget.attrs['class']            = 'form-select'
                visible.field.widget.attrs['data-control']     = 'select2'
                visible.field.widget.attrs['data-placeholder'] = 'Select an Option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'
    
    
    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result

    
    def clean(self):
        super(BtForm, self).clean()
        from .utils import create_bt_tree
        
        parent= self.cleaned_data.get('parent')
        bucode = self.cleaned_data.get('bucode')
        butype = self.cleaned_data.get('butype')
        instance = self.instance
        ic(bucode)
        create_bt_tree(bucode, butype, instance, parent)
        
        
    
    def clean_bucode(self):
        import re
        value = self.cleaned_data.get('bucode')
        if value:
            regex = "^[a-zA-Z0-9\-_]*$"
            if " " in value: raise forms.ValidationError(self.error_msg['invalid_bucode'])
            elif  not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_bucode2'])
            elif value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_bucode3'])
            return value.upper()
    
    def clean_gpslocation(self):
        import re
        gps = self.cleaned_data.get('gpslocation')
        if gps:
            regex = '^([-+]?)([\d]{1,2})(((\.)(\d+)(,)))(\s*)(([-+]?)([\d]{1,3})((\.)(\d+))?)$'
            if not re.match(regex, gps):
                raise forms.ValidationError(self.error_msg['invalid_latlng'])
            return gps

    def clean_buname(self):
        val = self.cleaned_data.get('buname')
        if val: return val.upper()



class ShiftForm(forms.ModelForm):
    required_css_class = 'required'
    error_msg = {
        'invalid_code' : "Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
    }
    class Meta:
        model = Shift
        fields = ['shiftname', 'starttime', 'endtime', 'captchafreq']
        labels={
            'shiftname':'Shift Name',
            'starttime': 'Start Time',
            'endtime': 'End Time',
            'capcthafreq':'Captcha Frequency'
        }
        widgets ={
            'shiftname':forms.TextInput(attrs={'placeholder':"Enter shift name"})            
        }
     
    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super(ShiftForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'

    def clean_shiftname(self):
        val = self.cleaned_data.get('shiftname')
        if val: return val.upper()

            


class SitePeopleForm(forms.ModelForm):
    required_css_class = 'required'
    error_msg = {
        'invalid_code' : "Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
    }
    class Meta:
        model=SitePeople
        fields = ['contract_id', 'peopleid', 'worktype', 'shift',
                 'reportto', 'webcapability', 'mobilecapability',
                'reportcapability', 'fromdt', 'uptodt', 'siteowner',
                'enable', 'enablesleepingguard']
        
    
    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super(SitePeopleForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                 visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type in ['select', 'selectmultiple']:
                visible.field.widget.attrs['class']            = 'form-select'
                visible.field.widget.attrs['data-control']     = 'select2'
                visible.field.widget.attrs['data-placeholder'] = 'Select an Option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'



class ContractForm(forms.ModelForm):
    class Meta:
        model=Contract
        fields = []
    
    
    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super(ContractForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                 visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type in ['select', 'selectmultiple']:
                visible.field.widget.attrs['class']            = 'form-select'
                visible.field.widget.attrs['data-control']     = 'select2'
                visible.field.widget.attrs['data-placeholder'] = 'Select an Option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'



class ContractDetailForm(forms.ModelForm):
    class Meta:
        model=ContractDetail
        fields = []
    
    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super(ContractDetailForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                 visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type in ['select', 'selectmultiple']:
                visible.field.widget.attrs['class']            = 'form-select'
                visible.field.widget.attrs['data-control']     = 'select2'
                visible.field.widget.attrs['data-placeholder'] = 'Select an Option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'


#========================================== END MODEL FORMS =======================================#


#========================================== START JSON FORMS =======================================#
class BuPrefForm(forms.Form):
    required_css_class = "required"
    from .utils import get_webcaps_choices
    
    mobilecapability        = forms.MultipleChoiceField(required=False, label="Mobile Capability")
    webcapability           = forms.MultipleChoiceField(required=False, label="Web Capability")
    reportcapability        = forms.MultipleChoiceField(required=False, label="Report Capability")
    portletcapability       = forms.MultipleChoiceField(required=False, label="Portlet Capability")
    validimei                = forms.CharField(max_length=15, required=False,label="IMEI No.")
    validip                  = forms.CharField(max_length=15, required=False, label="IP Address")
    usereliver               = forms.BooleanField(initial=False, required=False, label="Reliver needed?")
    malestrength             = forms.IntegerField(initial=0, label="Male Strength")
    femalestrength           = forms.IntegerField(initial=0, label="Female Strength")
    reliveronpeoplecount     = forms.IntegerField(initial=0)
    pvideolength             = forms.IntegerField(initial="10", label='Panic video length (sec)')
    guardstrenth             = forms.IntegerField(initial=0)
    siteclosetime            = forms.TimeField(label="Site Close Time", required=False)
    tag                      = forms.CharField(max_length=200, required=False)
    siteopentime             = forms.TimeField(required=False, label="Site Open Time")
    nearby_emergencycontacts = forms.CharField(max_length=500, required=False)




    def __init__(self, *args, **kwargs):
        """Initializes form"""
        super(BuPrefForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                 visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type in ['select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-select'
                visible.field.widget.attrs['data-control'] = 'select2'
                visible.field.widget.attrs['data-placeholder'] = 'Select an option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'


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
        super(BuPrefForm, self).__init__(*args, **kwargs)
        from apps.peoples.utils import get_caps_choices
        self.fields['webcapability'].choices = get_caps_choices(cfor='WEB')
        self.fields['mobilecapability'].choices = get_caps_choices(cfor='MOB')
        self.fields['reportcapability'].choices = get_caps_choices(cfor='REPORT')
        self.fields['portletcapability'].choices = get_caps_choices(cfor='PORTLET')
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type in ['select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-select'
                visible.field.widget.attrs['data-control'] = 'select2'
                visible.field.widget.attrs['data-placeholder'] = 'Select an option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'


    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result

#========================================== END JSON FORMS =======================================#
