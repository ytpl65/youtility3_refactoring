from cv2 import trace
import graphene
from  graphql_jwt.shortcuts import get_token, get_payload
from graphql_jwt.decorators import login_required
from graphene.types.generic import GenericScalar
from graphql import GraphQLError
from numpy import rec
from apps.service import utils as sutils
from apps.core import utils as cutils
from django.utils import timezone
from . import tasks

from apps.peoples.models import People
from . import types as ty
from graphene_file_upload.scalars import Upload


from logging import getLogger
import traceback as tb
log = getLogger('__main__')













########################### BEGIN GLOBAL INSERT RECORD ##############################

########################### END GLOBAL INSERT RECORD ##############################






# class InsertRecord(graphene.Mutation):
#     """
#     Inserts new record in the specified table.
#     """
#     output = graphene.Field(ty.ServiceOutputType)
#     class Arguments:
#         input = ty.RowInput(required = True)


#     @classmethod
#     @login_required
#     def mutate(cls, root, info, input):
#         log.info(f"{Messages.START} insertRecord --")
#         log.debug(f'input.columns {input.columns}')
#         log.debug(f'input.values {input.values}')
#         log.debug(f'input.tablename {input.tablename}')

#         model, Form  = get_model_or_form(input.tablename.lower())

#         if not model or len(input.columns) != len(input.values):
#             raise GraphQLError(Messages.IMPROPER_DATA)
#         try:
#             if instance := cls.create_record(model, Form, input):
#                 msg = Messages.INSERT_SUCCESS
#                 output = ty.ServiceOutputType(msg = msg, returnid = instance.id)
#                 log.info(f"{pformat(output)}")
#                 log.info(f'{Messages.END} insert record ++')
#                 return InsertRecord(output=output)

#         except IntegrityError as e:
#             log.error(e, exc_info=True)
#             output = ty.ServiceOutputType(
#                 msg = Messages.
#             )

#         except Exception as e:
#             log.error(e, exc_info=True)
#             raise Exception(f'{Messages.INSERT_FAILED} {e}') from e


#     @classmethod
#     def create_record(cls, model, F, input):
#         """
#         Insert record in specified table
#         """
#         record = utils.get_record_from_input(input)
#         log.info(f"record: {pformat(record)}")
#         record = clean_record(record)

#         with transaction.atomic(using=utils.get_current_db_name()):
#             log.info(f'record after cleaning {pformat(record)}')
#             return model.objects.create(**record)



# class UpdateRecord(graphene.Mutation):
#     """
#     Updates the existing record 'id' field is must
#     in ty.RowInput.
#     """
#     output = graphene.Field(RowOutput)
#     class Arguments:
#         input = ty.RowInput(required=True)

#     @login_required
#     @classmethod
#     def mutate(cls, root, info, input):
#         model, Form  = get_model_or_form(input.tablename.lower())
#         ic(len(input.columns) != len(input.values))
#         ic(model)
#         if not model or len(input.columns) != len(input.values):
#             raise GraphQLError(Messages.IMPROPER_DATA)
#         try:
#             if instance := cls.update_record(model, Form, input):
#                 msg = Messages.INSERT_SUCCESS
#                 output = RowOutput(msg = msg, id = instance.id)
#                 return UpdateRecord(output=output)
#         except IntegrityError as e:
#             log.error(e, exc_info=True)
#             raise Exception(f'{Messages.DBERROR} {e}') from e
#         except Exception as e:
#             log.error(e, exc_info=True)
#             raise Exception(f'{Messages.UPDATE_FAILED} {e}') from e


#     @classmethod
#     def update_record(cls, model, F, input):
#         """
#         Update record from the table
#         """
#         record = utils.get_record_from_input(input)
#         form = F(data = record)
#         with transaction.atomic(using=utils.get_current_db_name()):
#             if form.is_valid():
#                 ic(form.data)
#                 model.objects.filter(
#                     id = record['id']).update(**form.data)
#                 return model.objects.get(id=record['id'])


######################### START PEOPLEEVENTLOG MUTATION #########################
# class PELogMutation(DjangoModelFormMutation, BaseReturnType):
#     output = graphene.Field(PELogType)

