################## Activity app - Forms ###################
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
import apps.activity.models as am
import apps.peoples.models as pm
import apps.onboarding.models as om
from apps.core import utils
import apps.activity.utils as ac_utils
import django_select2.forms as s2forms
from django.contrib.gis.geos import GEOSGeometry
import json
import re
from django.http import QueryDict
from datetime import datetime



class QuestionForm(forms.ModelForm):
    error_msg = {
        'invalid_name'  : "[Invalid name] Only these special characters [-, _, @, #] are allowed in name field",
    }
    required_css_class = "required"
    alertbelow         = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Below')
    alertabove = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Above')
    options = forms.CharField(max_length=2000, required=False, label='Options', widget=forms.TextInput(attrs={'placeholder': 'Enter options separated by comma (,)'}))

    class Meta:
        model = am.Question
        fields = ['quesname', 'answertype', 'alerton', 'isworkflow', 'isavpt', 'avpttype',
                  'unit', 'category', 'options', 'isworkflow', 'min', 'max', 'ctzoffset']
        labels = {
            'quesname' : 'Name',
            'answertype': 'Type',
            'unit'      : 'Unit',
            'category'  : 'Category',
            'min'       : 'Min Value',
            'max'       : 'Max Value',
            'alerton'   : 'Alert On',
            'isworkflow': 'used in workflow?',
        }

        widgets = {
            'answertype': s2forms.Select2Widget,
            'category'  : s2forms.Select2Widget,
            'unit'      : s2forms.Select2Widget,
            'alerton'   : s2forms.Select2MultipleWidget,
        }

    def __init__(self, *args, **kwargs):  # sourcery skip: use-named-expression
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['min'].initial       = None
        self.fields['max'].initial       = None
        self.fields['category'].required = False
        self.fields['unit'].required     = False
        self.fields['alerton'].required  = False
        
        #filters for dropdown fields
        self.fields['unit'].queryset = om.TypeAssist.objects.select_related('tatype').filter(tatype__tacode = 'QUESTIONUNIT', client_id = S['client_id'])
        self.fields['category'].queryset = om.TypeAssist.objects.select_related('tatype').filter(tatype__tacode = 'QUESTIONCATEGORY', client_id = S['client_id'])
        
        if self.instance.id:
            ac_utils.initialize_alertbelow_alertabove(self.instance, self)
        utils.initailize_form_fields(self)

    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data
        print(data.get('alerton'), data.get('min'), "********88888")
        alertabove = alertbelow = None
        if(data.get('answertype') not in ['NUMERIC', 'RATING', 'CHECKBOX', 'DROPDOWN']):
            cleaned_data['min'] = cleaned_data['max'] = None
            cleaned_data['alertbelow'] = cleaned_data['alertabove'] = None
            cleaned_data['alerton'] = cleaned_data['options'] = None
        if data.get('answertype') in  ['CHECKBOX', 'DROPDOWN', 'MULTISELECT']:
            cleaned_data['min'] = cleaned_data['max'] = None
            cleaned_data['alertbelow'] = cleaned_data['alertabove'] = None
        if data.get('answertype') in ['NUMERIC', 'RATING']:
            cleaned_data['options'] = None
        if data.get('alertbelow') and data.get('min') not in [None, ""]:
            alertbelow = ac_utils.validate_alertbelow(forms, data)
            ic(alertbelow)
        if data.get('alertabove') and data.get('max') not in [None, '']:
            alertabove = ac_utils.validate_alertabove(forms, data)
            ic(alertabove)
        if data.get('answertype') == 'NUMERIC' and alertabove and alertbelow:
            alerton = f'<{alertbelow}, >{alertabove}'
            ic(alerton)
            cleaned_data['alerton'] = alerton

    def clean_alerton(self):
        if val := self.cleaned_data.get('alerton'):
            return ac_utils.validate_alerton(forms, val)
        else:
            return val

    def clean_options(self):
        if val := self.cleaned_data.get('options'):
            return ac_utils.validate_options(forms, val)
        else:
            return val
    
    def clean_min(self):
        ic(self.cleaned_data)
        return val if (val := self.cleaned_data.get('min')) else 0.0
    
    def clean_max(self):
        ic(self.cleaned_data)
        val = val if (val := self.cleaned_data.get('max')) else 0.0
        return val
    
            

class MasterQsetForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_name'  : "[Invalid name] Only these special characters [-, _, @, #] are allowed in name field",
    }
    assetincludes = forms.MultipleChoiceField(
        required = True, label='Checkpoint', widget = s2forms.Select2MultipleWidget)
    site_type_includes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label="Site Types", required=False)
    buincludes         = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label='Site Includes', required=False)
    site_grp_includes  = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label='Site groups', required=False)

    class Meta:
        model = am.QuestionSet
        fields = ['qsetname', 'parent', 'enable', 'assetincludes', 'type', 'ctzoffset', 'site_type_includes', 'buincludes', 'site_grp_includes']

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
        self.fields['site_type_includes'].choices = om.TypeAssist.objects.filter(Q(tatype__tacode = "SITETYPE") | Q(tacode='NONE'), client_id = self.request.session['client_id']).values_list('id', 'taname')
        bulist = om.Bt.objects.get_all_bu_of_client(self.request.session['client_id'])
        self.fields['buincludes'].choices = pm.Pgbelonging.objects.get_assigned_sites_to_people(self.request.user.id, makechoice=True)
        self.fields['site_grp_includes'].choices = pm.Pgroup.objects.filter(
            Q(groupname='NONE') |  Q(identifier__tacode='SITEGROUP') & Q(bu_id__in = bulist)).values_list('id', 'groupname')
        utils.initailize_form_fields(self)
    
    def clean_qsetname(self):
        if value := self.cleaned_data.get('qsetname'):
            regex = "^[a-zA-Z0-9\-_@#\[\]\(\|\)\{\} ]*$"
            if not re.match(regex, value):
                raise forms.ValidationError("[Invalid name] Only these special characters [-, _, @, #] are allowed in name field")
        return value

class QsetBelongingForm(forms.ModelForm):
    required_css_class = "required"
    alertbelow = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Below')
    alertabove = forms.CharField(widget = forms.NumberInput(
        attrs={'step': "0.01"}), required = False, label='Alert Above')
    options = forms.CharField(max_length=2000, required=False, label='Options', widget=forms.TextInput(attrs= {'placeholder':'Enter options separated by comma ","'}))


    class Meta:
        model = am.QuestionSetBelonging
        fields = ['seqno', 'qset', 'question', 'answertype', 'min', 'max',
                  'isavpt', 'avpttype',
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
        self.fields['min'].initial = None
        self.fields['max'].initial = None
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
        ic(data)
        alertabove = alertbelow = None
        if(data.get('answertype') not in ['NUMERIC', 'RATING', 'CHECKBOX', 'DROPDOWN']):
            cleaned_data['min'] = cleaned_data['max'] = None
            cleaned_data['alertbelow'] = cleaned_data['alertabove'] = None
            cleaned_data['alerton'] = cleaned_data['options'] = None
        if data.get('answertype') in  ['CHECKBOX', 'DROPDOWN']:
            cleaned_data['min'] = cleaned_data['max'] = None
            cleaned_data['alertbelow'] = cleaned_data['alertabove'] = None
        if data.get('answertype') in ['NUMERIC', 'RATING']:
            cleaned_data['options'] = None
        if data.get('alertbelow') and data.get('min'):
            alertbelow = ac_utils.validate_alertbelow(forms, data)
        if data.get('alertabove') and data.get('max'):
            alertabove = ac_utils.validate_alertabove(forms, data)
        if data.get('answertype') == 'NUMERIC' and alertabove and alertbelow:
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

class ChecklistForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_name'  : "[Invalid name] Only these special characters [-, _, @, #] are allowed in name field",
    }
    assetincludes = forms.MultipleChoiceField(
        required = True, label='Checkpoint', widget = s2forms.Select2MultipleWidget)
    site_type_includes = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label="Site Types", required=False)
    buincludes         = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label='Site Includes', required=False)
    site_grp_includes  = forms.MultipleChoiceField(widget=s2forms.Select2MultipleWidget, label='Site groups', required=False)
    
    class Meta:
        model = am.QuestionSet
        fields = ['qsetname', 'enable', 'type', 'ctzoffset', 'assetincludes', 'show_to_all_sites',
                  'site_type_includes', 'buincludes', 'site_grp_includes', 'parent']
        widgets = {
            'parent':forms.TextInput(attrs={'style':'display:none'}),
        }


    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['type'].initial        = 'CHECKLIST'
        self.fields['parent'].required = False
        #self.fields['type'].widget.attrs   = {"style": "display:none;"}
        if not self.instance.id:
            self.fields['site_grp_includes'].initial = 1
            self.fields['site_type_includes'].initial = 1
            self.fields['buincludes'].initial = 1
            self.fields['assetincludes'].initial = 1
        else: 
            self.fields['type'].required = False
        
        self.fields['site_type_includes'].choices = om.TypeAssist.objects.filter(Q(tacode='NONE') |  Q(client_id = S['client_id']) & Q(tatype__tacode = "SITETYPE"),  enable=True).values_list('id', 'taname')
        bulist = om.Bt.objects.get_all_bu_of_client(self.request.session['client_id'])
        self.fields['buincludes'].choices = pm.Pgbelonging.objects.get_assigned_sites_to_people(self.request.user.id, makechoice=True)
        self.fields['site_grp_includes'].choices = pm.Pgroup.objects.filter(
            Q(groupname='NONE') |  Q(identifier__tacode='SITEGROUP') & Q(bu_id__in = bulist) & Q(client_id = S['client_id'])).values_list('id', 'groupname')
        self.fields['assetincludes'].choices = ac_utils.get_assetsmartplace_choices(self.request, ['CHECKPOINT', 'ASSET'])
        utils.initailize_form_fields(self)
        
    def clean(self):
        super().clean()
        self.cleaned_data = self.check_nones(self.cleaned_data)
        if self.instance.id:
            self.cleaned_data['type'] = self.instance.type
        
    def check_nones(self, cd):
        fields = {
            'parent':'get_or_create_none_qset'
            }
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd  


