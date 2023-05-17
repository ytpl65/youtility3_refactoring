from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Vendor, Wom, WomDetails
from apps.core import utils
from django.http import QueryDict
from django.contrib.gis.geos import GEOSGeometry
import django_select2.forms as s2forms
from django.utils import timezone
from apps.onboarding import models as om
from apps.activity import models as am

class VendorForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = Vendor
        fields = ['code', 'name', 'address', 'mobno', 'type', 'show_to_all_sites',
                  'email', 'ctzoffset', 'enable', 'address']
        labels = {
            'code':"Code",
            'name':"Name",
            'address':"Address",
            'mobno':"Mob no",
            'email':"Email"
        }
        widgets = {
            'name':forms.TextInput(attrs={'placeholder':'Enter Name...'}),
            'address':forms.Textarea(attrs={'rows':4}),
            'code':forms.TextInput(attrs={'style': "text-transform: uppercase;", 'placeholder':"Enter characters without spaces..."}),
            'type':s2forms.Select2Widget
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['address'].required = True
        self.fields['type'].required = False
        self.fields['type'].queryset = om.TypeAssist.objects.filter(tatype__tacode = 'VENDOR_TYPE', enable=True, client_id = S['client_id'])
        utils.initailize_form_fields(self)
    
    def clean(self):
        ic(self.request)
        super().clean()
        self.cleaned_data['gpslocation'] = self.data.get('gpslocation')
        if self.cleaned_data.get('gpslocation'):
            data = QueryDict(self.request.POST['formData'])
            self.cleaned_data['gpslocation'] = self.clean_gpslocation(data.get('gpslocation', 'NONE'))
        return self.cleaned_data
        
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
    
    def clean_code(self):
        return val.upper() if (val := self.cleaned_data.get('code')) else val
    

class WorkOrderForm(forms.ModelForm):
    required_css_class = "required"
    
    categories = forms.MultipleChoiceField(label='Queue', widget=s2forms.Select2MultipleWidget, required=False)
    
    class Meta:
        model = Wom
        fields = ['description', 'plandatetime', 'expirydatetime',  'asset', 'location', 'qset', 'ismailsent',
                  'priority', 'qset', 'ticketcategory', 'categories', 'vendor', 'ctzoffset', 'workstatus']
        
        widgets = {'categories':s2forms.Select2MultipleWidget,
                   'vendor'    : s2forms.Select2Widget,
                   'description':forms.Textarea(attrs={'rows':4, 'placeholder':"Enter detailed description of work to be done..."}),
                   'workstatus':forms.TextInput(attrs={'readonly':True}),
                   'ismailsent':forms.HiddenInput()
                   }
        labels = {
            'description':'Description',
            'qset':'Question Set',
            'workstatus':"Status",
           
        }
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['qset'].required = True
        
        self.fields['categories'].choices = om.TypeAssist.objects.filter((Q(client_id = S['client_id']) | Q(cuser__is_superuser = True)), tatype__tacode = 'WORKORDER_CATEGORY', enable=True).values_list('tacode', 'taname')
        self.fields['ticketcategory'].queryset = om.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        self.fields['asset'].queryset = am.Asset.objects.filter_for_dd_asset_field(self.request, ['ASSET'], sitewise=True)
        self.fields['location'].queryset = am.Location.objects.filter(Q(client_id = S['client_id']), bu_id = S['bu_id'])
        self.fields['vendor'].queryset = Vendor.objects.filter(
            Q(enable=True) & Q(client_id = S['client_id']) & Q(bu_id = S['bu_id']) | (Q(client_id = S['client_id']) & Q(show_to_all_sites = True)))
        self.fields['qset'].queryset = am.QuestionSet.objects.filter(client_id = S['client_id'], enable=True, type = am.QuestionSet.Type.WORKORDER) 
        utils.initailize_form_fields(self)
        if not self.instance.id:
            self.fields['plandatetime'].initial = timezone.now()
            self.fields['priority'].initial = Wom.Priority.LOW  
            self.fields['ticketcategory'].initial = om.TypeAssist.objects.get(tacode='AUTOCLOSED', tatype__tacode = 'NOTIFYCATEGORY')
    
    

class WorkPermitForm(forms.ModelForm):
    required_css_class = "required"
    seqno = forms.IntegerField(label="Seq. #", required=False, widget=forms.TextInput(attrs={'readonly':True}))
    class Meta:
        model = Wom
        fields = ['qset', 'seqno', 'ctzoffset']
        labels={
            'qset':'Permit to work',
            'seqno':'Seq No'
        }
        widgets = {
            'wptype':s2forms.Select2Widget
            
        }
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        
        self.fields['qset'].queryset = am.QuestionSet.objects.filter(
            type='WORKPERMIT', client_id = S['client_id'], bu_id = S['bu_id'], enable=True)