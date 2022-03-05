from django import forms
from django_select2 import forms as s2forms
import apps.onboarding.utils as ob_utils
import apps.attendance.models as atdm
import apps.peoples.models as pm

class AttendanceForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = atdm.PeopleEventlog
        fields = ['people', 'punch_intime', 'punch_outtime', 'datefor',
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
        ob_utils.initailize_form_fields(self)
        self.fields['datefor'].required       = True
        self.fields['punch_intime'].required  = True
        self.fields['punch_outtime'].required = True
        self.fields['verifiedby'].required    = True
        self.fields['people'].required      = True
        self.fields['peventtype'].required    = True
        self.fields['shift'].initial          = 1

    def is_valid(self) -> bool:
        """Adds 'is-invalid' class to invalid fields"""
        result = super().is_valid()
        ob_utils.apply_error_classes(self)
        return result 
    
class ConveyanceForm(forms.ModelForm):
    required_css_class = "required"
    class Meta:
        model=atdm.PeopleEventlog
        fields = ['people', 'transportmodes', 'expamt', 'duration', 'distance', 'punch_intime',
                  'punch_outtime', 'startlocation', 'endlocation']
    
    def __ini__(self, *args, **kwargs):
        super(ConveyanceForm, self).__init__(*args, **kwargs)
        ob_utils.initailize_form_fields(self)
    
    
    def is_valid(self) -> bool:
        """Adds 'is-invalid' class to invalid fields"""
        result = super().is_valid()
        ob_utils.apply_error_classes(self)
        return result 