class QuestionSetForm(MasterQsetForm):

    class Meta(MasterQsetForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S  = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['type'].initial          = 'QUESTIONSET'    
        self.fields['assetincludes'].label   = 'Asset/Smartplace'
        self.fields['assetincludes'].choices = ac_utils.get_assetsmartplace_choices(self.request, ['ASSET', 'SMARTPLACE'])
        self.fields['site_type_includes'].choices = om.TypeAssist.objects.filter(tatype__tacode='SITETYPE', client_id = S['client_id']).values_list('id', 'tacode')
        self.fields['type'].widget.attrs     = {"style": "display:none;"}
        if not self.instance.id:
            self.fields['parent'].initial = 1
            self.fields['site_grp_includes'].initial = 1
            self.fields['site_type_includes'].initial = 1
            self.fields['buincludes'].initial = 1
        utils.initailize_form_fields(self)



class  MasterAssetForm(forms.ModelForm):
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
        
    
    def clean_assetname(self):
        if value := self.cleaned_data.get('assetname'):
            regex = "^[a-zA-Z0-9\-_@#\[\]\(\|\)\{\} ]*$"
            if not re.match(regex, value):
                raise forms.ValidationError("[Invalid name] Only these special characters [-, _, @, #] are allowed in name field")
        return value

class SmartPlaceForm(forms.ModelForm):


    class Meta:
        model = am.Asset
        fields = ['assetcode', 'assetname', 'identifier', 'ctzoffset', 'runningstatus',
                  'type', 'parent', 'iscritical', 'enable']
        labels = {
            'assetcode':'Code', 'assetname':'Name', 'enable':'Enable',
            'type': 'Type', 'iscritical':'Critical', 'runningstatus':"Status",
            'parent':'Belongs To'
        }

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['identifier'].initial = 'SMARTPLACE'
        self.fields['identifier'].widget.attrs = {"style": "display:none;"}
        self.fields['parent'].queryset = am.Asset.objects.filter(
            Q(identifier='LOCATION') & Q(enable = True) | Q(assetcode='NONE'))
        self.fields['type'].queryset = om.TypeAssist.objects.filter(tatype__tacode__in = ['ASSETTYPE', 'ASSET_TYPE'])

    
    def clean(self):
        super().clean()
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        if self.cleaned_data.get('gpslocation'):
            data = QueryDict(self.request.POST['formData'])
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        return self.cleaned_data

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


class CheckpointForm(forms.ModelForm):
    required_css_class = "required"
    error_msg = {
        'invalid_assetcode'  : 'Spaces are not allowed in [Code]',
        'invalid_assetcode2' : "[Invalid code] Only ('-', '_') special characters are allowed",
        'invalid_assetcode3' : "[Invalid code] Code should not endwith '.' ",
        'invalid_latlng'  : "Please enter a correct gps coordinates."
    }
    request=None


    class Meta:
        model = am.Asset
        fields = ['assetcode', 'assetname', 'runningstatus', 'parent',
            'iscritical', 'enable', 'identifier', 'ctzoffset', 'type', 'location']
        widgets = {
            'location':s2forms.Select2Widget,
            'type':s2forms.Select2Widget,
            'parent':s2forms.Select2Widget,
            'runningstatus':s2forms.Select2Widget
        }
        labels = {'location':'Location', 'parent':'Belongs To'}
        

    def __init__(self, *args, **kwargs):
        """Initializes form add atttibutes and classes here."""
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super(CheckpointForm, self).__init__(*args, **kwargs)
        self.fields['assetcode'].widget.attrs = {'style':"text-transform:uppercase"}
        if self.instance.id is None:
            self.fields['parent'].initial = 1
        self.fields['identifier'].initial = 'CHECKPOINT'
        self.fields['type'].required = False
        self.fields['identifier'].widget.attrs = {"style": "display:none"}
        
        #filters for dropdown fields
        self.fields['location'].queryset = am.Location.objects.filter(Q(enable = True) | Q(loccode='NONE'), bu_id = S['bu_id'])
        self.fields['parent'].queryset = am.Asset.objects.filter(Q(enable=True)| Q(assetcode='NONE'), bu_id = S['bu_id'])
        self.fields['type'].queryset = om.TypeAssist.objects.filter(client_id = S['client_id'], tatype__tacode = 'CHECKPOINTTYPE')
        utils.initailize_form_fields(self)

        
        
        
    def clean(self):
        ic(self.request)
        super().clean()
        self.cleaned_data = self.check_nones(self.cleaned_data)
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        if self.cleaned_data.get('gpslocation'):
            data = QueryDict(self.request.POST['formData'])
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        if self.cleaned_data['assetcode'] == self.cleaned_data['parent'].assetcode:
            raise forms.ValidationError("Code and Belongs To cannot be same!")
        return self.cleaned_data

    
        
    def clean_assetcode(self):
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        import re
        if value := self.cleaned_data.get('assetcode'):
            regex = "^[a-zA-Z0-9\-_()#)]*$"
            if " " in value: raise forms.ValidationError(self.error_msg['invalid_assetcode'])
            if  not re.match(regex, value):
                raise forms.ValidationError(self.error_msg['invalid_assetcode2'])
            if value.endswith('.'):
                raise forms.ValidationError(self.error_msg['invalid_assetcode3'])
            return value.upper()
        
    def clean_gpslocation(self, val):
        import re
        if gps := val:
            if gps == 'NONE': return None
            regex = '^([-+]?)([\d]{1,2})(((\.)(\d+)(,)))(\s*)(([-+]?)([\d]{1,3})((\.)(\d+))?)$'
            gps = gps.replace('(', '').replace(')', '')
            if not re.match(regex, gps):
               raise forms.ValidationError(self.error_msg['invalid_latlng'])
            gps.replace(' ', '')
            lat, lng = gps.split(',')
            gps = GEOSGeometry(f'SRID=4326;POINT({lng} {lat})')
        return gps
    
    def check_nones(self, cd):
        fields = {
            'parent': 'get_or_create_none_asset',
            'servprov'   : 'get_or_create_none_bv',
            'type'       : 'get_none_typeassist',
            'category'   : 'get_none_typeassist',
            'subcategory': 'get_none_typeassist',
            'brand'      : 'get_none_typeassist',
            'unit'       : 'get_none_typeassist',
            'location'   : 'get_or_create_none_location'}
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd
    

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
    jobdesc = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 40}), label='Description', required=False)
    cronstrue = forms.CharField(widget=forms.Textarea(attrs={'readonly':True, 'rows':2}), required=False) 

    class Meta:
        model = am.Job
        fields = [
            'jobname', 'jobdesc', 'fromdate', 'uptodate', 'cron','sgroup',
            'identifier', 'planduration', 'gracetime', 'expirytime',
            'asset', 'priority', 'qset', 'pgroup', 'geofence', 'parent',
            'seqno', 'client', 'bu', 'starttime', 'endtime', 'ctzoffset',
            'frequency',  'scantype', 'ticketcategory', 'people', 'shift']

        labels = {
            'jobname'   : 'Name',            'fromdate'      : 'Valid From',
            'uptodate' : 'Valid To',     'cron'        : 'Scheduler', 'ticketcategory': 'Notify Catgory',
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
            'fromdate'      : forms.DateTimeInput,
            'uptodate'      : forms.DateTimeInput,
            'ctzoffset'     : forms.NumberInput(attrs={"style": "display:none;"}),
            'qset'          : s2forms.Select2Widget,
            'people'        : s2forms.Select2Widget,
            'bu'            : s2forms.Select2Widget,
            'cron'          :forms.TextInput(attrs={'style':'display:none'}),
            'jobdesc'       :forms.Textarea(attrs={'rows':'5', 'placeholder':"What does this tour about?"})
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
        return val

    @staticmethod
    def clean_slno():
        return -1

    def clean(self):
        cd = super().clean()
        self.instance.jobdesc = f'{cd.get("bu")} - {cd.get("jobname")}'

class JobNeedForm(forms.ModelForm):
    class Meta:
        model = am.Jobneed
        fields = ['identifier', 'frequency', 'parent', 'jobdesc', 'asset', 'ticketcategory',
                  'qset',  'people', 'pgroup', 'priority', 'scantype', 'multifactor',
                  'jobstatus', 'plandatetime', 'expirydatetime', 'gracetime', 'starttime',
                  'endtime', 'performedby', 'gpslocation', 'cuser', 'remarks', 'ctzoffset',
                  'remarkstype']
        widgets = {
            'ticketcategory': s2forms.Select2Widget,
            'scantype'      : s2forms.Select2Widget,
            'pgroup'        : s2forms.Select2Widget,
            'people'        : s2forms.Select2Widget,
            'qset'          : s2forms.ModelSelect2Widget(model = am.QuestionSet, search_fields = ['qset_name__icontains']),
            'asset'         : s2forms.ModelSelect2Widget(model = am.Asset, search_fields = ['assetname__icontains']),
            'priority'      : s2forms.Select2Widget,
            'jobdesc'       : forms.Textarea(attrs={'rows': 2, 'cols': 40}),
            'remarks'       : forms.Textarea(attrs={'rows': 2, 'cols': 40}),
            'jobstatus'     : s2forms.Select2Widget,
            'performedby'   : s2forms.Select2Widget,
            'gpslocation'   : forms.TextInput,
            'remarks_type' : s2forms.Select2Widget
        }
        label = {
            'endtime': 'End Time',
            'ticketcategory':"Notify Category"
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
            'ticketcategory': 'Notify Category',
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
        self.fields['gpslocation'].required  = False
        #filters for dropdown fields
        self.fields['ticketcategory'].queryset = om.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        utils.initailize_form_fields(self)





class AssetForm(forms.ModelForm):
    required_css_class = "required"
    enable = forms.BooleanField(required=False, initial=True, label='Enable')
    status_field = forms.ChoiceField(choices=am.Asset.RunningStatus.choices, label = 'Duration of Selected Status', required=False, widget=s2forms.Select2Widget)
    
    class Meta:
        model = am.Asset
        fields = [
            'assetcode', 'assetname', 'runningstatus', 'type', 'category', 
            'subcategory', 'brand', 'unit', 'capacity', 'servprov', 'parent',
            'iscritical', 'enable', 'identifier', 'ctzoffset','location'
        ]
        labels={
            'assetcode':'Code', 'assetname':'Name', 'runningstatus':'Status',
            'type':'Type', 'category':'Category', 'subcategory':'Sub Category',
            'brand':'Brand', 'unit':'Unit', 'capacity':'Capacity', 'servprov':'Service Provider',
            'parent':'Belongs To', 'gpslocation':'GPS', 'location':'Location'
        }
        widgets={
            'brand'        : s2forms.Select2Widget,
            'unit'         : s2forms.Select2Widget,
            'category'     : s2forms.Select2Widget,
            'subcategory'  : s2forms.Select2Widget,
            'servprov'     : s2forms.Select2Widget,
            'runningstatus': s2forms.Select2Widget,
            'type'         : s2forms.Select2Widget,
            'parent'       : s2forms.Select2Widget,
            'location'     : s2forms.Select2Widget,
            'identifier':forms.TextInput(attrs={'style':"display:none;"})
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['enable'].widget.attrs = {'checked':False} if self.instance.id else {'checked':True}
        self.fields['assetcode'].widget.attrs = {'style':"text-transform:uppercase"}
        
        self.fields['identifier'].widget.attrs = {'style':"display:none"}
        self.fields['identifier'].initial      = 'ASSET'
        self.fields['capacity'].required       = False
        self.fields['servprov'].required       = False
        
        #filters for dropdown fields
        self.fields['parent'].queryset         = am.Asset.objects.filter(~Q(runningstatus='SCRAPPED'), identifier='ASSET', bu_id = S['bu_id'])
        self.fields['location'].queryset       = am.Location.objects.filter(~Q(locstatus='SCRAPPED'), bu_id = S['bu_id'])
        self.fields['type'].queryset           = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETTYPE', 'ASSET_TYPE']), client_id = S['client_id'])
        self.fields['category'].queryset       = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETCATEGORY', 'ASSET_CATEGORY']), client_id = S['client_id'])
        self.fields['subcategory'].queryset    = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETSUBCATEGORY', 'ASSET_SUBCATEGORY']), client_id = S['client_id'])
        self.fields['unit'].queryset           = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETUNIT', 'ASSET_UNIT', 'UNIT']), client_id = S['client_id'])
        self.fields['brand'].queryset          = om.TypeAssist.objects.filter(Q(tatype__tacode__in = ['ASSETBRAND', 'ASSET_BRAND', 'BRAND']), client_id = S['client_id'])
        self.fields['servprov'].queryset       = om.Bt.objects.filter(id = S['bu_id'], isserviceprovider = True, enable=True)
        utils.initailize_form_fields(self)
        
        
    
    def clean(self):
        super().clean()
        self.cleaned_data = self.check_nones(self.cleaned_data)
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        if self.cleaned_data.get('parent') is None:
            self.cleaned_data['parent'] = utils.get_or_create_none_asset()
        if self.cleaned_data.get('gpslocation'):
            data = QueryDict(self.request.POST['formData'])
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        if self.cleaned_data['assetcode'] == self.cleaned_data['parent'].assetcode:
            raise forms.ValidationError("Code and Belongs To cannot be same!")
        return self.cleaned_data
    
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
    
    def clean_assetcode(self):
        if val := self.cleaned_data.get('assetcode'):
            if not self.instance.id and  am.Asset.objects.filter(assetcode = val, client_id = self.request.session['client_id']).exists():
                raise forms.ValidationError("Asset with this code already exist")
            if ' ' in val:
                raise forms.ValidationError("Spaces are not allowed")
            return val.upper()
            
        return val
    
    def check_nones(self, cd):
        fields = {'parent': 'get_or_create_none_asset',
                'servprov': 'get_or_create_none_bv',
                'type': 'get_none_typeassist',
                'category': 'get_none_typeassist',
                'subcategory': 'get_none_typeassist',
                'brand': 'get_none_typeassist',
                'unit': 'get_none_typeassist',
                'location':'get_or_create_none_location'}
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd



class AssetExtrasForm(forms.Form):
    required_css_class = "required"
    ismeter =    forms.BooleanField(initial=False, required=False, label='Meter')
    is_nonengg_asset =    forms.BooleanField(initial=False, required=False, label='Non Engg. Asset')
    supplier      = forms.CharField(max_length=55, label='Supplier', required=False)
    meter         = forms.ChoiceField(widget=s2forms.Select2Widget, label='Meter', required=False)
    invoice_no    = forms.CharField( max_length=55, required=False, label='Invoice No')
    invoice_date  = forms.DateField(required=False, label='Invoice Date')
    service       = forms.ChoiceField(widget=s2forms.Select2Widget, label='Service', required=False)
    sfdate        = forms.DateField(label='Service From Date', required=False)
    stdate        = forms.DateField(label='Service To Date', required=False)
    yom           = forms.IntegerField(min_value=1980, max_value=utils.get_current_year(), label='Year of Manufactured', required=False)
    msn           = forms.CharField( max_length=55, required=False, label='Manufactured Serial No')
    bill_val      = forms.CharField(label='Bill Value', required=False, max_length=55)
    bill_date     = forms.DateField(label='Bill Date', required=False)
    purchase_date = forms.DateField(label='Purchase Date', required=False)
    inst_date     = forms.DateField(label='Installation Date', required=False)
    po_number     = forms.CharField(max_length=55, label='Purchase Order Number',required=False)
    far_asset_id  = forms.CharField(max_length=55, label='FAR Aseet ID',required=False)
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['service'].choices = om.TypeAssist.objects.filter(client_id = S['client_id'], tacode__in = ['SERVICE_TYPE','ASSETSERVICE', 'ASSET_SERVICE' 'SERVICETYPE']).values_list('id', 'tacode')
        self.fields['meter'].choices = om.TypeAssist.objects.filter(client_id = S['client_id'], tacode__in = ['ASSETMETER', 'ASSET_METER']).values_list('id', 'tacode')  
        utils.initailize_form_fields(self)
    
    def clean(self):
        cd = super().clean() #cleaned_data
        if (cd['sfdate'] and cd['stdate']) and cd['sfdate'] > cd['stdate']:
            raise forms.ValidationError('Service from date should be smaller than service to date!')
        if cd['bill_date'] and cd['bill_date'] > datetime.now().date():
            raise forms.ValidationError('Bill date cannot be greater than today')
        if cd['purchase_date'] and cd['purchase_date'] > datetime.now().date():
            raise forms.ValidationError('Purchase date cannot be greater than today')
        
        

class LocationForm(forms.ModelForm):
    required_css_class = "required"
    class Meta:
        model = am.Location
        fields = [
            'loccode', 'locname',  'parent', 'enable', 'type',
            'iscritical',  'ctzoffset', 'locstatus'
        ]
        labels = {
            'loccode':'Code', 'locname':'Name', 'parent':'Belongs To', 
        }
        widgets = {
            'type':s2forms.Select2Widget,
            'locstatus':s2forms.Select2Widget,
            'parent':s2forms.Select2Widget
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', False)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['loccode'].widget.attrs = {'style':"text-transform:uppercase"}
        #filters for dropdown fields
        self.fields['parent'].queryset = am.Location.objects.filter(client_id = S['client_id'], bu_id = S['bu_id'])
        self.fields['type'].queryset = om.TypeAssist.objects.filter(client_id = S['client_id'], tatype__tacode = 'LOCATIONTYPE')
        utils.initailize_form_fields(self)
        
        
        
    def clean(self):
        super().clean()
        self.cleaned_data = self.check_nones(self.cleaned_data)
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        if self.cleaned_data.get('gpslocation'):
            data = QueryDict(self.request.POST['formData'])
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        if self.cleaned_data['loccode'] == self.cleaned_data['parent'].loccode:
            raise forms.ValidationError("Code and Belongs To cannot be same!")
        return self.cleaned_data

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
    
    def clean_loccode(self):
        if val:= self.cleaned_data['loccode']:
            if not self.instance.id and am.Location.objects.filter(loccode = val, client_id=self.request.session['client_id']).exists():
                raise forms.ValidationError("Location code already exist, choose different code")
            if ' ' in val:
                raise forms.ValidationError("Spaces are not allowed")
        return val.upper() if val else val
    
    def check_nones(self, cd):
        fields = {'parent': 'get_or_create_none_location',
                'type': 'get_none_typeassist',
                }
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd
        
class PPMForm(forms.ModelForm):
    timeInChoices      = [('MINS', 'Minute'),('HRS', 'Hour'), ('DAYS', 'Day'), ('WEEKS', 'Week')]
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    FREQUENCY_CHOICES   = [('WEEKLY', 'Weekly'),('FORTNIGHTLY', 'Fortnight'), ('BIMONTHLY', 'Bimonthly'),
                           ("QUARTERLY", "Quarterly"), ('MONTHLY', 'Monthly'),('HALFYEARLY', 'Half Yearly'),
                           ('YEARLY', 'Yearly')]
    
    planduration_type  = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    gracetime_type     = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    expirytime_type    = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)
    frequency = forms.ChoiceField(choices=FREQUENCY_CHOICES, label="Frequency", widget=s2forms.Select2Widget)
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    cronstrue = forms.CharField(widget=forms.Textarea(attrs={'readonly':True, 'rows':2}), required=False) 

    required_css_class = "required"


    class Meta:
        model = am.Job
        fields = [
            'jobname', 'jobdesc', 'planduration', 'gracetime', 'expirytime', 'cron', 'priority', 'ticketcategory',
            'fromdate', 'uptodate', 'people', 'pgroup', 'scantype', 'frequency', 'asset', 'qset', 'assign_to',
            'ctzoffset', 'parent', 'identifier', 'seqno'
        ]
        labels = {
            'asset':'Asset', 'qset':"Question Set", 'people':"People", 
            'scantype':'Scantype', 'priority':'Priority',
            'jobdesc':'Description', 'jobname':"Name", 'planduration':"Plan Duration",
            'expirytime':'Exp time', 'cron':"Scheduler", 'ticketcategory':'Notify Category',
            'fromdate':'Valid From', 'uptdate':'Valid To', 'pgroup':'Group', 
            'assign_to':'Assign to'
        }
        widgets = {
            'asset'         : s2forms.Select2Widget,
            'qset'          : s2forms.Select2Widget,
            'people'        : s2forms.Select2Widget,
            'pgroup'        : s2forms.Select2Widget,
            'priority'      : s2forms.Select2Widget,
            'scantype'      : s2forms.Select2Widget,
            'ticketcategory': s2forms.Select2Widget,
            'identifier':forms.TextInput(attrs={'style':"display:none;"})
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super().__init__(*args, **kwargs)
        
        self.fields['asset'].required = True
        self.fields['qset'].required = True
        self.fields['identifier'].initial = 'PPM'
        self.fields['identifier'].widget.attrs = {'style':"display:none"}
        
        #filters for dropdown fields
        self.fields['ticketcategory'].queryset = om.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        self.fields['qset'].queryset = am.QuestionSet.objects.filter_for_dd_qset_field(self.request, ['CHECKLIST'], sitewise=True)
        self.fields['people'].queryset = pm.People.objects.filter_for_dd_people_field(self.request, sitewise=True)
        self.fields['pgroup'].queryset = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True)
        self.fields['asset'].queryset = am.Asset.objects.filter_for_dd_asset_field(self.request, ['ASSET', 'CHECKPOINT'], sitewise=True)
        utils.initailize_form_fields(self)
    
    def clean(self):
        cd          = self.cleaned_data
        times_names = ['planduration', 'expirytime', 'gracetime']
        types_names = ['planduration_type', 'expirytime_type', 'gracetime_type']
        
        
        times = [cd.get(time) for time in times_names]
        types = [cd.get(type) for type in types_names]
        for time, type, name in zip(times, types, times_names):
            cd[name] = self.convertto_mins(type, time)
        self.cleaned_data = self.check_nones(cd)

            
    
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
    def convertto_mins(_type, _time):
        ic("called")
        ic(_type, _time)
        if _type == 'HRS':
            ic("converted")
            return _time * 60
        if _type == 'WEEKS':
            ic('converted')
            return _time *7 * 24 * 60
        return _time * 24 * 60 if _type == 'DAYS' else _time

class PPMFormJobneed(forms.ModelForm):
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")
    required_css_class = "required"


    class Meta:
        model = am.Jobneed
        fields = [
            'jobdesc', 'asset',  'priority', 'ticketcategory', 'gracetime','starttime', 'endtime',
            'performedby','expirydatetime', 'people', 'pgroup', 'scantype', 'jobstatus',  'qset', 'assign_to',
            'plandatetime', 'ctzoffset'
        ]
        labels = {
            'asset':'Asset', 'qset':"Question Set", 'people':"People", 
            'scantype':'Scantype', 'priority':'Priority',
            'jobdesc':'Description', 'ticketcategory':'Notify Category',
            'fromdate':'Valid From', 'uptdate':'Valid To', 'pgroup':'Group', 
            'assign_to':'Assign to'
        }
        widgets = {
            'asset'         : s2forms.Select2Widget,
            'qset'          : s2forms.Select2Widget,
            'people'        : s2forms.Select2Widget,
            'pgroup'        : s2forms.Select2Widget,
            'priority'      : s2forms.Select2Widget,
            'scantype'      : s2forms.Select2Widget,
            'ticketcategory': s2forms.Select2Widget,
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['ticketcategory'].queryset = om.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        self.fields['qset'].queryset = am.QuestionSet.objects.filter_for_dd_qset_field(self.request, ['CHECKLIST'], sitewise=True)
        self.fields['people'].queryset = pm.People.objects.filter_for_dd_people_field(self.request, sitewise=True)
        self.fields['pgroup'].queryset = pm.Pgroup.objects.filter_for_dd_pgroup_field(self.request, sitewise=True)
        self.fields['asset'].queryset = am.Asset.objects.filter_for_dd_asset_field(self.request, ['ASSET'], sitewise=True)
        utils.initailize_form_fields(self)
        
class AssetComparisionForm(forms.Form):
    required_css_class = "required"
    
    asset_type = forms.ChoiceField(label="Asset Type", required=True, choices=[], widget=s2forms.Select2Widget)
    asset = forms.ChoiceField(label="Asset", required=True, choices=[], widget=s2forms.Select2MultipleWidget)
    qset = forms.ChoiceField(label="Question Set", required=True, choices=[], widget=s2forms.Select2Widget)
    question = forms.ChoiceField(label="Question", required=True, choices=[], widget=s2forms.Select2Widget)
    fromdate = forms.DateField(label='From', required=True)
    uptodate = forms.DateField(label='To', required=True)
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['asset_type'].choices = om.TypeAssist.objects.get_asset_types_choices(self.request)
        utils.initailize_form_fields(self)
        
    
class ParameterComparisionForm(forms.Form):
    required_css_class = "required"
    
    asset_type = forms.ChoiceField(label="Asset Type", required=True, choices=[], widget=s2forms.Select2Widget)
    asset = forms.ChoiceField(label="Asset", required=True, choices=[], widget=s2forms.Select2Widget)
    question = forms.ChoiceField(label="Question", required=True, choices=[], widget=s2forms.Select2MultipleWidget)
    fromdate = forms.DateField(label='From', required=True)
    uptodate = forms.DateField(label='To', required=True)
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        self.fields['asset_type'].choices = om.TypeAssist.objects.get_asset_types_choices(self.request)
        utils.initailize_form_fields(self)
    