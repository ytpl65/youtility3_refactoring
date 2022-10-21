from django import forms
from django.conf import settings
from django.core.validators import RegexValidator
from django.db.models import Q
from requests import request

import apps.peoples.models as pm  # people-models
import apps.onboarding.models as om  # onboarding-models
from django_select2 import forms as s2forms
from apps.core import utils
import re
from apps.peoples.utils import create_caps_choices_for_peopleform
#============= BEGIN LOGIN FORM ====================#

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length = 50,
        min_length = 4,
        required = True,
        widget = forms.TextInput(
            attrs={'placeholder': 'Username or Phone or Email'}),
        label='Username')

    password = forms.CharField(
        max_length = 25,
        required = True,
        widget = forms.PasswordInput(attrs={"placeholder": 'Enter Password',
                                          'autocomplete': 'off', 'data-toggle': 'password'}),
        label='Password')
    
    def clean(self):
        super().clean()
        username = self.cleaned_data.get('username')
        user  = self.get_user(username)
        self.check_active(user)
        self.check_user_hassite(user)
    
    def clean_username(self):
        import re
        if val := self.cleaned_data.get('username'):
            return val

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result
    
    def check_active(self, user):
        if not user.enable:
            raise forms.ValidationError("Can't Login User Is Not Active, Please Contact Admin")
    
    def check_user_hassite(self, user):
        if not user.bu and user.people_extras['assignsitegroup']:
            raise forms.ValidationError("User has no site assigned")
    
    def get_user(self, username):
        try:
            return pm.People.objects.get(Q(loginid = username) | Q(email = username) | Q(mobno = username))
        except pm.People.DoesNotExist as e:
            raise forms.ValidationError("User not found with these UserName") from e
            
    
    

