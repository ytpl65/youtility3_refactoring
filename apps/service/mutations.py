import graphene
from  graphql_jwt.shortcuts import get_token, get_payload
from graphql_jwt.decorators import login_required
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from apps.service import utils as sutils
from apps.core import utils as cutils
from apps.peoples.models import People
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FileUploadParser, JSONParser
from rest_framework.response import Response
from . import tasks
from . import types as ty
from graphene_file_upload.scalars import Upload

from logging import getLogger
import traceback as tb
log = getLogger('django')


class LoginUser(graphene.Mutation):
    """
    Authenticates user before log in
    """
    token   = graphene.String()
    user    = graphene.JSONString()
    payload = GenericScalar()
    msg     = graphene.String()
    shiftid = graphene.Int()

    class Arguments:
        input =  ty.AuthInput(required = True)

    @classmethod
    def mutate(cls, root, info, input):
        log.warning("login mutations start [+]")
        try:
            log.info("%s, %s, %s", input.deviceid, input.loginid, input.password)
            from .auth import auth_check
            output, user = auth_check(info, input, cls.returnUser)
            cls.updateDeviceId(user, input)
            log.warning("login mutations end [-]")
            return output
        except Exception as exc:
            log.error(exc, exc_info = True)
            raise GraphQLError(exc) from exc

    @classmethod
    def returnUser(cls, user, request):
        user.last_login = timezone.now()
        user.save()
        token = get_token(user)
        log.info(f"user logged in successfully! {user.peoplename}")
        user = cls.get_user_json(user)
        return LoginUser(token = token, user = user, payload = get_payload(token, request))

    @classmethod
    def updateDeviceId(cls, user, input):
        People.objects.update_deviceid(input.deviceid, user.id)

    @classmethod
    def get_user_json(cls, user):
        from django.db.models import F
        import json

        emergencycontacts = People.objects.get_emergencycontacts(user.bu_id, user.client_id)
        emergencyemails = People.objects.get_emergencyemails(user.bu_id, user.client_id)
        ic(emergencycontacts, emergencyemails)
        qset = People.objects.annotate(
            loggername          = F('peoplename'),
            mobilecapability    = F('people_extras__mobilecapability'),
            pvideolength        = F('client__bupreferences__pvideolength'),
            enablesleepingguard = F('client__enablesleepingguard'),
            skipsiteaudit       = F('client__skipsiteaudit'),
            deviceevent         = F('client__deviceevent'),
            isgpsenable         = F('client__gpsenable'),
            clientcode          = F('client__bucode'),
            clientname          = F('client__buname'),
            clientenable        = F('client__enable'),
            sitecode            = F('bu__bucode'),
            sitename            = F('bu__buname'),
            ).values(
                'loggername',  'mobilecapability',
                'enablesleepingguard',
                'skipsiteaudit', 'deviceevent', 'pvideolength',
                'client_id', 'bu_id', 'mobno', 'email', 'isverified',
                'deviceid', 'id', 'enable', 'isadmin', 'peoplecode',
                'tenant_id', 'loginid', 'clientcode', 'clientname', 'sitecode',
                'sitename', 'clientenable', 'isgpsenable').filter(id = user.id)
        qsetList = list(qset)
        ic(qsetList)
        qsetList[0].update({'emergencycontacts': list(emergencycontacts), 'emergencyemails':list(emergencyemails)})
        qsetList[0]['emergencyemails'] = str(qsetList[0]['emergencyemails']).replace('[', '').replace(']', '').replace("'", "")
        qsetList[0]['emergencycontacts'] = str(qsetList[0]['emergencycontacts']).replace('[', '').replace(']', '').replace("'", "")
        qsetList[0]['mobilecapability'] = str(qsetList[0]['mobilecapability']).replace('[', '').replace(']', '').replace("'", "")
        
        v = json.dumps(qsetList[0])
        ic(v)
        return v



class LogoutUser(graphene.Mutation):
    """
    Logs out user after resetting the deviceid 
    """
    status = graphene.Int(default_value = 404)
    msg    = graphene.String(default_value = "Failed")

    @classmethod
    @login_required
    def mutate(cls, root,info):

        updated = People.objects.reset_deviceid(info.context.user.id)
        if updated: 
            status, msg = 200, "Success"
            # log.info(f'user logged out successfully! {user.}')

        return LogoutUser(status = status, msg = msg)


class TaskTourUpdate(graphene.Mutation):
    """
    Update Task, Tour fields.
    like 'cdtz', 'mdtz', 'jobstatus', 'performedby' etc
    """
    output = graphene.Field(ty.ServiceOutputType)
    class Arguments:
        file = Upload()

    @classmethod
    def mutate(cls, root, info, file):
        log.warning("tasktour-update mutations start [+]")
        o = sutils.perform_tasktourupdate(file, info.context)
        log.info(f"Response: # records updated:{o.recordcount}, msg:{o.msg}, rc:{o.rc}, traceback:{o.traceback}")
        log.warning("tasktour-update mutations end [-]")
        return TaskTourUpdate(output = o)

