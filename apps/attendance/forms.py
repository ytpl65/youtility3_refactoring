from datetime import datetime, timezone
from django import forms
from django_select2 import forms as s2forms
from apps.core import utils
from django.contrib.gis.geos import GEOSGeometry
import apps.attendance.models as atdm
import apps.peoples.models as pm

class AttendanceForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = atdm.PeopleEventlog
        fields = ['people', 'datefor',
         'peventtype', 'verifiedby', 'remarks','shift', 'facerecognition']
        labels = {
            'people'        : 'People',
            'punch_intime'    : 'In Time',
            'punch_outtime'   : 'Out Time',
            'datefor'         : 'For Date',
            'peventtype'      : 'Attendance Type',
            'verifiedby'      : 'Verified By',
            'facerecognition' : 'Enable FaceRecognition',
            'remarks'         : "Remark"}
        widgets = {
            'people'    : s2forms.ModelSelect2Widget(
                model     = pm.People, search_fields =  ['peoplename__icontains','peoplecode__icontains']
            ),
            'verifiedby'  : s2forms.ModelSelect2Widget(
                model     = pm.People, search_fields = ['peoplename__icontains','peoplecode__icontains']
            ),
            'shift'       : s2forms.Select2Widget,
            'peventtype'  : s2forms.Select2Widget,
        }


    def __init__(self, *args, **kwargs):
        super(AttendanceForm, self).__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['datefor'].required       = True
        self.fields['punch_intime'].required  = True
        self.fields['punch_outtime'].required = True
        self.fields['verifiedby'].required    = True
        self.fields['people'].required        = True
        self.fields['peventtype'].required    = True
        self.fields['shift'].initial          = 1

    def is_valid(self) -> bool:
        """Adds 'is-invalid' class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result 
    
def clean_geometry(val):
    try:
        val = GEOSGeometry(val)
    except ValueError:
        raise forms.ValidationError('lat lng string input unrecognized!')
    else: return val


class ConveyanceForm(forms.ModelForm):
    required_css_class = "required"
    class Meta:
        model=atdm.PeopleEventlog
        fields = ['people', 'transportmodes', 'expamt', 'duration', 'distance', 'startlocation', 'endlocation']

    
    def __ini__(self, *args, **kwargs):
        super(ConveyanceForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            if visible.name in ['startlocation', 'endlocation', 'expamt', 'transportmodes']:
                visible.required = False
        utils.initailize_form_fields(self)
    
    
    def is_valid(self) -> bool:
        """Adds 'is-invalid' class to invalid fields"""
        result = super().is_valid()
        utils.apply_error_classes(self)
        return result
    
    def clean_startlocation(self):
        if val := self.cleaned_data.get('startlocation'):
            print("%%%%%%%%%%%%%%%%%55", val)
            val = clean_geometry(val)
        return val    
    
    def clean_endlocation(self):
        if val := self.cleaned_data.get('endlocation'):
            val = clean_geometry(val)
        return val
    
    def clean_journeypath(self):
        if val := self.cleaned_data.get('journeypath'):
            val = clean_geometry(val)
        return val




class TrackingForm(forms.ModelForm):
    gpslocation = forms.CharField(max_length=200, required=True)
    class Meta:
        model = atdm.Tracking
        fields = ['deviceid', 'gpslocation', 'reference', 'recieveddate', 
                  'people', 'transportmode','amount', 'identifier']
        
    def clean_gpslocation(self):
        if val := self.cleaned_data.get('gpslocation'):
            val = clean_geometry(val)
        return val