class PeopleForm(forms.ModelForm):
    required_css_class = "required"
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
        'invalid_code3' : "[Invalid code] Code should not endwith '.' ",                   
        'invalid_name'  : "[Invalid name] Only these special characters [-, _, @, #] are allowed in name field",                   
    }

    # defines field rendering order
    field_order = ['peoplecode',  'peoplename', 'loginid',     'email',
                   'mobno',        'gender',     'dateofbirth', 'enable',
                   'peopletype',   'dateofjoin', 'department',  'designation',
                   'dateofreport', 'reportto',   'deviceid']

    # defines validator which validates peoplecode
    alpha_special = RegexValidator(
        regex='[a-zA-Z0-9_\-]',
        message="Only this special characters are allowed -, _ ",
        code='invalid_code')

    peoplecode = forms.CharField(
        max_length = 20,
        required = True,
        widget = forms.TextInput(
            attrs={'style': 'text-transform:uppercase;',
                   'placeholder': 'Enter text not including any spaces'}),
        validators=[alpha_special],
        label="Code")
    email = forms.EmailField(max_length = 100,
                             widget = forms.TextInput(attrs={'placeholder': 'Enter email address'}))
    loginid = forms.CharField(max_length = 30, required = True,
                              widget = forms.TextInput(attrs={'placeholder': 'Enter text not including any spaces'}))

    class Meta:
        model = pm.People
        fields = ['peoplename', 'peoplecode',  'peopleimg',  'mobno',      'email',
                  'loginid',      'dateofbirth', 'enable',   'deviceid',   'gender',
                  'peopletype',   'dateofjoin',  'department', 'dateofreport', 'worktype',
                  'designation',  'reportto',   'bu', 'isadmin', 'ctzoffset',]
        labels = {
            'peoplename': 'Name',        'loginid'    : 'Login Id',        'email'       : 'Email',
            'peopletype': 'Employee Type', 'reportto'   : 'Report to',       'designation' : 'Designation',
            'gender'    : 'Gender',      'dateofbirth': 'Date of Birth',   'enable'      : 'Enable',
            'department': 'Department',  'dateofjoin' : 'Date of Joining', 'dateofreport': 'Date of Release',
            'deviceid'  : 'Device Id',   'bu'         : "Site",            'isadmin'     : "Is Admin",
            'worktype':'Work Type'}

        widgets = {
            'mobno'       : forms.TextInput(attrs={'placeholder': 'Eg:- 91XXXXXXXXXX, 44XXXXXXXXX'}),
            'peoplename'  : forms.TextInput(attrs={'placeholder': 'Enter people name'}),
            'loginid'     : forms.TextInput(attrs={'placeholder': 'Enter text not including any spaces'}),
            'dateofbirth' : forms.DateInput,
            'dateofjoin'  : forms.DateInput,
            'dateofreport': forms.DateInput,
            'peopletype'  : s2forms.Select2Widget,
            'gender'      : s2forms.Select2Widget,
            'department'  : s2forms.Select2Widget,
            'designation' : s2forms.Select2Widget,
            'reportto'    : s2forms.Select2Widget,
            'bu'          : s2forms.Select2Widget,
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['peopletype'].queryset = om.TypeAssist.objects.filter(
            tatype__tacode="PEOPLETYPE")
        self.fields['worktype'].queryset = om.TypeAssist.objects.filter(
            tatype__tacode="WORKTYPE")
        self.fields['department'].queryset = om.TypeAssist.objects.filter(
            tatype__tacode="DEPARTMENT")
        self.fields['designation'].queryset = om.TypeAssist.objects.filter(
            tatype__tacode="DESIGNATION")
        self.fields['dateofbirth'].input_formats  = settings.DATE_INPUT_FORMATS
        self.fields['dateofreport'].input_formats = settings.DATE_INPUT_FORMATS
        self.fields['dateofjoin'].input_formats   = settings.DATE_INPUT_FORMATS
        self.fields['dateofjoin'].required        = False
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

    def clean(self):
        super(PeopleForm, self).clean()
        dob = self.cleaned_data.get('dateofbirth')
        doj = self.cleaned_data.get('dateofjoin')
        dor = self.cleaned_data.get('dateofreport')
        if (dob and dor and doj):
            if dob == doj:
                raise forms.ValidationError(self.error_msg['invalid_dates'])
            if dob > doj:
                print(dob, doj)
                raise forms.ValidationError(self.error_msg['invalid_dates2'])
            if dob > dor:
                raise forms.ValidationError(self.error_msg['invalid_dates3'])

    # For field level validation define functions like clean_<func name>.

    def clean_peoplecode(self):
        import re
        if value := self.cleaned_data.get('peoplecode'):
            regex = "^[a-zA-Z0-9\-_]*$"
            if " " in value:
                raise forms.ValidationError(self.error_msg['invalid_code'])
            if not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_code2'])
            if value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_code3'])
            return value.upper()

    def clean_loginid(self):
        
        if value := self.cleaned_data.get('loginid'):
            if " " in value:
                raise forms.ValidationError(self.error_msg['invalid_id2'])
            regex = '[a-zA-Z0-9@\-\.]+'
            if not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_id'])
            return value

    def clean_peoplename(self):
        if value := self.cleaned_data.get('peoplename'):
            regex = "^[a-zA-Z0-9\-_@#\[\]\(\|\)\{\} ]*$"
            if not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_name'])
        return value

    def clean_mobno(self):
        import phonenumbers as pn
        from phonenumbers.phonenumberutil import NumberParseException
        if mobno := self.cleaned_data.get('mobno'):
            try:
                no = pn.parse(f'+{mobno}')
                if not pn.is_valid_number(no):
                    raise forms.ValidationError(
                        self.error_msg['invalid_mobno2'])
            except NumberParseException as e:
                raise forms.ValidationError(self.error_msg['invalid_mobno2']) from e
            return mobno

class PgroupForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_code' : "Spaces are not allowed in [Code]",
        'invalid_code2': "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_code3': "[Invalid code] Code should not endwith '.' ",
        'invalid_name'  : "[Invalid name] Only these special characters [-, _, @, #] are allowed in name field", 
    }
    peoples = forms.MultipleChoiceField(
        required = True,
        widget = s2forms.Select2MultipleWidget,
        label="Select People")

    class Meta:
        model = pm.Pgroup
        fields = ['groupname', 'enable', 'identifier', 'ctzoffset']
        labels = {
            'name': 'Name',
            'enable': 'Enable'
        }
        widgets = {
            'groupname': forms.TextInput(attrs={
                'placeholder': "Enter People Group Name"
            }),
            'identifier':forms.TextInput(attrs = {"style": "display:none"})
        }

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

    def clean_peoples(self):
        if val := self.request.POST.get('peoples'):
            print(val)
    
    def clean_groupname(self):
        if value := self.cleaned_data.get('groupname'):
            regex = "^[a-zA-Z0-9\-_@#\[\]\(\|\)\{\} ]*$"
            if not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_name'])
        return value

class SiteGroupForm(PgroupForm):
    peoples = None

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['identifier'].initial = om.TypeAssist.objects.get(tacode='SITEGROUP')


class PeopleGroupForm(PgroupForm):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        site = self.request.user.bu.bucode if self.request.user.bu else ""
        self.fields['identifier'].initial = om.TypeAssist.objects.get(tacode='PEOPLEGROUP')
        self.fields['peoples'].choices = pm.People.objects.select_related(
            'bu').filter(~Q(peoplecode='NONE'), isadmin = False).values_list(
            'id', 'peoplename')

class PgbelongingForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = pm.Pgbelonging
        fields = ['isgrouplead']
        labels = {
            'isgrouplead': 'Group Lead'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

class CapabilityForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_code' : "Please don't enter spaces in your code",
        'invalid_code2': "Only these '-', '_' special characters are allowed in code",
        'invalid_code3': "Code's should not be endswith '.' ",
        'invalid_name'  : "[Invalid name] Only these special characters [-, _, @, #] are allowed in name field",                   
    }
    parent = forms.ModelChoiceField(queryset = pm.Capability.objects.filter(Q(parent__capscode='NONE') | Q(capscode='NONE')),
                                    label='Belongs to', widget = s2forms.Select2Widget)

    class Meta:
        model = pm.Capability
        fields = ['capscode', 'capsname', 'parent', 'cfor', 'ctzoffset']
        labels = {
            'capscode': 'Code',
            'capsname': 'Capability',
            'parent': 'Belongs to',
            'cfor': 'Capability for'}
        widgets = {
            'capscode': forms.TextInput(
                attrs={'placeholder': "Code",
                       'style': "  text-transform: uppercase;"}
            ),
            'capsname': forms.TextInput(attrs={'placeholder': "Enter name"}),
            'cfor': s2forms.Select2Widget}

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)

    def clean_capscode(self):
        import re
        if value := self.cleaned_data.get('capscode'):
            regex = "^[a-zA-Z0-9\-_]*$"
            if " " in value:
                raise forms.ValidationError(self.error_msg['invalid_code'])
            if not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_code2'])
            if value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_code3'])
            return value.upper()

    def clean_capsname(self):
        if value := self.cleaned_data.get('capsname'):
            regex = "^[a-zA-Z0-9\-_@#\[\]\(\|\)\{\} ]*$"
            if not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_name'])
        return value

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result

class PeopleExtrasForm(forms.Form):

    labels = {'mob': 'Mobile Capability', 'port': 'Portlet Capability',
              'report': 'Report Capability', 'web': 'Web Capability'}
    andriodversion            = forms.CharField(max_length = 2, required = False, label='Andriod Version')
    appversion                = forms.CharField(max_length = 8, required = False, label='App Version')
    mobilecapability          = forms.MultipleChoiceField(required = False, label = labels['mob'], widget = s2forms.Select2MultipleWidget)
    portletcapability         = forms.MultipleChoiceField(required = False, label = labels['port'], widget = s2forms.Select2MultipleWidget)
    reportcapability          = forms.MultipleChoiceField(required = False, label = labels['report'], widget = s2forms.Select2MultipleWidget)
    webcapability             = forms.MultipleChoiceField(required = False, label = labels['web'], widget = s2forms.Select2MultipleWidget)
    loacationtracking         = forms.BooleanField(initial = False, required = False)
    capturemlog               = forms.BooleanField(initial = False, required = False)
    showalltemplates          = forms.BooleanField(initial = False, required = False, label="Show all Templates ")
    debug                     = forms.BooleanField(initial = False, required = False)
    showtemplatebasedonfilter = forms.BooleanField(initial = False, required = False, label="Display site wise templates")
    blacklist                 = forms.BooleanField(initial = False, required = False)
    alertmails                = forms.BooleanField(initial=False , label='Alert Mails', required=False)
    isemergencycontact        = forms.BooleanField(initial=False , label='Is Emergency Contact', required=False)
    assignsitegroup           = forms.MultipleChoiceField(required = False, label="Site Group", widget = s2forms.Select2MultipleWidget)
    tempincludes              = forms.MultipleChoiceField(required = False, label="Template", widget = s2forms.Select2MultipleWidget)
    mlogsendsto               = forms.CharField(max_length = 25, required = False)
    currentaddress            = forms.CharField(required = False, widget=forms.Textarea(attrs={'rows': 2, 'cols': 15}))
    permanentaddress          = forms.CharField(required = False,  widget=forms.Textarea(attrs={'rows': 2, 'cols': 15}))

    
    def __init__(self, *args, **kwargs):
        session = kwargs.pop('session')
        request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['assignsitegroup'].choices = pm.Pgroup.objects.get_assignedsitegroup_forclient(session['client_id'])
        self.fields['tempincludes'].choices = pm.Pgroup.objects.get_assignedsitegroup_forclient(session['client_id'])
        web, mob, portlet, report = create_caps_choices_for_peopleform(request.user.client)
        if not (session['is_superadmin']):
            self.fields['webcapability'].choices     = session['people_webcaps'] or  web
            self.fields['mobilecapability'].choices  = session['people_mobcaps'] or mob
            self.fields['portletcapability'].choices = session['people_portletcaps'] or portlet
            self.fields['reportcapability'].choices  = session['people_reportcaps'] or report
        else:
            # if superadmin is logged in
            from .utils import get_caps_choices
            self.fields['webcapability'].choices    = get_caps_choices(cfor = pm.Capability.Cfor.WEB)
            self.fields['mobilecapability'].choices = get_caps_choices(
                cfor = pm.Capability.Cfor.MOB)
            self.fields['portletcapability'].choices = get_caps_choices(
                cfor = pm.Capability.Cfor.PORTLET)
            self.fields['reportcapability'].choices = get_caps_choices(
                cfor = pm.Capability.Cfor.REPORT)
        utils.initailize_form_fields(self)

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result



class PeopleGrpAllocation(forms.Form):
    people = forms.ChoiceField(required = True, widget = s2forms.Select2Widget)
    is_grouplead = forms.BooleanField(required = False, initial = False)

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        site = request.user.bu.bucode if request.user.bu else ""
        self.fields['people'].choices = pm.People.objects.select_related(
            'bu').filter(
            bu__bucode = site).values_list(
            'id', 'peoplename')

    def is_valid(self) -> bool:
        """Add class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result
