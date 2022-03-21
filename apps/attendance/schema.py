import graphene
from .models import (
    PeopleEventlog, Tracking, TestGeo
)
from .types import (
    PELogType, TrackingType, TestGeoType
)
from .mutations import (
    PELogMutation, TrackingMutation, TestGeoMutation, AddTaMutation
)

class Query(graphene.ObjectType):
    PELogs    = graphene.List(PELogType, event_id=graphene.Int())
    trackings = graphene.List(TrackingType)
    testcases = graphene.List(TestGeoType)
    
    '''query-resolutions'''
    @staticmethod
    def resolve_PELogs(self, info, event_id):
        return PeopleEventlog.objects.filter(
            peventtype_id = event_id).order_by('-mdtz')
    @staticmethod
    def resolve_trackings(self, info):
        return Tracking.objects.all()
    @staticmethod
    def resole_testcases(self, info):
        objs = TestGeo.objects.all()
        ic(objs)
        return list(objs)


class Mutation(graphene.ObjectType):
    create_peopleevent    = PELogMutation.Field() 
    create_tracking = TrackingMutation.Field()
    create_GEOS     = TestGeoMutation.Field()
    create_typeassist = AddTaMutation.Field()
    


schema = graphene.Schema(query=Query, mutation=Mutation)