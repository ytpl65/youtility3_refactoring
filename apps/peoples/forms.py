from django import forms
from .models import Capability, People, PeopleEventlog, Pgbelonging, Pgroup
from apps.onboarding.models import Bt
from django.core.validators import RegexValidator
from icecream import ic
from django.db.models import Q

#============= BEGIN LOGIN FORM ====================#

class LoginForm(forms.Form):
    username = forms.CharField(
                max_length = 50,
                min_length=4,
                required   = True,
                widget     = forms.TextInput(attrs={'placeholder': 'Username or Phone or Email'}),
                label = 'Username')
    
    password  = forms.CharField(
                max_length = 25,
                required   = True,
                widget     = forms.PasswordInput(attrs={"placeholder": 'Enter Password', 
                            'autocomplete': 'off',
                            'data-toggle': 'password'}),
                label = 'Password')

    
    
    def clean_username(self):
        import re
        from .utils import validate_emailadd, validate_mobileno
        val = self.cleaned_data.get('username')
        if val:
            ic('username',val)
            email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            mobile_regex = r'^[+][0-9]{2,3}[0-9]+'
            if re.match(email_regex, val):
                validate_emailadd(val)
            elif re.match(mobile_regex, val):
                validate_mobileno(val)
            else:
                user = People.objects.filter(loginid__exact=val)
                ic(user)
                if not user.exists():
                    raise forms.ValidationError("[Access Denied] Invalid user details")
            return val
    



#=================- END LOGIN FORM ==================#

#============= BEGIN PEOPLE FORM ====================#

