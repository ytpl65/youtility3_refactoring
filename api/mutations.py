from urllib import request
import graphene
from graphene_django import DjangoObjectType
from django.db import transaction
from django.db.utils import IntegrityError
from graphene_gis.scalars import LineStringScalar, PointScalar, PolygonScalar
from  graphql_jwt.shortcuts import get_token, get_payload
from graphql_jwt.decorators import login_required
from django.contrib.gis.geos import GEOSGeometry
from graphql_jwt import ObtainJSONWebToken
from graphene.types.generic import GenericScalar
from django.contrib.gis.geos import(
    Point, LineString, Polygon
)
from graphql import GraphQLError

from graphene_django.forms.mutation import DjangoModelFormMutation
from django.utils import timezone
from zmq import MECHANISM

from apps.activity.models import Jobneed
from apps.peoples.models import People
from .types import (
    PELogType, TrackingType, PeopleType, RowInput, RowOutput, AuthInput
)
from apps.attendance.models import (
     PeopleEventlog, Tracking, TestGeo
)
from apps.attendance.forms import (
    InsertPeopleEventlog, TrackingForm 
)
from apps.onboarding.models import TypeAssist
from apps.onboarding.forms import TypeAssistForm
from apps.core import utils
from .auth import Messages as AM

class BaseReturnType:
    user = graphene.Field(PeopleType)
    status = graphene.Int()
    msg = graphene.String()

class Messages(AM):
    INSERT_SUCCESS = "Inserted Successfully!"
    INSERT_FAILED = "Failed to insert!"
    WRONG_OPERATION = "Wrong operation 'id' is passed during insertion!"
    DBERROR = "Integrity Error!"
    

def get_model(tablename):
    match tablename:
        case "peopleeventlog":
            return PeopleEventlog
        case 'jobneed':
            return Jobneed
        case _:
            return None
        



########################### BEGIN GLOBAL INSERT RECORD ##############################

########################### END GLOBAL INSERT RECORD ##############################

class InsertRecord(graphene.Mutation):
    output = graphene.Field(RowOutput)
    class Arguments:
        input = RowInput(required = True)

    
    @classmethod
    @login_required
    def mutate(cls, root, info, input):
        model, id = get_model(input.tablename.lower()), None
        if not model or len(input.columns) != len(input.values):
            raise GraphQLError(Messages.INSERT_FAILED)

        try:
            if 'id' in input.columns:
                raise ValueError
            instance = cls.create_record(model, input)
            msg = Messages.INSERT_SUCCESS
            output = RowOutput(msg = msg, id = instance.id)
            return InsertRecord(output=output)
        except ValueError as e:
            raise Exception(Messages.WRONG_OPERATION) from e
        except IntegrityError as e:
            raise Exception(f'{Messages.DBERROR} {e}') from e
        except Exception as e:
            raise Exception(f'{Messages.INSERT_FAILED} {e}') from e
            

    @classmethod
    def create_record(cls, model, input):
        """
        Insert record in specified table
        """
        record = dict(zip(input.columns, input.values))
        record = utils.clean_record(record)
        with transaction.atomic():
            return model.objects.create(**record)



class UpdateRecord(graphene.Mutation):
    output = graphene.Field(RowOutput)
    class Arguments:
        input = RowInput(required=True)
        
    def mutate(cls, root, info, input):
        model = get_model(input.table)





######################### START PEOPLEEVENTLOG MUTATION #########################
class PELogMutation(DjangoModelFormMutation, BaseReturnType):
    output = graphene.Field(PELogType)
    
    class Meta:
        form_class = InsertPeopleEventlog
        return_field_name = 'output'

    @classmethod
    def perform_mutate(cls, form, info):
        obj = form.save(commit=True)
        obj.cdtz = form.data['cdtz']
        obj.mdtz = form.data['mdtz']
        obj.save()
        kwargs = {
            'output':obj, 'user':info.context.user
            }
        return cls(errors=[], **kwargs)
######################### END PEOPLEEVENTLOG MUTATION #########################



######################### START TRACKING MUTATION #########################
class TrackingMutation(DjangoModelFormMutation):
    TrackingType = graphene.Field(TrackingType)
    
    class Meta:
        model             = Tracking
        form_class        = TrackingForm
        return_field_name = 'output'
######################### END TRACKING MUTATION #########################

        
######################### START TYPEASSIST MUTATION #########################
class TaType(DjangoObjectType): 
    class Meta:
        model=TypeAssist
        fields = ['tacode', 'taname',]
        
        
class AddTaMutation(DjangoModelFormMutation):
    input = graphene.Field(TaType)
    
    class Meta:
        form_class=TypeAssistForm
        return_field_name = 'output'
    
    @classmethod
    def perform_mutate(cls, form, info):
        obj = form.save()
        kwargs = {cls._meta.return_field_name: obj, 'typeassist':obj}
        return cls(errors=[], **kwargs)
######################### END TYPEASSIST MUTATION #########################


######################### START AUTHENTICATION #########################

class LoginUser(graphene.Mutation):
    """Authenticates user before log in"""
    token = graphene.String()
    user = graphene.Field(PeopleType)
    payload = GenericScalar()
    msg = graphene.String()
    
    class Arguments:
        input =  AuthInput(required=True)
    
    @classmethod
    def mutate(cls, root, info, input):
        try:
            from .auth import authenticate_user
            output, user = authenticate_user(input, info.context,  Messages(), cls.returnUser)
            cls.updateDeviceId(user, input)
            return output
        except Exception as exc:
            raise GraphQLError(exc) from exc
            
    
    @classmethod
    def returnUser(cls, user, request):
        user.last_login = timezone.now()
        user.save()
        token = get_token(user)
        return LoginUser(token=token, user=user, payload = get_payload(token, request))
    
    
    @classmethod
    def updateDeviceId(cls, user, input):
        People.objects.update_deviceid(input.deviceid, user.id)



    
class LogoutUser(graphene.Mutation):
    """
    Logs out user after resetting the deviceid 
    """
    status = graphene.Int(default_value = 404)
    msg    = graphene.String(default_value = "Failed")

    
    @login_required
    def mutate(self, info):
        updated = People.objects.reset_deviceid(info.context.user.id)
        if updated: status, msg = 200, "Success"
        return LogoutUser(status=status, msg=msg)
                
        
            
        
        
    


        


######################### END AUTHENTICATION ###########################


######################### START TESTGEO MUTATION #########################
# class TestGeoMutation(graphene.Mutation):
#     code = graphene.String()
#     point = PointScalar()
#     line = LineStringScalar()
#     poly = PolygonScalar()

    
#     class Arguments:
#         #The input arguments for this mutation
#         id    = graphene.ID()
#         code  = graphene.String()
#         point = graphene.String(required=False)
#         poly  = graphene.String(required=False)
#         line  = graphene.String(required=False)
        
    
#     def mutate(self, info, code, point=Point(), poly=Polygon(), line=LineString()):
#         testGeo = TestGeo(
#             code=code,
#             point= GEOSGeometry(point),
#             poly = GEOSGeometry(poly),
#             line = GEOSGeometry(line)
#         )
#         testGeo.save()

#         return TestGeoMutation(
#             code = testGeo.code,
#             point= testGeo.point,
#             poly = testGeo.poly,
#             line = testGeo.line
#         )
######################### END TESTGEO MUTATION #########################
