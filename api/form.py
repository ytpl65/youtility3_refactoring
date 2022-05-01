from dis import dis
from os import access
import re
from attr import field
from django import forms
from apps.attendance.models import PeopleEventlog
from apps.activity.models import Jobneed, JobneedDetails
import api.validators as vds
from graphql import GraphQLError




class CommonCleanMethods(forms.ModelForm):
    def clean_jobdesc(self):
        return vds.clean_text(self.cleaned_data.get('jobdesc'))
    
    def clean_gracetime(self):
        if val:= self.cleaned_data.get('gracetime'):
            int(val)
        return val
    
    def clean_gpslocation(self):
        try:
            if val:= self.cleaned_data.get('gpslocation'):
                vds.clean_point_field(val)
        except Exception as e:
            raise GraphQLError(
                "Unable to clean Lat/Lng field make sure its in proper format!"
            ) from e
            
    def clean_startlocation(self):
        try:
            if val:= self.cleaned_data.get('startlocation'):
                vds.clean_point_field(val)
            return val
        except Exception as e:
            raise GraphQLError(
                "Unable to clean Lat/Lng field make sure its in proper format!"
            ) from e

    def clean_endlocation(self):
        try:
            if val:= self.cleaned_data.get('endlocation'):
                vds.clean_point_field(val)
            return val
        except Exception as e:
            raise GraphQLError(
                "Unable to clean Lat/Lng field make sure its in proper format!"
            ) from e
    
    def clean_answer(self):
        if val:= self.cleaned_data.get('answer'):
            val = vds.clean_text(val)
        return val
    
    def clean_remarks(self):
        if val:= self.cleaned_data.get('remarks'):
            val = vds.clean_text(val)
        return val
    
    def clean_othersite(self):
        if val:= self.cleaned_data.get('remarks'):
            val = vds.clean_text(val)
        return val


    




class JobneedFormApi(CommonCleanMethods):
    class Meta:
        model = Jobneed
        exclude = [
            'asset', 'job', 'performedby', 'people', 'pgroup',
            'parent', 'client', 'bu', 'ticketcategory', 'other_info'
        ]
    
    def clean(self):
        super(JobneedFormApi, self).clean()
        pdt = self.cleaned_data.get('plandatetime')
        edt = self.cleaned_data.get('expirydatetime')
        offset = self.cleaned_data.get('ctzoffset')
        if pdt and edt:
            pdt = vds.clean_datetimes(pdt, offset)
            edt = vds.clean_datetimes(edt, offset)
        if pdt and edt and  not pdt < edt:
            raise forms.ValidationError("Incorrect plandatetime and expirydatetime!")



class PELFormApi(CommonCleanMethods):
    class Meta:
        model = PeopleEventlog
        exclude = [
            'people', 'client', 'shift', 'verifiedby', 'geofence', 'peventtype',
            'peventlogextras', 'journeypath'
        ]
    
    def clean(self):
        super(PELFormApi, self).clean()
        cdtz    = self.cleaned_data.get('cdtz')
        mdtz    = self.cleaned_data.get('mdtz')
        tz      = self.cleaned_data.get('tzoffset')
        intime  = self.cleaned_data.get('punchintime')
        outtime = self.cleaned_data.get('punchouttime')
        self.cleaned_data['cdtz'] = vds.clean_datetimes(cdtz, tz)
        self.cleaned_data['mdtz'] = vds.clean_datetimes(mdtz, tz)
        self.cleaned_data['punchintime'] = vds.clean_datetimes(intime, tz)
        self.cleaned_data['punchouttime'] = vds.clean_datetimes(outtime, tz)
        

class JndFormApi(CommonCleanMethods):
    class Meta:
        model = JobneedDetails
        exclude = [
            'question', 'jobneed'
        ]