class PeopleForm(forms.ModelForm):
    required_css_class  = "required"
    error_msg = {
        'invalid_dates' : 'Date of birth & Date of join cannot be equal!',
        'invalid_dates2': 'Date of birth cannot be greater than Date of join',
        'invalid_dates3': 'Date of birth cannot be greater than Date of release',
        'invalid_id'    : 'Please choose a different loginid',
        'invalid_mobno' : 'Please enter mob no with country code first +XX',
        'invalid_mobno2': 'Please enter a valid mobile number',
        'invalid_id2'   : 'Enter loginid without any spaces',   
        'invalid_code'  : "Spaces are not allowed in [Code]",
        'invalid_code2' : "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3' : "[Invalid code] Code should not endwith '.' ",}
    
    #defines field rendering order
    field_order   = ['peoplecode',  'peoplename', 'loginid',     'email',
                    'mobno',        'gender',     'dateofbirth', 'isenable',
                    'peopletype',   'dateofjoin', 'department',  'designation',
                    'dateofreport', 'reportto',   'deviceid']
    
    #defines validator which validates peoplecode
    alpha_special = RegexValidator(
                        regex   = '[a-zA-Z0-9_\-]',
                        message = "Only this special characters are allowed -, _ ",
                        code    = 'invalid_code')
    
    peoplecode    = forms.CharField(
                        max_length = 20,
                        required   = True,
                        help_text  ='Enter text not including any spaces',
                        widget     = forms.TextInput(
                                    attrs={'style':'text-transform:uppercase;',
                                            'placeholder':'Enter people code'}),
                        validators = [alpha_special],
                        label      = "Code")
    email         = forms.EmailField(max_length=100,
                    widget = forms.TextInput(attrs={'placeholder':'Enter email address'}))
    loginid       = forms.CharField(max_length=30, required=True)

    class Meta:
        model  = People
        fields = ['peoplename', 'peoplecode',  'peopleimg',  'mobno',      'email', 
                'loginid',      'dateofbirth', 'isenable',   'deviceid',   'gender',
                'peopletype',   'dateofjoin',  'department', 'dateofreport', 
                'designation',  'reportto', ]
        labels = {
            'peoplename':'Name',       'loginid'    :'Login Id',         'email'       :'Email',
            'peopletype':'People Type', 'reportto'  :'Report to',        'designation':'Designation',
            'gender'    :'Gender',     'dateofbirth':'Date of Birth',    'isenable'    :'Enable',         
            'department':'Department', 'dateofjoin' : 'Date of Joining', 'dateofreport':'Date of Release',
            'deviceid':'Device Id' }
        
        widgets = {
            'mobno'     : forms.TextInput(attrs={'placeholder':'Enter mobile number'}), 
            'peoplename': forms.TextInput(attrs={'placeholder':'Enter people name'}),
            'loginid'   : forms.TextInput(attrs={'placeholder':'Enter login id'}),
            'dateofbirth':forms.DateInput(format='%d %b %Y'),
            'dateofjoin':forms.DateInput(format='%d %b %Y'),
            'dateofreport':forms.DateInput(format='%d %b %Y')
        }
    
    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        
        super(PeopleForm, self).__init__(*args, **kwargs)
        self.fields['mobno'].help_text = 'Eg:- +91XXXXXXXXXX, +44XXXXXXXXX'
        self.fields['loginid'].help_text = 'Enter text not including any spaces'
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
    
    def clean(self):
        from datetime import datetime
        super(PeopleForm, self).clean()
        dob = self.cleaned_data.get('dateofbirth')
        doj = self.cleaned_data.get('dateofjoin')
        dor = self.cleaned_data.get('dateofreport')
        if (dob and dor and doj):
            if dob == doj:
                raise forms.ValidationError(self.error_msg['invalid_dates'])
            elif dob > doj:
                print(dob, doj)
                raise forms.ValidationError(self.error_msg['invalid_dates2'])
            elif dob > dor:
                raise forms.ValidationError(self.error_msg['invalid_dates3'])
            
    
    #For field level validation define functions like clean_<func name>.
    def clean_peoplecode(self):
        import re
        value = self.cleaned_data.get('peoplecode')
        regex = "^[a-zA-Z0-9\-_]*$"
        if value:
            if " " in value: raise forms.ValidationError(self.error_msg['invalid_code'])
            elif  not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_code2'])
            elif value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_code3'])
            return value.upper()

    def clean_loginid(self):
        import re
        value = self.cleaned_data.get('loginid')
        if value:
            if " " in value:
                raise forms.ValidationError(self.error_msg['invalid_id2'])
            regex = '[a-zA-Z0-9@\-\.]+'
            if not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_id'])
            return value
    
    def clean_peoplename(self):
        value =  self.cleaned_data.get('peoplename')
        if value: return value.upper()

    def clean_mobno(self):
        import phonenumbers as pn
        from phonenumbers.phonenumberutil import NumberParseException
        mobno = self.cleaned_data.get('mobno')
        if mobno:
            if '+' not in mobno:
                raise forms.ValidationError(self.error_msg['invalid_mobno'])
            try:
                no = pn.parse(mobno)
                if not pn.is_valid_number(no):
                    raise forms.ValidationError(self.error_msg['invalid_mobno2'])
            except NumberParseException:
                raise forms.ValidationError(self.error_msg['invalid_mobno2'])
            return mobno

#============= END PEOPLE FORM ====================#


#============= BEGIN PGROUP FORM ====================#

class PgroupForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_code' : "Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
    }

    class Meta:
        model  = Pgroup
        fields = ['groupname', 'enable']
        labels = {
            'groupname': 'Name',
            'enable'   : 'Enable'
        }
        widgets = {
            'groupname':forms.TimeInput(attrs={
                'placeholder':"Enter People Group Name"
            })
        }

    def __init__(self, *args, **kwargs):
        super(PgroupForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select']:
                visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                 visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type == 'select':
                visible.field.widget.attrs['class']            = 'form-select'
                visible.field.widget.attrs['data-control']     = 'select2'
                visible.field.widget.attrs['data-placeholder'] = 'Select an Option'

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result
    
    def clean_groupname(self):
        val = self.cleaned_data.get('groupname')
        if val: return val.upper()


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

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result


#============= BEGIN PGROUP FORM ====================#


#============= BEGIN CAPABILITY FORM ====================#

class CapabilityForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_code' : "Please don't enter spaces in your code",
        'invalid_code2': "Only these '-', '_' special characters are allowed in code",
        'invalid_code3': "Code's should not be endswith '.' ",
    }
    parent = forms.ModelChoiceField(queryset=Capability.objects.filter(Q(parent__capscode = 'NONE') | Q(capscode='NONE')),
    label='Belongs to')
    class Meta:
        model  = Capability
        fields = ['capscode', 'capsname', 'parent', 'cfor']
        labels = {
            'capscode' :'Code',
            'capsname' :'Capability',
            'parent'   :'Belongs to', 
            'cfor'     :'Capability for'}
        widgets =  {
            'capscode':forms.TextInput(
                attrs={'placeholder':"Code", 'style':"  text-transform: uppercase;"}
                ),
            'capsname':forms.TextInput(attrs={'placeholder':"Enter name"})}

    def __init__(self, *args, **kwargs):
        super(CapabilityForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
                    visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type in ['select', 'selectmultiple']:
                visible.field.widget.attrs['class']            = 'form-select'
                visible.field.widget.attrs['data-control']     = 'select2'
                visible.field.widget.attrs['data-placeholder'] = 'Select an option'
                visible.field.widget.attrs['data-allow-clear'] = 'true'
    
    def clean_capscode(self):
        import re
        value = self.cleaned_data.get('capscode')
        if value:
            regex = "^[a-zA-Z0-9\-_]*$"
            if " " in value: raise forms.ValidationError(self.error_msg['invalid_code'])
            elif  not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_code2'])
            elif value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_code3'])
            return value.upper()
    

    def clean_capsname(self):
        value = self.cleaned_data.get('capsname')
        if value: return value.upper()


    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        # loop on *all* fields if key '__all__' found else only on errors:
        for x in (self.fields if '__all__' in self.errors else self.errors):
            attrs = self.fields[x].widget.attrs
            attrs.update({'class': attrs.get('class', '') + ' is-invalid'})
        return result

#============= BEGIN CAPABILITY FORM ====================#


#============= BEGIN PEOPLE_EXTRAS FORM ====================#

class PeopleExtrasForm(forms.Form):

    labels = {'mob':'Mobile Capability', 'port':'Portlet Capability', 
            'report':'Report Capability', 'web':'Web Capability'}
    
    andriodversion            = forms.CharField(max_length=2, required=False, label='Andriod Version')
    appversion                = forms.CharField(max_length=8, required=False, label='App Version')
    mobilecapability          = forms.MultipleChoiceField(required=False, label=labels['mob'])
    portletcapability         = forms.MultipleChoiceField(required=False, label=labels['port'])
    reportcapability          = forms.MultipleChoiceField(required=False, label=labels['report'])
    webcapability             = forms.MultipleChoiceField(required=False, label=labels['web'])
    loacationtracking         = forms.BooleanField(initial=False,required=False)
    capturemlog               = forms.BooleanField(initial=False, required=False)
    showalltemplates          = forms.BooleanField(initial=False, required=False, label="Show all Templates ")
    debug                     = forms.BooleanField(initial=False, required=False)
    showtemplatebasedonfilter = forms.BooleanField(initial= False, required=False, label="Display site wise templates")
    blacklist                 = forms.BooleanField(initial=False, required=False)
    assignsitegroup           = forms.ChoiceField(required=False, label="Site Group")
    tempincludes              = forms.ChoiceField(required=False, label="Template")
    mlogsendsto               = forms.CharField(max_length=25, required=False)

    def __init__(self, *args, **kwargs):
        session = kwargs.pop('session')
        super(PeopleExtrasForm, self).__init__(*args, **kwargs)
        if not (session['is_superadmin']):
            self.fields['webcapability'].choices     = session['people_webcaps'] or session['client_webcaps']
            self.fields['mobilecapability'].choices  = session['people_mobcaps'] or session['client_mobcaps']
            self.fields['portletcapability'].choices = session['people_reportcaps'] or session['client_reportcaps']
            self.fields['reportcapability'].choices  = session['people_portletcaps'] or session['client_portletcaps']
        else:
            from .utils import get_caps_choices
            self.fields['webcapability'].choices     = get_caps_choices(cfor='WEB')
            self.fields['mobilecapability'].choices  = get_caps_choices(cfor='MOB')
            self.fields['portletcapability'].choices = get_caps_choices(cfor='REPORT')
            self.fields['reportcapability'].choices  = get_caps_choices(cfor='PORTLET')
        for visible in self.visible_fields():
            if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
                visible.field.widget.attrs['class'] = 'form-control'
            elif visible.widget_type == 'checkbox':
                 visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            elif visible.widget_type in ['select', 'selectmultiple']:
                visible.field.widget.attrs['class']            = 'form-select'
                visible.field.widget.attrs['data-control']     = 'select2'
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

#============= END PEOPLE_EXTRAS FORM ====================#
