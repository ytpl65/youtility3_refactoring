from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Vendor
from apps.core import utils
from django.http import QueryDict
from django.contrib.gis.geos import GEOSGeometry



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
            'address':forms.Textarea(attrs={'rows':2})
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