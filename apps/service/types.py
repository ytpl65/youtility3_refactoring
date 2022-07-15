from graphene_django.types import DjangoObjectType
from typing import List
import graphene
from djantic import ModelSchema
from pydantic import BaseModel,  validator
from graphene_gis.scalars import  PointScalar
from graphene_gis.converter import gis_converter  # noqa
from datetime import datetime
from enum import Enum
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
    cuser__id   = graphene.Int(required=True)
    muser__id   = graphene.Int(required=True)
    tenant_id   = graphene.Int(required=True)
    question_id = graphene.Int(required=True)
    jobneed_id  = graphene.Int(required=True)
    seqno       = graphene.Int(required=True)
    cdtz        = graphene.String(required=True)
    mdtz        = graphene.String(required=True)
    answertype  = graphene.String(required=True)
    answer      = graphene.String(required=True)
    isavpt      = graphene.Boolean(required=True)
    ismadatory  = graphene.Boolean(required=True)
    alerts      = graphene.Boolean(required=True)
    question_id = graphene.Int(required=True)
    options     = graphene.String(required=True)
    min         = graphene.Float(required=True)
    max         = graphene.Float(required=True)


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
    rc        = graphene.Int(default_value=0)
    msg       = graphene.String()
    url = graphene.String(default_value = "")

class LoginResponseType(DjangoObjectType):
    tenantid = graphene.Int()
    shiftid = graphene.Int()

    class Meta:
        model = People
        fields = [
            'peoplecode', 'loginid', 'peoplename', 'isadmin',
             'email', 'mobno']
    def resolve_tenantid(self, info, *args, **kwargs):
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
        model=Pgbelonging

class PgroupType(DjangoObjectType):
    class Meta:
        model = Pgroup





class AuthInput(graphene.InputObjectType):
    loginid     = graphene.String(required=True)
    password    = graphene.String(required=True)
    deviceid    = graphene.String(required=True)


class AuthOutput(graphene.ObjectType):
    isauthenticated = graphene.Boolean()
    user            = graphene.Field(PeopleType)
    msg             = graphene.String()


class TyType(DjangoObjectType): 
    class Meta:
        model=TypeAssist
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
    questionsetid = graphene.Int(required=True)
    tablename     = graphene.String(required=True)
    columns       = graphene.List(graphene.String)
    values        = graphene.List(graphene.String)
    childs        = graphene.List(graphene.String)



class AttachmentInput(graphene.InputObjectType):
    file     = Upload(required=True)
    pelogid  = graphene.Int(required=True)
    peopleid = graphene.Int(required=True)
    filename = graphene.String(required=True)
    path     = graphene.String(required=True)




class AdhocInputType(graphene.InputObjectType):
    plandatetime = graphene.String(required=True)
    jobdesc      = graphene.String(required=True)
    bu_id        = graphene.Int(required=True)
    people_id    = graphene.Int(required=True)
    site_id      = graphene.Int(required=True)
    qset_id      = graphene.Int(required=True)
    remarks      = graphene.String(required=False)


class TestJsonInput(graphene.InputObjectType):
    file = Upload(required=True)
    sevicename = graphene.String(required=True)


class ServiceOutputType(graphene.ObjectType):
    rc        = graphene.Int(default_value=0)
    msg       = graphene.String()
    recordcount  = graphene.Int()
    traceback = graphene.String(default_value = 'NA')




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



class TemplateReportSchema(BaseModel):
    parent: JobneedSchema
    childs:List[JobneedSchema]

class AnswerType(str, Enum):
    CHECKBOX    = 'CHECKBOX'   
    DATE        = 'DATE'       
    DROPDOWN    = 'DROPDOWN'   
    EMAILID     = 'EMAILID'    
    MULTILINE   = 'MULTILINE'  
    NUMERIC     = 'NUMERIC'    
    SIGNATURE   = 'SIGNATURE'  
    SINGLELINE  = 'SINGLELINE' 
    TIME        = 'TIME'       
    RATING      = 'RATING'     
    BACKCAMERA  = 'BACKCAMERA' 
    FRONTCAMERA = 'FRONTCAMERA'
    PEOPLELIST  = 'PEOPLELIST' 
    SITELIST    = 'SITELIST'   