#     class Meta:
#         form_class = InsertPeopleEventlog
#         return_field_name = 'output'

#     @classmethod
#     def perform_mutate(cls, form, info):
#         obj = form.save(commit=True)
#         obj.cdtz = form.data['cdtz']
#         obj.mdtz = form.data['mdtz']
#         obj.save()
#         kwargs = {
#             'output':obj, 'user':info.context.user
#             }
#         return cls(errors=[], **kwargs)
######################### END PEOPLEEVENTLOG MUTATION #########################



######################### START TRACKING MUTATION #########################
# class TrackingMutation(DjangoModelFormMutation):
#     TrackingType = graphene.Field(TrackingType)

#     class Meta:
#         model             = Tracking
#         form_class        = TrackingForm
#         return_field_name = 'output'
######################### END TRACKING MUTATION #########################


######################### START TYPEASSIST MUTATION #########################
# class AddTaMutation(DjangoModelFormMutation):
#     input = graphene.Field(TyType)

#     class Meta:
#         form_class=TypeAssistForm
#         return_field_name = 'output'

#     @classmethod
#     def perform_mutate(cls, form, info):
#         obj = form.save()
#         kwargs = {cls._meta.return_field_name: obj, 'typeassist':obj}
#         return cls(errors=[], **kwargs)
######################### END TYPEASSIST MUTATION #########################


######################### START AUTHENTICATION #########################


# class TaskTourUpdate(graphene.Mutation):
#     """
#     Update Task, Tour fields.
#     like 'cdtz', 'mdtz', 'jobstatus', 'performedby' etc
#     """
#     output = graphene.Field(RowOutput)
#     class Arguments:
#         input = TaskTourUpdateInput(required=True)

#     @classmethod
#     @login_required
#     def mutate(cls, root, info, input):
#         from apps.activity.models import Jobneed, JobneedDetails
#         if len(input.columns) != len(input.values):
#             raise GraphQLError(Messages.IMPROPER_DATA)
#         try:
#             if updated:= cls.update_record(input, Jobneed, JobneedDetails):
#                 msg = Messages.UPDATE_SUCCESS
#                 output = RowOutput(msg=msg, id = input.jobneedid)
#                 return TaskTourUpdate(output=output)

#         except IntegrityError as e:
#             log.error(e, exc_info=True)
#             raise Exception(f'{Messages.DBERROR} {e}') from e

#         except Exception as e:
#             log.error(e, exc_info=True)
#             raise Exception(f'{Messages.UPDATE_FAILED} {e}') from e

#     @classmethod    
#     def update_record(cls, input, Jn, Jnd):
#         alerttype = 'OBSERVATION'
#         record = utils.get_record_from_input(input)
#         record = clean_record(record)
#         with transaction.atomic(using=utils.get_current_db_name()):
#             isJnUpdated = Jn.objects.filter(
#                 id = input.jobneedid).update(**record)
#             isJndUpdated = cls.update_jobneeddetails(input, Jnd)
#             if isJnUpdated and  isJndUpdated:
#                 utils.alert_email(input.jobneedid, alerttype)
#                 #TODO send observation email
#                 #TODO send deviation mail
#                 return True



#     @classmethod
#     def update_jobneeddetails(cls, input, Jnd):
#         if input.jobneeddetails:
#             updated=0
#             for detail in input.jobneeddetails:
#                 detail = eval(detail)
#                 record = clean_record(detail)
#                 updated = Jnd.objects.filter(id = detail['id']).update(**record)
#             if len(input.jobneeddetails) == updated: return True


# def perform_template_report_mutation(input, model):
#     parent = insert_parent(input, model)
#     insert_child_and_details(input, model, parent)
#     return parent


# class TemplateReport(graphene.Mutation):
#     output = graphene.Field(RowOutput)

#     class Arguments:
#         input = TemplateReportInput(required=True)

#     @classmethod
#     @login_required
#     def mutate(cls, root, info, input):
#         from apps.activity.models import Jobneed

