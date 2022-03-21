import graphene
from graphene_django.debug import DjangoDebug
import apps.attendance.schema as  atd_schema


class Query(atd_schema.Query):
    debug = graphene.Field(DjangoDebug, name='_debug')
    pass

class Mutation(atd_schema.Mutation):
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)