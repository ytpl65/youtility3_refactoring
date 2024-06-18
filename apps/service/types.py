from graphene_django.types import DjangoObjectType
from typing import List
import graphene
from djantic import ModelSchema
from graphene_gis.scalars import  PointScalar
from graphene_gis.converter import gis_converter  # noqa
from datetime import datetime
from apps.attendance.models import (
    PeopleEventlog, Tracking, TestGeo
)
from apps.activity.models import (
    Job, Jobneed, JobneedDetails, Asset, Question, QuestionSet, QuestionSetBelonging
)
from apps.onboarding.models import TypeAssist
from apps.peoples.models import (
    People,
    Pgbelonging,
    Pgroup
)
from graphene_file_upload.scalars import Upload

class PELogType(DjangoObjectType):

    class Meta:
        model = PeopleEventlog

class JNDType(graphene.InputObjectType):
    cuser__id   = graphene.Int(required = True)
    muser__id   = graphene.Int(required = True)
    tenant_id   = graphene.Int(required = True)
    question_id = graphene.Int(required = True)
    jobneed_id  = graphene.Int(required = True)
    seqno       = graphene.Int(required = True)
    cdtz        = graphene.String(required = True)
    mdtz        = graphene.String(required = True)
    answertype  = graphene.String(required = True)
    answer      = graphene.String(required = True)
    isavpt      = graphene.Boolean(required = True)
    ismadatory  = graphene.Boolean(required = True)
    alerts      = graphene.Boolean(required = True)
    question_id = graphene.Int(required = True)
    options     = graphene.String(required = True)
    min         = graphene.Float(required = True)
    max         = graphene.Float(required = True)

    # class Meta:
    #     model = JobneedDetails
    #     fields = ['seqno', 'cdtz', 'mdtz', 'answertype', 'answer', 'options', 'min',
    #               'max', 'alerton', 'ismadatory', 'alerts']

class JndType(DjangoObjectType):
    class Meta:
        model = JobneedDetails

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
        fields = '__all__'

class VerifyClientOutput(graphene.ObjectType):
    rc        = graphene.Int(default_value = 0)
    msg       = graphene.String()
    url = graphene.String(default_value = "")
    
class BasicOutput(graphene.ObjectType):
    rc = graphene.Int(default_value=0)
    msg = graphene.String()
    email = graphene.String()
    
class DowntimeResponse(graphene.ObjectType):
    message = graphene.String()
    startDateTime = graphene.String(default_value="")
    endDateTime = graphene.String(default_value="")

class LoginResponseType(DjangoObjectType):
    tenantid = graphene.Int()
    shiftid = graphene.Int()

    class Meta:
        model = People
        fields = [
            'peoplecode', 'loginid', 'peoplename', 'isadmin',
             'email', 'mobno']
    @staticmethod
    def resolve_tenantid(info, *args, **kwargs):
        print("called")
        print(dir(info.context))
        print(dict(info.context.GET))
        print(dict(info.context.POST))
        print(dir(info.context.body))
        print(info.context.content_params)

class AssetType(DjangoObjectType):
    class Meta:
        model = Asset

class QuestionType(DjangoObjectType):
    class Meta:
        model = Question

class QSetType(DjangoObjectType):
    class Meta:
        model = QuestionSet

class QSetBlngType(DjangoObjectType):
    class Meta:
        model = QuestionSetBelonging

class PgBlngType(DjangoObjectType):
    class Meta:
        model = Pgbelonging

class PgroupType(DjangoObjectType):
    class Meta:
        model = Pgroup



class AuthInput(graphene.InputObjectType):
    clientcode = graphene.String(required = True)
    loginid    = graphene.String(required = True)
    password   = graphene.String(required = True)
    deviceid   = graphene.String(required = True)

class AuthOutput(graphene.ObjectType):
    isauthenticated = graphene.Boolean()
    user            = graphene.Field(PeopleType)
    msg             = graphene.String()

class TyType(DjangoObjectType): 
    class Meta:
        model = TypeAssist
        fields = [
            'id', 'tacode', 'taname'
        ]

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
    msg = graphene.JSONString()



class TemplateReportInput(graphene.InputObjectType):
    questionsetid = graphene.Int(required = True)
    tablename     = graphene.String(required = True)
    columns       = graphene.List(graphene.String)
    values        = graphene.List(graphene.String)
    childs        = graphene.List(graphene.String)


class AttachmentInput(graphene.InputObjectType):
    file     = Upload(required = True)
    pelogid  = graphene.Int(required = True)
    peopleid = graphene.Int(required = True)
    filename = graphene.String(required = True)
    path     = graphene.String(required = True)



class AdhocInputType(graphene.InputObjectType):
    plandatetime = graphene.String(required = True)
    jobdesc      = graphene.String(required = True)
    bu_id        = graphene.Int(required = True)
    people_id    = graphene.Int(required = True)
    site_id      = graphene.Int(required = True)
    qset_id      = graphene.Int(required = True)
    remarks      = graphene.String(required = False)

class TestJsonInput(graphene.InputObjectType):
    file = Upload(required = True)
    sevicename = graphene.String(required = True)

class ServiceOutputType(graphene.ObjectType):
    rc        = graphene.Int(default_value = 0)
    msg       = graphene.String()
    recordcount  = graphene.Int()
    traceback = graphene.String(default_value = 'NA')
    uuids = graphene.List(graphene.String, default_value = ())



class JobSchema(ModelSchema):
    class Config:
        model = Job
        exclude = ['other_info']

class JndSchema(ModelSchema):
    class Config:
        model = JobneedDetails

class JobneedSchema(ModelSchema):
    detals: List[JndSchema]
    class Config:
        model = Jobneed
        exclude = ['other_info', 'receivedonserver']


class JobneedMdtzAfter(graphene.ObjectType):
    jobneedid         = graphene.Int()
    jobdesc           = graphene.String()
    plandatetime      = graphene.String()
    expirydatetime    = graphene.String()
    receivedonserver  = graphene.String()
    starttime         = graphene.String()
    endtime           = graphene.String()
    gpslocation       = PointScalar()
    remarks           = graphene.String()
    cdtz              = graphene.String()
    mdtz              = graphene.String()
    jobstatus         = graphene.String()
    jobtype           = graphene.String()
    pgroup_id         = graphene.Int()
    asset_id          = graphene.Int()
    cuser_id          = graphene.Int()
    muser_id          = graphene.Int()
    performedby_id    = graphene.Int()
    bu_id             = graphene.Int()
    job_id            = graphene.Int()
    seqno             = graphene.Int()
    ticketcategory_id = graphene.Int()
    ctzoffset         = graphene.Int()
    multifactor       = graphene.Decimal()
    frequency         = graphene.String()



class SelectOutputType(graphene.ObjectType):
    nrows   = graphene.Int()
    ncols    = graphene.Int()
    msg     = graphene.String()
    rc      = graphene.Int(default_value = 0)
    records = graphene.JSONString()

class UploadAttType(graphene.InputObjectType):
    record = graphene.JSONString(required = True)
    tablname = graphene.String(required = True)
    file = Upload() 