class InsertRecord(graphene.Mutation):
    """
    Inserts new record in the specified table.
    """
    output = graphene.Field(ty.ServiceOutputType)

    class Arguments:
        file = Upload(required = True)

    @classmethod    
    def mutate(cls, root, info, file):
        log.warning("insert-record mutations start [+]")
        o = sutils.perform_insertrecord(file, info.context)
        log.info(f"Response: # records updated:{o.recordcount}, msg:{o.msg}, rc:{o.rc}, traceback:{o.traceback}")
        log.warning("insert-record mutations end [-]")
        return InsertRecord(output = o)


class ReportMutation(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)
    # msg = graphene.String()
    # ic(output)
    class Arguments:
        file = Upload(required = True)

    @classmethod
    def mutate(cls, root, info, file):
        log.warning("report mutations start [+]")
        o = sutils.perform_reportmutation(file)
        log.info(f"Response: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback}")
        log.warning("report mutations end [-]")
        return ReportMutation(output = o)

class UploadAttMutaion(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)

    class Arguments:
        record = graphene.JSONString(required = True)
        file = Upload(required = True) 
        biodata = graphene.JSONString(required = True)

    @classmethod
    def mutate(cls,root, info, file,  record, biodata):
        import zipfile
        try:
            with zipfile.ZipFile(file, 'r') as zip_ref:
                for file in zip_ref:
                    o = sutils.perform_uploadattachment( file, record, biodata)
                    log.info(f"Response: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback}")
                    return UploadAttMutaion(output = o)
        except Exception as e:
            return UploadAttMutaion(output = ty.ServiceOutputType(rc = 1, recordcount = 0, msg = 'Upload Failed', traceback = tb.format_exc()))


class UploadFile(APIView):
    parser_classes = [MultiPartParser, FileUploadParser, JSONParser]
    
    def post(self, request, format=None):
        file    = request.data['file']
        biodata = request.data['biodata']
        record  = request.data['record']
        ic(file, biodata, record)
        ic(type(file), type(biodata), type(record))
        output = sutils.perform_uploadattachment(file, record, biodata)
        return Response(data={'rc':output.rc, 'msg':output.msg, 
            'recordcount':output.recordcount, 'traceback':output.traceback})
        
        
        



class AdhocMutation(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)
    class Arguments:
        file = Upload(required = True)

    @classmethod
    def mutate(cls, root, info, file):
        o = sutils.perform_adhocmutation(file)
        log.info(f"Response: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback}")
        return AdhocMutation(output = o)


class InsertJsonMutation(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)

    class Arguments:
        jsondata = graphene.List(graphene.String,required = True)
        tablename = graphene.String(required = True)

    @classmethod
    def mutate(cls, root, info, jsondata, tablename):
        # sourcery skip: instance-method-first-arg-name
        from .tasks import insertrecord_json
        from apps.core.utils import get_current_db_name
        import json
        log.info('insert jsondata mutations start[+]')
        rc, traceback, resp, recordcount = 0,  'NA', 0, 0
        msg = ""
        try:
            db = get_current_db_name()
            log.info(f'=================== jsondata:============= \n{jsondata}')
            uuids = insertrecord_json(jsondata, tablename)
            recordcount, msg = 1, 'Inserted Successfully'
        except Exception as e:
            log.error('something went wrong', exc_info = True)
            msg, rc, traceback = 'Insert Failed!',1, tb.format_exc()
        o = ty.ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback, uuids=uuids)
        log.info(f"Response: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback}")
        return InsertJsonMutation(output = o)



class SyncMutation(graphene.Mutation):
    rc = graphene.Int()

    class Arguments:
        file         = Upload(required = True)
        filesize     = graphene.Int(required = True)
        totalrecords = graphene.Int(required = True)

    @classmethod
    def mutate(cls, root, info, file, filesize, totalrecords):
        from apps.core.utils import get_current_db_name
        log.info("sync now mutation is running")
        import zipfile
        from apps.service import tasks
        try:
            db = get_current_db_name()
            log.info(f'the type of file is {type(file)}')
            with zipfile.ZipFile(file) as zip:
                zipsize = TR = 0
                for file in zip.filelist:
                    zipsize += file.file_size
                    log.info(f'filename: {file.filename} and size: {file.file_size}')
                    with zip.open(file) as f:
                        data = tasks.get_json_data(f)
                        # raise ValueError
                        TR += len(data)
                        tasks.call_service_based_on_filename(data, file.filename, db = db)
                        ic(data)
                if filesize !=  zipsize:
                    log.error(f"file size is not matched with the actual zipfile {filesize} x {zipsize}")
                    raise cutils.FileSizeMisMatchError
                if TR !=  totalrecords:
                    log.error(f"totalrecords is not matched with th actual totalrecords after extraction... {totalrecords} x {TR}")
                    raise cutils.TotalRecordsMisMatchError
        except Exception:
            log.error("something went wrong!", exc_info = True)
            return SyncMutation(rc = 1)
        else:
            return SyncMutation(rc = 0)


