from graphene_django.types import DjangoObjectType
from graphene_gis.converter import gis_converter
import graphene
from apps.attendance.models import (
    PeopleEventlog, Tracking, TestGeo
)
from apps.onboarding.models import TypeAssist
from apps.peoples.models import (
    People
)

class PELogType(DjangoObjectType):
    
    class Meta:
        model = PeopleEventlog
    

class TrackingType(DjangoObjectType):
    class Meta:
        model = Tracking
        fields = '__all__'
        

class TestGeoType(DjangoObjectType):
    class Meta:
        model = TestGeo
        fields = '__all__'
        

class PeopleType(DjangoObjectType):
    class Meta:
        model = People

     
class AuthInput(graphene.InputObjectType):
    loginid     = graphene.String(required=True)
    password    = graphene.String(required=True)
    deviceid    = graphene.String(required=True)
    
    
class AuthOutput(graphene.ObjectType):
    isauthenticated = graphene.Boolean()
    user            = graphene.Field(PeopleType)
    msg             = graphene.String()
    
    
class TaType(DjangoObjectType): 
    class Meta:
        model=TypeAssist
        fields = ['tacode', 'taname',]
        

class BaseReturnType:
    user = graphene.Field(PeopleType)
    status = graphene.Int()
    msg = graphene.String()
    

class RowInput(graphene.InputObjectType):
    columns   = graphene.List(graphene.String)
    values    = graphene.List(graphene.String)
    tablename = graphene.String()

    
class RowOutput(graphene.ObjectType):
    id = graphene.Int()
    msg = graphene.String()


