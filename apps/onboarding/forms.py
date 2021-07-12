#imports from standard library

#imports from django core
from django import forms
from django.forms import widgets
from django.utils.translation import ugettext_lazy as _
from django.core.validators import RegexValidator

#imports from thirdparty apps

#import from this project
from .models import TypeAssist, Bt


#========================================= BEGIN MODEL FORMS ======================================#

class TypeAssistForm(forms.ModelForm): 
    #error_css_class = "error"
    required_css_class = "required"
    
    
    class Meta:
        model  = TypeAssist
        fields = ['tacode' ,'taname', 'tatype', 'parent']
        labels = {
            'tacode': 'Code',
            'tatype': 'Type',
            'taname': 'Name',
            'parent': 'Parent'}

    
    def __init__(self, *args, **kwargs):
        super(TypeAssistForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile']:
                visible.field.widget.attrs['class'] = 'form-control'


    def clean_tacode(self):
        import re
        value = self.cleaned_data['tacode']
        regex = '[a-zA-Z0-9_\-]'
        if not re.search(regex, value):
            raise forms.ValidationError(f"[Invalid code] Only ('-', '_') special characters are allowed", code="invalid_code")
        return value.upper()



class BtForm(forms.ModelForm):
    required_css_class = "required"
    
    class Meta:
        model = Bt
        fields=['bucode', 'buname', 'butype', 'parent', 'gpslocation',
                'iswarehouse', 'enable']
        labels = {
            'bucode':'Code', 'buname':'Name','butype':'Type', 'parent':'Belongs To',
            'iswarehouse':'Warehouse', 'gpslocation':'GPS Location', 'isenable':'Enable'
        }
        widgets={
            'bucode':forms.TextInput(attrs={'style':'text-transform:uppercase;'})
        }
    
    def __init__(self, *args, **kwargs):
        super(BtForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile']:
                visible.field.widget.attrs['class'] = 'form-control'


    def clean_bucode(self):
        bucode = self.cleaned_data['bucode']
        return bucode.upper()
    
    def clean_gpslocation(self):
        import re
        gps = self.cleaned_data['gpslocation']
        regex = '^([-+]?)([\d]{1,2})(((\.)(\d+)(,)))(\s*)(([-+]?)([\d]{1,3})((\.)(\d+))?)$'
        if not re.match(regex, gps):
            raise forms.ValidationError("Please enter a correct gps coordinates.")
        return gps

#========================================== END MODEL FORMS =======================================#


#========================================== START JSON FORMS =======================================#
class BuPrefForm(forms.Form):
    required_css_class = "required"

    is_vendor = forms.BooleanField(initial=False, required=False)
    isserviceprovider = forms.BooleanField(required=False, initial=False)

    def __init__(self, *args, **kwargs):
        super(BuPrefForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile']:
                visible.field.widget.attrs['class'] = 'form-control'


#========================================== END JSON FORMS =======================================#
