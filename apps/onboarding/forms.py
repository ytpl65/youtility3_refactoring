#imports from standard library

#imports from django core
from django import forms
from django.utils.translation import ugettext_lazy as _

#imports from thirdparty apps

#import from this project
from .models import TypeAssist


class TypeAssistForm(forms.ModelForm): 
    #error_css_class = "error"
    required_css_class = "required"
    
    class Meta:
        model  = TypeAssist
        fields = ['tacode', 'taname', 'tatype', 'parent']
        labels = {
            'tacode': "Code",
            'taname': "Name",
            'tatype':'Type',
            'parent':'Parent'
        }
    
    def __init__(self, *args, **kwargs):
        super(TypeAssistForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    