#         if input.childs and len(input.childs)>0:
#             try:
#                 with transaction.atomic(using=utils.get_current_db_name()):
#                     parent = perform_template_report_mutation(input, Jobneed)
#                     #TODO send email for report
#                     output = RowOutput(id = parent.id, msg = Messages.INSERT_SUCCESS)
#                     return TemplateReport(output=output)
#             except Exception as e:
#                 log.error(e, exc_info=True)
#                 raise Exception(f'{Messages.INSERT_FAILED} << {e} >>') from e
#         else:
#             return TemplateReport(output=RowOutput(id = None, msg = Messages.NOT_INTIATED ))


# def insert_parent(input, model):
#     print(pformat(input, compact=True))
#     record = utils.get_record_from_input(input)
#     ic('parent record', record)
#     try:
#         if len(input.childs) > 0:
#             record.pop('qset_id', None)
#             return model.objects.create(qset_id = input.questionsetid, **record)
#         else: raise Exception(Messages.NODETAILS)
#     except Exception:
#         raise

# def insert_child_and_details(input, model, parent):
#     import json
#     from apps.activity.models import JobneedDetails
#     try:
#         childs = input.childs
#         ic(childs)
#         for child in childs:
#             details = child.pop('details')
#             ic(child)
#             child = eval(child)
#             child = clean_record(child)
#             ic("record jobneed ", child)
#             details = clean_record(details)
#             ic("record details", details)
#             child = model.objects.create(
#                 parent_id = parent.id, **child  
#             )
#             for detail in details:
#                 JobneedDetails.objects.create(
#                     jobneed_id = child.id, **detail)
#     except Exception:
#         raise


# class UploadAttachment(graphene.Mutation):
#     """
#     Upload attachment.
#     """
#     output = graphene.Field(RowOutput)

#     class Arguments:
#         input = graphene.Field(AttachmentInput)

#     @login_required
#     @classmethod
#     def mutate(cls, root, info, input):  
#         try:
#             with transaction.atomic(using=utils.get_current_db_name()):
#                 files = cls.write_file_to_dir(input)
#                 cls.perform_query(input, files[1])
#         except Exception as e:
#             log.error(e, exc_info=True)
#             raise Exception(f'{Messages.UPLOAD_FAILED} {e}') from e

#     @classmethod
#     def perform_query(cls, input, files):
#         from apps.attendance.models import PeopleEventlog
#         #TODO perform query coming from mobile
#         if people_att := PeopleEventlog.objects.get(id = input.pelogid):
#             from apps.onboarding.models import TypeAssist
#             from apps.activity.models import Attachment

#             attachmentid   = cls.execute_query(cls, input)
#             ownertype      = TypeAssist.objects.get(tatype__tacode = 'OWNER', tacode='PEOPLE')
#             attachmenttype = TypeAssist.objects.get(tacode ='ATTACHMENT')
#             if people_pic := Attachment.objects.get_people_pic(
#                 ownertype.id, attachmenttype.id, people_att.id):
#                 people_pic.default_image_path = f'{files[0]}{people_pic.default_image_path}'
#                 try:
#                     fr_results = utils.fr(people_pic.default_image_path, files[1])
#                     PeopleEventlog.objects.filter(id = input.pelogid).update(
#                         peventlogextras__fr_threshold = fr_results[2],
#                         peventlogextras__face_recognition = fr_results[1],
#                         peventlogextras__serverresponse = fr_results[0]
#                     )
#                 except Exception:
#                     log.error("ERROR Failed to recognize face ", exc_info=True)
#         else:
#             raise Exception(Messages.NOTFOUND)