class Frequency(str, Enum):
    NONE        = 'NONE'       
    DAILY       = 'DAILY'      
    WEEKLY      = 'WEEKLY'     
    MONTHLY     = 'MONTHLY'    
    BIMONTHLY   = 'BIMONTHLY'  
    QUARTERLY   = 'QUARTERLY'  
    HALFYEARLY  = 'HALFYEARLY' 
    YEARLY      = 'YEARLY'     
    FORTNIGHTLY = 'FORTNIGHTLY'


class JobStatus(str, Enum):
    ASSIGNED           = 'ASSIGNED'          
    AUTOCLOSED         = 'AUTOCLOSED'        
    COMPLETED          = 'COMPLETED'         
    INPROGRESS         = 'INPROGRESS'        
    PARTIALLYCOMPLETED = 'PARTIALLYCOMPLETED'
    RESOLVED           = 'RESOLVED'          
    OPEN               = 'OPEN'              
    CANCELLED          = 'CANCELLED'         
    ESCALATED          = 'ESCALATED'         
    NEW                = 'NEW'               
    MAINTENANCE        = 'MAINTENANCE'       
    STANDBY            = 'STANDBY'           
    WORKING            = 'WORKING'           
    SCRAPPED           = 'SCRAPPED'          


class JobIdentifier(str, Enum):
    TASK             = 'TASK'            
    TICKET           = 'TICKET'          
    INTERNALTOUR     = 'INTERNALTOUR'    
    EXTERNALTOUR     = 'EXTERNALTOUR'    
    PPM              = 'PPM'             
    OTHER            = 'OTHER'           
    SITEREPORT       = 'SITEREPORT'      
    INCIDENTREPORT   = 'INCIDENTREPORT'  
    ASSETLOG         = 'ASSETLOG'        
    ASSETMAINTENANCE = 'ASSETMAINTENANCE'


class JobType(str, Enum):
    SCHEDULE = 'SCHEDULE'
    ADHOC    = 'ADHOC'


class Scantype(str, Enum):
    NONE    = 'NONE'
    QR      = 'QR'
    NFC     = 'NFC'
    SKIP    = 'SKIP'
    ENTERED = 'ENTERED'




class DetailsSchema(BaseModel):
    answer: str = 'NA'
    answertype: AnswerType
    uuid: str
    jobneed_id: int
    parent_id: int
    seqno: int
    question_id: int
    options: str
    min: float
    max: float
    alerton: str
    ismandatory: bool = True
    alerts: bool = False


class ChildSchema(BaseModel):
    details: List[DetailsSchema]
    jobdesc: str
    qset_id: int
    seqno: int

    @validator('jobdesc', allow_reuse=True)
    def to_title_case(cls, v):
        if v: return v.title()


class ReportSchema(BaseModel):
    child: List[ChildSchema]
    asset_id: int
    bu_id: int
    cuser_id: int
    expirydatetime: datetime
    frequency: Frequency
    gpslocation: str
    gracetime: int
    pgroup_id:int
    identifier: JobIdentifier
    jobdesc: str
    job_id: int
    jobstatus: JobStatus
    jobtype: JobType
    muser_id: int
    othersite: str
    parent_id: int
    performedby_id: int
    plandatetime: datetime
    qset_id: int
    scantype: Scantype

    @validator('jobdesc', 'othersite', allow_reuse=True)
    def to_title_case(cls, v):  # sourcery skip: instance-method-first-arg-name
        if v: return v.title()

    @validator('gpslocation', allow_reuse=True)
    def check_gpslocation_format(cls, v):
        # sourcery skip: inline-immediately-returned-variable, instance-method-first-arg-name
        from django.contrib.gis.geos import GEOSGeometry
        try:
            lat, lng = v.split(', ')
            point = GEOSGeometry(f'SRID=4326;POINT({lng} {lat})')
            return point
        except Exception as e:
            raise ValueError('unrecognized gpslocation format') from e


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
    msg     = graphene.String()
    records = graphene.JSONString()


class UploadAttType(graphene.InputObjectType):
    # columns  = graphene.String()
    # values   = graphene.String()
    # image    = Upload()
    # path = graphene.String(required=False)
    # pelogid  = graphene.Int()
    # peopleid = graphene.Int()
    # filename = graphene.String()
    record = graphene.JSONString(required=True)
    tablname = graphene.String(required=True)
    file = Upload() 
