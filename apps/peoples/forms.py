from django import forms
from django.forms.fields import BooleanField
from .models import Capability, People, PeopleEventlog, Pgbelonging, Pgroup
from django.core.validators import RegexValidator

#Model Forms

class PeopleForm(forms.ModelForm):
    required_css_class = "required"

    alpha_special = RegexValidator(regex='[a-zA-Z0-9_\-]', 
                                   message="Only this special characters are allowed -, _ ", 
                                   code='invalid_code')
    
    peoplecode = forms.CharField(max_length=20, 
                            required=True, 
                            widget=forms.TextInput(attrs={'style':'text-transform:uppercase;'}),
                            validators=[alpha_special])
    email = forms.EmailField(max_length=100)

    class Meta:
        model = People
        fields = ['peoplename', 'loginid', 'mobno', 'dateofbirth', 'isenable', 'deviceid', 'gender'
                    'peopletype', 'dateofjoin', 'department', 'dateofreport', 'reportto', ]
        labels = {
            'peoplecode':'Code',       'peoplename':'Name',             'loginid':'Login Id', 'email':'Email',
            'gender':'Gender',         'dateofbirth':'Date of Birth',   'isenable':'Enable',  'peopletype':'People Type',
            'department':'Department', 'dateofjoin': 'Date of Joining', 'dateofreport':'Date of Release'}

    
    def __init__(self, *args, **kwargs):
        super(PeopleForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'    

    def clean_peoplecode(self):
        peoplcode = self.cleaned_data['peoplecode']
        return peoplcode.upper()

    def clean_loginid(self):
        import re
        value = self.cleaned_data['loginid']
        regex = '[a-zA-Z0-9@\-\.]'
        if not re.match(regex, value):
            raise forms.ValidationError("Please choose a different loginid", code="invalid_id")
        return value
    
    def clean_peoplename(self):
        return self.cleaned_data['peoplename'].upper()


class PgroupForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model  = Pgroup
        fields = ['groupname', 'enable']
        labels = {
            'groupname':'Name',
            'enable':'Enable'
        }

    def __init__(self, *args, **kwargs):
        super(PgroupForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'  


class PgbelongingForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model  = Pgbelonging
        fields = ['isgrouplead']
        labels = {
            'isgrouplead':'Group Lead'
        }
    
    def __init__(self, *args, **kwargs):
        super(PgbelongingForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'      


class CapabilityForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model  = Capability
        fields = ['caps', 'includes', 'description', 'enable', 'cfor']
        labels = {
            'caps':'Capability',
            'description':'Description',
            'enable':'Enable', 
            'cfor':'Capability For'
        }

    def __init__(self, *args, **kwargs):
        super(CapabilityForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control' 


#Json Forms

class PeopleExtrasForm(forms.Form):
    WEBCAPABILITY_CHOICES = [('T', 'TASk'),('Tr', 'TOUR'),('A', 'ASSET')]
    REPCAPABILITY_CHOICES = [('T', 'TASk'),('Tr', 'TOUR'),('A', 'ASSET')]
    MOBCAPABILITY_CHOICES = [('T', 'TASk'),('Tr', 'TOUR'),('A', 'ASSET')]
    PORTLETCAPABILITY_CHOICES = [('T', 'TASk'),('Tr', 'TOUR'),('A', 'ASSET')]
    
    andriodversion            = forms.CharField(max_length=2, required=False, label='Andriod Version')
    appversion                = forms.CharField(max_length=8, required=False, label='App Version')
    mobilecapability          = forms.MultipleChoiceField(required=False, choices=WEBCAPABILITY_CHOICES)
    portletcapability         = forms.MultipleChoiceField(required=False, choices=MOBCAPABILITY_CHOICES)
    reportcapability          = forms.MultipleChoiceField(required=False, choices=REPCAPABILITY_CHOICES)
    webcapability             = forms.MultipleChoiceField(required=False, choices=PORTLETCAPABILITY_CHOICES)
    loacationtracking         = forms.BooleanField(initial=False,required=False)
    capturemlog               = forms.BooleanField(initial=False, required=False)
    showalltemplates          = forms.BooleanField(initial=False, required=False)
    debug                     = forms.BooleanField(initial=False, required=False)
    showtemplatebasedonfilter = forms.BooleanField(False, required=False)
    blacklist                 = forms.BooleanField(initial=False, required=False)
    assignsitegroup           = forms.ChoiceField(required=False)
    tempincludes              = forms.ChoiceField(required=False)
    mlogsendsto               = forms.CharField(max_length=25, required=False)

    def __init__(self, *args, **kwargs):
        super(PeopleExtrasForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control' 