# def process_adhoc_mutation(input):
#     try:
#         if input.assetid == 1:
#             bu_data = Bt.objects.filter(id = input.buid, bucode = input.remarks)[0]
#             input.siteid = bu_data.id
#         schedule_task = Jobneed.objects.get_schedule_for_adhoc(
#             input.plandatetime, input.buid, input.peopleid, input.assetid, input.qsetid)
#         if len(schedule_task) > 0:
#             jnid = schedule_task[0].jobneedid
#             record = utils.get_record_from_input(input)
#             record.update({'people_id':input.people_id})
#             record = clean_record(record)
#             Jobneed.objects.filter(id = jnid).update(**record)
#             schedule_task_details = JobneedDetails.objects.select_related('jobneed', 'job' 'question').filter(jobneed_id = jnid).values()
#             for jnd, dtl in itertools.product(schedule_task_details, input.jobneeddetails):
#                 dtl = clean_record(eval(dtl))
#                 if jnd['question_id'] == dtl['question_id']:
#                     JobneedDetails.objects.update_ans_muser(dtl['answer'], input.people_id, dtl['mdtz'], jnid)
#         else:
#             record = utils.get_record_from_input(input)
#             record.update({'qset_id':input.qset_id, 'jobdesc':input.jobdesc})
#             record = clean_record(record)
#             jnid = Jobneed.objects.create(**record)
#             for dtl in input.jobneeddetails:
#                 dtl = clean_record(eval(dtl))

#     except Exception as e:
#         raise



# class Adhoc(graphene.Mutation):
#     """
#     Adhoc task/tours are inserted
#     """
#     output = graphene.Field(RowOutput)

#     class Arguments:
#         input = AdhocInputType(required=True)

#     @classmethod
#     def mutate(cls, root, info, input):
#         try:
#             with transaction.atomic(using=utils.get_current_db_name()):
#                 process_adhoc_mutation(input)
#         except Exception as e:
#             raise Exception(f'{Messages.ADHOCFAILED} {e}') from e


# class TestJsonMutation(graphene.Mutation):
#     """
#     test
#     """
#     output = graphene.Field(RowOutput)

#     class Arguments:
#         file = Upload(required=True)

#     @classmethod
#     def mutate(cls, root, info, file):
#         try:
#             import codecs
#             import json
#             import gzip
#             ic(file, type(file), file.size)
#             reader = codecs.getreader("utf-8")
#             with gzip.open(file, 'rb') as f: 
#                 # list all the contents of the zip file
#                 ic(json.loads(f.read().decode('utf-8')) , file.size)
#             return TestJsonMutation(output = RowOutput(msg = "Json data red successfully",  id=None))
#         except Exception as e:
#             raise GraphQLError(e) from e


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
        input =  ty.AuthInput(required=True)

    @classmethod
    def mutate(cls, root, info, input):
        log.warn("login mutations start [+]")
        try:
            from .auth import auth_check
            output, user = auth_check(info, input, cls.returnUser)
            cls.updateDeviceId(user, input)
            log.warn("login mutations end [-]")
            return output
        except Exception as exc:
            log.error(exc, exc_info=True)
            raise GraphQLError(exc) from exc


    @classmethod
    def returnUser(cls, user, request):
        user.last_login = timezone.now()
        user.save()
        token = get_token(user)
        log.info(f"user logged in successfully! {user.peoplename}")
        user = cls.get_user_json(user)
        return LoginUser(token=token, user=user, payload = get_payload(token, request))


    @classmethod
    def updateDeviceId(cls, user, input):
        People.objects.update_deviceid(input.deviceid, user.id)


    @classmethod
    def get_user_json(cls, user):
        from django.db.models import F
        import json

        emergencycontacts = People.objects.get_emergencycontacts(user.bu_id, user.client_id)
        emergencyemails = People.objects.get_emergencyemails(user.bu_id, user.client_id)

        qset = People.objects.annotate(
            loggername          = F('peoplename'),
            mobilecapability    = F('people_extras__mobilecapability'),
            pvideolength        = F('bu__bupreferences__pvideolength'),
            enablesleepingguard = F('bu__enablesleepingguard'),
            skipsiteaudit       = F('bu__skipsiteaudit'),
            deviceevent         = F('bu__deviceevent'),
            isgpsenable         = F('bu__gpsenable'),
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
            'sitename', 'clientenable', 'isgpsenable').get(id=user.id)
        qset.update({'emergencycontacts': list(emergencycontacts), 'emergencyemails':list(emergencyemails)})
        return  json.dumps(qset)




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
            #log.info(f'user logged out successfully! {user.}')

        return LogoutUser(status=status, msg=msg)



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
        log.warn("tasktour-update mutations start [+]")
        o = sutils.perform_tasktourupdate(file, info.context)
        log.info(f"Response: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback}")
        log.warn("tasktour-update mutations end [-]")
        return TaskTourUpdate(output=o)


