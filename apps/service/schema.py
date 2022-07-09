import graphene
import graphql_jwt
from graphql_auth.schema import  MeQuery
from graphql_jwt.decorators import login_required
from graphene_django.debug import DjangoDebug
from .mutations import (
  InsertRecord, AdhocMutation,
  LoginUser, LogoutUser,
  ReportMutation,  TaskTourUpdate,
  UploadAttMutaion, SyncMutation, InsertJsonMutation
)
from .types import (
    PELogType, PeopleType, TrackingType, TestGeoType, TyType
)
from apps.attendance.models import (
    PeopleEventlog, Tracking, TestGeo
)
from .querys import Query as ApiQuery
from apps.onboarding.models import TypeAssist


class Mutation(graphene.ObjectType):
    token_auth          = LoginUser.Field()
    logout_user         = LogoutUser.Field()
    insert_record       = InsertRecord.Field()
    #update_record      = UpdateRecord.Field()
    #create_peopleevent = PELogMutation.Field()
    #create_tracking    = TrackingMutation.Field()
    #create_GEOS        = TestGeoMutation.Field()
    #create_typeassist  = AddTaMutation.Field()
    update_task_tour    = TaskTourUpdate.Field()
    #template_report    = TemplateReport.Field()
    #testJsonFile       = TestJsonMutation.Field()
    upload_report       = ReportMutation.Field()
    upload_attachment   = UploadAttMutaion.Field()
    sync_upload         = SyncMutation.Field()
    adhoc_record      = AdhocMutation.Field()
    insert_json      = InsertJsonMutation.Field()


class Query(MeQuery, ApiQuery,  graphene.ObjectType):
    PELog_by_id = graphene.Field(PELogType, id = graphene.Int())
    trackings   = graphene.List(TrackingType)
    testcases   = graphene.List(TestGeoType)
    viewer      = graphene.String()
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
        return  "validtoken" if info.context.user.is_authenticated else "tokenexpired"




class RootQuery(Query):
    debug = graphene.Field(DjangoDebug, name='_debug')
    pass

class RootMutation(Mutation):
    pass

schema = graphene.Schema(query=RootQuery, mutation=RootMutation)