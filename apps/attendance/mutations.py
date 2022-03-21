import graphene
from graphene_django import DjangoObjectType
from graphene_gis.scalars import LineStringScalar, PointScalar, PolygonScalar
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.geos import(
    Point, LineString, Polygon
)
from graphene_django.forms.mutation import DjangoModelFormMutation
from pytest import PytestUnhandledCoroutineWarning
from .types import (
    PELogType, TrackingType, TestGeoType
)
from .models import (
     Tracking, TestGeo
)
from .forms import (
    ConveyanceForm, TrackingForm 
)
from apps.onboarding.models import TypeAssist
from apps.onboarding.forms import TypeAssistForm
    
class PELogMutation(DjangoModelFormMutation):
    PELog = graphene.Field(PELogType)
    class Meta:
        form_class        = ConveyanceForm
        return_field_name = 'output'
        fields = (
            'deviceid', 'shift_id', 'people_id', 'client_id', 'bu_id', 'transportmodes',
            'punch_intime', 'datefor', 'expamt', 'startlocation', 'endlocation',
            'peventtype_id')


class TrackingMutation(DjangoModelFormMutation):
    TrackingType = graphene.Field(TrackingType)
    
    class Meta:
        model             = Tracking
        form_class        = TrackingForm
        return_field_name = 'output'
        

        

class TestGeoMutation(graphene.Mutation):
    #class arguments which can be returned in response
    code = graphene.String()
    point = PointScalar()
    line = LineStringScalar()
    poly = PolygonScalar()

    
    class Arguments:
        #The input arguments for this mutation
        id    = graphene.ID()
        code  = graphene.String()
        point = graphene.String(required=False)
        poly  = graphene.String(required=False)
        line  = graphene.String(required=False)
        
    
    def mutate(self, info, code, point=Point(), poly=Polygon(), line=LineString()):
        testGeo = TestGeo(
            code=code,
            point= GEOSGeometry(point),
            poly = GEOSGeometry(poly),
            line = GEOSGeometry(line)
        )
        testGeo.save()

        return TestGeoMutation(
            code = testGeo.code,
            point= testGeo.point,
            poly = testGeo.poly,
            line = testGeo.line
        )
        
class TaType(DjangoObjectType): 
    class Meta:
        model=TypeAssist
        fields = ['tacode', 'taname',]
        
        
class AddTaMutation(DjangoModelFormMutation):
    typeassist = graphene.Field(TaType)
    
    class Meta:
        form_class=TypeAssistForm
        return_field_name = 'output'

    
    @classmethod
    def perform_mutate(cls, form, info):
        obj = form.save()
        kwargs = {cls._meta.return_field_name: obj, 'ta':obj}
        return cls(errors=[], **kwargs)