class InsertRecord(graphene.Mutation):
    """
    Inserts new record in the specified table.
    """
    output = graphene.Field(ty.ServiceOutputType)

    class Arguments:
        file = Upload(required=True)

    @classmethod    
    def mutate(cls, root, info, file):
        log.warn("insert-record mutations start [+]")
        ic(file, type(file))
        o = sutils.perform_insertrecord(file, info.context)
        log.warn("insert-record mutations end [-]")
        return InsertRecord(output = o)



class ReportMutation(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)
    #msg = graphene.String()
    #ic(output)
    class Arguments:
        file = Upload(required=True)


    @classmethod
    def mutate(cls, root, info, file):
        log.warn("report mutations start [+]")
        o = sutils.perform_reportmutation(file)
        log.info(f"Response: {o.recordcount}, {o.msg}, {o.rc}, {o.traceback}")
        log.warn("report mutations end [-]")
        return ReportMutation(output = o)


class UploadAttMutaion(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)

    class Arguments:
        record = graphene.JSONString(required=True)
        file = Upload(required=True) 
        biodata = graphene.JSONString(required=True)

    @classmethod
    def mutate(cls,root, info, file,  record, biodata):
        output = sutils.perform_uploadattachment( file, record, biodata)
        return UploadAttMutaion(output = output)



class AdhocMutation(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)
    class Arguments:
        file = Upload(required=True)

    @classmethod
    def mutate(cls, root, info, file):
        output = sutils.perform_adhocmutation(file)
        return AdhocMutation(output=output)



class InsertJsonMutation(graphene.Mutation):
    output = graphene.Field(ty.ServiceOutputType)

    class Arguments:
        jsondata = graphene.JSONString(required=True)
        tablename = graphene.String(required=True)

    @classmethod
    def mutate(cls, root, info, jsondata, tablename):
        # sourcery skip: instance-method-first-arg-name
        from .tasks import insertrecord_from_tablename
        from apps.core.utils import get_current_db_name
        import json
        log.info('insert jsondata mutations start[+]')
        rc, traceback, resp, recordcount = 0,  'NA', 0, 0
        msg = ""
        try:
            db = get_current_db_name()
            insertrecord_from_tablename(jsondata, tablename, db)
            recordcount, msg = 1, 'Inserted Successfully'
        except Exception as e:
            log.error('something went wrong', exc_info=True)
            msg, rc, traceback = 'Insert Failed!',1, tb.format_exc()
        output = ty.ServiceOutputType(rc=rc, recordcount = recordcount, msg = msg, traceback = traceback)
        return InsertJsonMutation(output=output)




class SyncMutation(graphene.Mutation):
    rc = graphene.Int()


    class Arguments:
        file         = Upload(required=True)
        filesize     = graphene.Int(required=True)
        totalrecords = graphene.Int(required=True)

    @classmethod
    def mutate(cls, root, info, file, filesize, totalrecords):
        from apps.core.utils import get_current_db_name
        log.info("sync now mutation is running")
        import zipfile
        from apps.service import tasks
        try:
            db = get_current_db_name()
            with zipfile.ZipFile(file) as zip:
                zipsize = TR = 0
                for file in zip.filelist:
                    zipsize+=file.file_size
                    log.info(f'filename: {file.filename} and size: {file.file_size}')
                    with zip.open(file) as f:
                        data = tasks.get_json_data(f)
                        #raise ValueError
                        TR+=len(data)
                        tasks.call_service_based_on_filename(data, file.filename, db=db)
                        ic(data)
                if filesize!=zipsize:
                    log.error(f"file size is not matched with the actual zipfile {filesize} x {zipsize}")
                    raise cutils.FileSizeMisMatchError
                if TR!=totalrecords:
                    log.error(f"totalrecords is not matched with th actual totalrecords after extraction... {totalrecords} x {TR}")
                    raise cutils.TotalRecordsMisMatchError
        except Exception:
            log.error("something went wrong!", exc_info=True)
            return SyncMutation(rc=1)
        else:
            return SyncMutation(rc=0)























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
