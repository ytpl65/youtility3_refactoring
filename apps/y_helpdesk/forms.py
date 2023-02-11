from django import forms
from .models import Ticket, EscalationMatrix
from apps.onboarding.models import TypeAssist
from apps.core import utils

class TicketForm(forms.ModelForm):
    required_css_class = "required"
    ASSIGNTO_CHOICES   = [('PEOPLE', 'People'), ('GROUP', 'Group of people')]
    assign_to          = forms.ChoiceField(choices = ASSIGNTO_CHOICES, initial="PEOPLE")

    class Meta:
        model = Ticket
        fields = [
            'ticketdesc', 'assignedtopeople', 'assignedtogroup', 'priority', 'ctzoffset',
            'ticketcategory', 'status', 'comments', 'assign_to', 'location', 'cuser', 'cdtz',
            'isescalated', 'ticketsource'
        ]
        labels = {
            'assignedtopeople':'People', 'assignedtogroup':"Group of people", 'ticketdesc':"Subject",
            'cuser':"Created By", 'cdtz':"Created On", 'ticketcategory':"Ticket Category",
            "isescalated":"Is Escalated"
        }
        widgets={
            'comments' : forms.Textarea(attrs={'rows': 2, 'cols': 40}),
            'isescalated':forms.TextInput(attrs={'readonly':True})
        }
        

    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['ticketdesc'].required=True
        self.fields['ticketcategory'].required=True
        self.fields['priority'].required=True
        self.fields['comments'].required=False
        self.fields['ticketsource'].initial=Ticket.TicketSource.USERDEFINED
        self.fields['ticketsource'].widget.attrs = {'style':"display:none"}
        self.fields['ticketcategory'].queryset = TypeAssist.objects.filter(tatype__tacode='TICKETCATEGORY')
        if not self.instance.id:
            self.fields['status'].initial = 'NEW'
    
    def clean(self):
        super().clean()
        cd = self.cleaned_data
        if not (cd['assignedtopeople'] and cd['assignedtogroup']):
            raise forms.ValidationError("Make Sure You Assigned Ticket Either People OR Group")
        if cd['assign_to'] == 'PEOPLE':
            cd['assignedtogroup'] = utils.get_or_create_none_pgroup()
        else:
            cd['assignedtopeople'] = utils.get_or_create_none_people()
        
        
        
        
    def clean_ticketdesc(self):
        if val:= self.cleaned_data.get('ticketdesc'):
            val = val.strip()
            val.capitalize()
        return val
    
    def clean_comments(self):
        return val.strip() if (val:= self.cleaned_data.get('comments')) else val
    


# create a ModelForm
class EscalationForm(forms.ModelForm):
    # specify the name of model to use
    class Meta:
        model = EscalationMatrix
        fields = ['escalationtemplate', 'ctzoffset']
        labels = {
            'escalationtemplate':"Escalation Template"
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)
        utils.initailize_form_fields(self)
        self.fields['escalationtemplate'].queryset = TypeAssist.objects.filter(
            tatype__tacode__in = ['TICKETCATEGORY', 'TICKET_CATEGORY'])