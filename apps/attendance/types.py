from datetime import datetime
from graphene_django.types import DjangoObjectType
from graphene_gis.converter import gis_converter
from .models import (
    PeopleEventlog, Tracking, TestGeo
)
import graphene
from graphene import DateTime

class PELogType(DjangoObjectType):
    
    class Meta:
        model = PeopleEventlog
        fields = '__all__'
    punch_intime = graphene.String()
    punch_outtime = graphene.String(required=False)
    def resolve_punch_intime(self, info):
        return datetime()
    


class TrackingType(DjangoObjectType):
    class Meta:
        model = Tracking
        fields = '__all__'
        

class TestGeoType(DjangoObjectType):
    class Meta:
        model = TestGeo
        fields = '__all__'