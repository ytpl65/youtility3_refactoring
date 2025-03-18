from django import forms
from .models import Employee, Reference

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'
        exclude = ['created_at', 'updated_at', 'approval_status', 'remarks']
        
class ReferenceForm(forms.ModelForm):
    class Meta:
        model = Reference
        exclude = ('employee',)

ReferenceFormSet = forms.inlineformset_factory(
    Employee,
    Reference,
    form=ReferenceForm,
    extra=0,  # Show 2 reference forms
    min_num=2,  # Require 2 references
    validate_min=True,
)