from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Vendor, Wom
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
        fields = ['code', 'name', 'address', 'mobno',
                  'email', 'ctzoffset', 'enable', 'address']
        labels = {
            'code':"Code",
            'name':"Name",
            'address':"Address",
            'mobno':"Mob no",
            'email':"Email"
        }
        widgets = {
            'address':forms.Textarea(attrs={'rows':4}),
            'code':forms.TextInput(attrs={'style': "text-transform: uppercase;"})
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
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
    timeInChoices      = [('MINS', 'Min'),('HRS', 'Hour'), ('DAYS', 'Day')]
    
    gracetime_type     = forms.ChoiceField(choices = timeInChoices, initial='MIN', widget = s2forms.Select2Widget)

    
    class Meta:
        model = Wom
        fields = ['description', 'plandatetime', 'expirydatetime', 'gracetime', 'asset', 'location',
                  'priority', 'qset', 'ticketcategory', 'categories', 'vendor', 'ctzoffset']
        
        widgets = {'categories':s2forms.Select2MultipleWidget,
                   'vendor'    : s2forms.Select2Widget,
                   'description':forms.Textarea(attrs={'rows':3})
                   }
        labels = {
            'description':'Description',
        }
        
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['ticketcategory'].queryset = om.TypeAssist.objects.filter_for_dd_notifycategory_field(self.request, sitewise=True)
        self.fields['asset'].queryset = am.Asset.objects.filter_for_dd_asset_field(self.request, ['ASSET'], sitewise=True)
        self.fields['vendor'].queryset = Vendor.objects.filter(enable=True, client_id = S['client_id'])
        utils.initailize_form_fields(self)
        if not self.instance.id:
            self.fields['plandatetime'].initial = timezone.now()
            self.fields['priority'].initial = Wom.Priority.LOW  
            self.fields['ticketcategory'].initial = om.TypeAssist.objects.get(tacode='AUTOCLOSED', tatype__tacode = 'NOTIFYCATEGORY')
    
    
    def clean(self):
        super().clean()
        cd          = self.cleaned_data
        times_names = ['gracetime']
        types_names = ['gracetime_type']
        
        times = [cd.get(time) for time in times_names]
        types = [cd.get(type) for type in types_names]
        for time, type, name in zip(times, types, times_names):
            self.cleaned_data[name] = self.convertto_mins(type, time)
            
    @staticmethod
    def convertto_mins(_type, _time):
        if _type == 'HRS':
            return _time * 60
        return _time * 24 * 60 if _type == 'DAYS' else _time