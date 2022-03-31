import graphene
import graphql_jwt
from graphql_auth.schema import  MeQuery
from graphql_jwt.decorators import login_required
from graphene_django.debug import DjangoDebug
from .mutations import (
  PELogMutation, TrackingMutation,  AddTaMutation,  InsertRecord,
  LoginUser, LogoutUser, UpdateRecord
)
from .types import (
    PELogType, PeopleType, TrackingType, TestGeoType
)
from apps.attendance.models import (
    PeopleEventlog, Tracking, TestGeo
)

class Mutation(graphene.ObjectType):
    token_auth    = LoginUser.Field()
    logout_user   = LogoutUser.Field()
    verify_token  = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    revoke_token  = graphql_jwt.Revoke.Field()

    create_peopleevent = PELogMutation.Field()
    create_tracking    = TrackingMutation.Field()
    #create_GEOS       = TestGeoMutation.Field()
    create_typeassist  = AddTaMutation.Field()
    insert_record      = InsertRecord.Field()
    update_record      = UpdateRecord.Field()

class Query(MeQuery, graphene.ObjectType):
    PELog_by_id = graphene.Field(PELogType, id = graphene.Int())
    trackings   = graphene.List(TrackingType)
    testcases   = graphene.List(TestGeoType)
    viewer      = graphene.Field(PeopleType)
    '''query-resolutions'''
    
    @staticmethod
    def resolve_PELog_by_id(self, info, id):
        return PeopleEventlog.objects.get(
            id = id)
    @staticmethod
    def resolve_trackings(self, info):
        return Tracking.objects.all()
    @staticmethod
    def resole_testcases(self, info):
        objs = TestGeo.objects.all()
        return list(objs)
    
    @login_required
    def resolve_viewer(self, info, **kwargs):
        return info.context.user
















class RootQuery(Query):
    debug = graphene.Field(DjangoDebug, name='_debug')
    pass

class RootMutation(Mutation):
    pass

schema = graphene.Schema(query=RootQuery, mutation=RootMutation)