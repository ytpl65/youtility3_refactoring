from django import forms
from .models import Ticket, EscalationMatrix
from apps.onboarding.models import TypeAssist
from apps.core import utils
from apps.peoples.models import Pgroup
from apps.activity.models import Location
class TicketForm(forms.ModelForm):
    required_css_class = "required"

    class Meta:
        model = Ticket
        fields = [
            'ticketdesc', 'assignedtopeople', 'assignedtogroup', 'priority', 'ctzoffset',
            'ticketcategory', 'status', 'comments', 'location', 'cdtz',
            'isescalated', 'ticketsource'
        ]
        labels = {
            'assignedtopeople':'User', 'assignedtogroup':"User Group", 'ticketdesc':"Subject",
            'cdtz':"Created On", 'ticketcategory':"Queue",
            "isescalated":"Is Escalated"
        }
        widgets={
            'comments' : forms.Textarea(attrs={'rows': 2, 'cols': 40}),
            'isescalated':forms.TextInput(attrs={'readonly':True})
        }
        

    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        S = self.request.session
        super().__init__(*args, **kwargs)
        self.fields['assignedtogroup'].required=True
        self.fields['ticketdesc'].required=True
        self.fields['ticketcategory'].required=True
        self.fields['priority'].required=True
        self.fields['comments'].required=False
        self.fields['ticketsource'].initial=Ticket.TicketSource.USERDEFINED
        self.fields['ticketsource'].widget.attrs = {'style':"display:none"}
        
        #filters for dropdown fields
        self.fields['assignedtogroup'].queryset = Pgroup.objects.filter(bu_id = S['bu_id'], identifier__tacode__in = ['PEOPLEGROUP', 'PEOPLE_GROUP'], enable=True)
        self.fields['ticketcategory'].queryset = TypeAssist.objects.filter(tatype__tacode='TICKETCATEGORY', client_id = S{'client_id'})
        self.fields['location'].queryset = Location.objects.filter(bu_id = S['bu_id'], enable=True).exclude(loccode='NONE')
        utils.initailize_form_fields(self)
        if not self.instance.id:
            self.fields['status'].initial = 'NEW'
    
    def clean(self):
        super().clean()
        cd = self.cleaned_data
        ic(cd)
        if cd['assignedtopeople'] is None and cd['assignedtogroup'] is None:
            raise forms.ValidationError("Make Sure You Assigned Ticket Either People OR Group")
        self.cleaned_data = self.check_nones(self.cleaned_data)
        ic(self.cleaned_data)
        
    def clean_ticketdesc(self):
        if val:= self.cleaned_data.get('ticketdesc'):
            val = val.strip()
            val.capitalize()
        return val
    
    def clean_comments(self):
        return val.strip() if (val:= self.cleaned_data.get('comments')) else val
    
    def check_nones(self, cd):
        fields = {
            'location':'get_or_create_none_location',
            'assignedtopeople': 'get_or_create_none_people',
            'assignedtogroup': 'get_or_create_none_pgroup',}
        for field, func in fields.items():
            if cd.get(field) in [None, ""]:
                cd[field] = getattr(utils, func)()
        return cd
    


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