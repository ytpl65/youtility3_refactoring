from graphql import GraphQLError
from apps.service import serializers as sz
from apps.attendance.models import PeopleEventlog
from apps.activity.models import (Jobneed, JobneedDetails, Attachment, Asset)
from django.db.utils import IntegrityError
from django.db import transaction
from .auth import Messages as AM
from .types import ServiceOutputType
from logging import getLogger
import traceback as tb
from .validators import clean_record
from pprint import pformat
from apps.core import utils
from intelliwiz_config.celery import app
from celery.utils.log import get_task_logger
log = get_task_logger(__name__)

def get_model_or_form(tablename):
    match tablename:
        case "peopleeventlog":
            return PeopleEventlog
        case 'jobneed':
            return  Jobneed
        case 'attachment':
            return  Attachment
        case 'jobneeddetails':
            return  JobneedDetails
        case _:
            return None


def get_or_create_dir(path):
    try:
        import os
        created=True
        if not os.path.exists(path):
            os.makedirs(path)
        else: created= False
        return created
    except Exception:
        raise


def write_file_to_dir(filebuffer, uploadedfile):
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    
    try:
        path = default_storage.save(uploadedfile, ContentFile(filebuffer.read()))
    except Exception:
        raise




class Messages(AM):
    INSERT_SUCCESS  = "Inserted Successfully!"
    UPDATE_SUCCESS  = "Updated Successfully!"
    IMPROPER_DATA   = "Failed to insert incorrect tablname or size of columns and rows doesn't match",
    WRONG_OPERATION = "Wrong operation 'id' is passed during insertion!"
    DBERROR         = "Integrity Error!"
    INSERT_FAILED   = "Failed to insert something went wrong!"
    UPDATE_FAILED   = "Failed to Update something went wrong!"
    NOT_INTIATED    = "Insert cannot be initated not provided necessary data"
    UPLOAD_FAILED   = "Upload Failed!"
    NOTFOUND        = "Unable to find people with this pelogid"
    START           = "Mutation start"
    END             = "Mutation end"
    ADHOCFAILED     = 'Adhoc service failed'
    NODETAILS       = ' Unable to find any details record against site/incident report'
    REPORTSFAILED   = 'Failed to generate jasper reports'
    UPLOAD_SUCCESS  = 'Uploaded Successfully!'



def insertrecord_for_att(record, tablename, db):
    try:
        if model := get_model_or_form(tablename):
            record = clean_record(record)
            obj = model.objects.create(**record)
            return obj.id
        raise GraphQLError(Messages.IMPROPER_DATA)
    except Exception as e:
        raise e


# @app.task(bind=True, default_retry_delay=300, max_retries=5)
# def substract(x, y):
#     try:
#         return x-y
#     except Exception as e:
#         self.retry(e)

def call_service_based_on_filename(data, filename, db='default'):
    ic("moment", data)
    ic("moment", filename)
    ic("moment", db)
    match filename:
        case 'insertRecord.gz':
            log.info("calling insertrecord.gz")
            return perform_insertrecord_bgt.delay(data, db=db)
        case 'updateTaskTour.gz':
            log.info("calling updateTaskTour.gz")
            return perform_tasktourupdate_bgt.delay(data, db=db)
        case 'uploadReport.gz':
            log.info("calling uploadReport.gz")
            return perform_reportmutation_bgt.delay(data, db=db)
        case 'adhocRecord.gz':
            log.info("calling adhocRecord.gz")
            return perform_adhocmutation_bgt.delay(data, db=db)
        




def perform_uploadattachment(file, tablename, record, biodata):
    rc, traceback, resp = 0,  'NA', 0
    recordcount = msg=None
    #ic(file, tablename, record, type(record), biodata, type(biodata))
    try:
        import os
        
        file_buffer = file
        #ic(file_buffer, type(file_buffer))
        filename = biodata['filename']
        pelogid = biodata['pelog_id']
        peopleid = biodata['people_id']
        path = biodata['path']
        home_dir = os.path.expanduser('~') + '/'
        filepath = home_dir + path
        uploadfile = f'{filepath}/{filename}'
        db = utils.get_current_db_name()
        with transaction.atomic(using=db):
            iscreated = get_or_create_dir(filepath)
            log.info(f'filepath is {iscreated}')
            write_file_to_dir(file_buffer, uploadfile)
            resp = insertrecord_for_att(record, tablename, db)
            rc, traceback, msg = 0, tb.format_exc(), Messages.UPLOAD_SUCCESS
            recordcount = 1
        from apps.activity.tasks import perform_facerecognition
        results = perform_facerecognition.delay(pelogid, peopleid, resp, home_dir, uploadfile, db)
        log.warn(f"face recognition status {results.state}")
    except Exception as e:
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
        log.error('something went wrong', exc_info=True)
    return ServiceOutputType(rc=rc, recordcount = recordcount, msg = msg, traceback = traceback)



@app.task(bind=True, default_retry_delay=300, max_retries=5)
def perform_insertrecord_bgt(self, data, request=None, filebased=True, db='default'):
    """
    Insert records in specified tablename.

    Args:
        file (file|json): file object| json data
        tablename (str): name of table
        request (http wsgi request, optional): request object. Defaults to None.
        filebased (bool, optional): type of data, file (True) or json (False) Defaults to True.

    Returns:
        ServiceOutputType: rc, recordcount, msg, traceback
    """
    log.info('perform_insertrecord [start]')
    log.info('perform_insertrecord [data]', data)
    log.info('perform_insertrecord [db]', db)
    
    rc, recordcount, traceback= 0, 0, 'NA'
    instance = None
    try:
        try:
            with transaction.atomic(using=db):
                utils.set_db_for_router(db)
                for record in data:
                    tablename = record.pop('tablename')
                    model = get_model_or_form(tablename)
                    record = clean_record(record)
                    log.info(f'record after cleaning {pformat(record)}')
                    instance = model.objects.create(**record)
                    recordcount+=1
        except Exception:
            raise
        if recordcount:
            msg = Messages.INSERT_SUCCESS
    except Exception as e:
        log.error("something went wrong!", exc_info=True)
        msg, rc, traceback = Messages.INSERT_FAILED, 1, tb.format_exc()
    return  ServiceOutputType(rc=rc, recordcount = recordcount, msg = msg, traceback = traceback)


def get_json_data(file):
    import gzip
    import json
    try:
        #ic((file, type(file))
        with gzip.open(file, 'rb') as f:
            s = f.read().decode('utf-8')
            s = s.replace("'", "")
            return json.loads(s)
    except Exception as e:
        log.error("File unzipping error", exc_info=True)
    return None, None


def print_json_data(file):
    import gzip
    import json
    try:
        with gzip.open(file, 'rb') as f:
            s = f.read().decode('utf-8')
            s = s.replace("'", "")
            ic(json.loads(s))
    except Exception as e:
        log.error("json print error", exc_info= True)


def update_record(details, jobneed, Jn, Jnd, db):
    alerttype = 'OBSERVATION'
    record = clean_record(jobneed)
    #ic((record)
    try:
        with transaction.atomic(using=db):
            instance = Jn.objects.get(uuid = record['uuid'])
            jn_parent_serializer = sz.JobneedSerializer(data=record, instance=instance)
            if jn_parent_serializer.is_valid():
                isJnUpdated = jn_parent_serializer.save()
            else: log.error(f"something went wrong!\n{jn_parent_serializer.errors} ", exc_info=True )
            isJndUpdated = update_jobneeddetails(details, Jnd, db)
            if isJnUpdated and  isJndUpdated:
                #utils.alert_email(input.jobneedid, alerttype)
                #TODO send observation email
                #TODO send deviation mail
                return True
    except Exception:
        raise


def update_jobneeddetails(jobneeddetails, Jnd, db):
    if jobneeddetails:
        updated=0
        for detail in jobneeddetails:
            record = clean_record(detail)
            instance = Jnd.objects.get(uuid = record['uuid'])
            jnd_ser = sz.JndSerializers(data=record, instance=instance)
            if jnd_ser.is_valid():
                jnd = jnd_ser.save()
            updated+=1
        if len(jobneeddetails) == updated: return True 



@app.task(bind=True, default_retry_delay=300, max_retries=5)
def perform_tasktourupdate_bgt(self, data, request, db='default'):
    log.info("perform_tasktourupdate [start]")
    rc, recordcount, traceback= 0, 0, 'NA'
    instance, msg = None, ""

    try:
        #ic((data)
        for record in data:
            details = record.pop('details')
            jobneed = record
            with transaction.atomic(using=db):
                utils.set_db_for_router(db)
                if updated :=  update_record(details, jobneed, Jobneed, JobneedDetails, db):
                    recordcount+=1
    
    except IntegrityError as e:
        log.error("Database Error", exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    
    except Exception as e:
        log.error('Something went wrong', exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    return ServiceOutputType(rc=rc, msg=msg, recordcount=recordcount, traceback=traceback)



@app.task(bind=True, default_retry_delay=300, max_retries=5)
def perform_reportmutation_bgt(self, data, db='default'):
    rc, recordcount, traceback= 0, 0, 'NA'
    instance = None
    try:
        if data:
            for record in data:
                child = record.pop('child', None)
                parent = record
                try:
                    with transaction.atomic(using=db):
                        utils.set_db_for_router(db)
                        if child and len(child) > 0 and parent:
                            jobneed_parent_post_data = parent
                            jn_parent_serializer = sz.JobneedSerializer(data=clean_record(jobneed_parent_post_data))
                            rc,  traceback, msg = save_parent_childs(sz, jn_parent_serializer, child, Messages, db)
                            if rc == 0: recordcount+=1
                        else:
                            log.error(Messages.NODETAILS)
                            msg, rc = Messages.NODETAILS, 1
                except Exception as e:
                    log.error('something went wrong', exc_info=True)
                    raise
    except Exception as e:
        msg, traceback, rc = Messages.INSERT_FAILED, tb.format_exc(), 1
        log.error('something went wrong', exc_info=True)
    return ServiceOutputType(rc=rc, recordcount = recordcount, msg = msg, traceback = traceback)



def save_parent_childs(sz, jn_parent_serializer, child, M, db):
    log.info("save_parent_childs ............start")
    try:
        rc,  traceback= 0,  'NA'
        instance = None
        if jn_parent_serializer.is_valid():
            parent = jn_parent_serializer.save()
            allsaved=0
            for ch in child:
                #ic((ch, type(child))
                details = ch.pop('details')
                #ic((details, type(details))
                ch.update({'parent_id':parent.id})
                child_serializer = sz.JobneedSerializer(data=clean_record(ch))
                
                if child_serializer.is_valid():
                    child_instance = child_serializer.save()
                    for dtl in details:
                        #ic((dtl, type(dtl))
                        dtl.update({'jobneed_id':child_instance.id})
                        ch_detail_serializer = sz.JndSerializers(data=clean_record(dtl))
                        if ch_detail_serializer.is_valid():
                            ch_dtl = ch_detail_serializer.save()
                        else:
                            log.error(ch_detail_serializer.errors)
                            traceback, msg, rc = str(ch_detail_serializer.errors), M.INSERT_FAILED, 1
                    allsaved+=1
                else:
                    log.error(child_serializer.errors)
                    traceback, msg, rc = str(child_serializer.errors), M.INSERT_FAILED, 1
            if allsaved == len(child):
                msg= M.INSERT_SUCCESS
        else:
            log.error(jn_parent_serializer.errors)
            traceback, msg, rc = str(jn_parent_serializer.errors), M.INSERT_FAILED, 1
        log.info("save_parent_childs ............end")
        return rc, traceback, msg
    except Exception:
        log.error("something went wrong",exc_info=True)
        raise


@app.task(bind=True, default_retry_delay=300, max_retries=5)
def perform_facerecognition_bgt(self, pelogid, peopleid, ownerid, home_dir, uploadfile, db='default'):
    from apps.activity.models import Attachment
    from apps.attendance.models import PeopleEventlog
    from django.db import transaction
    from apps.core import utils
    
    log.info("perform_facerecognition ...start [+]")
    log.info(f'parameters are {pelogid} {peopleid} {ownerid} {type(ownerid)} {home_dir} {uploadfile}')
    try:
        with transaction.atomic(using=utils.get_current_db_name()):
            if pelogid!=1:
                if ATT := Attachment.objects.get_attachment_record(ownerid, db):
                    if PEOPLE_ATT := PeopleEventlog.objects.get_people_attachment(pelogid, db):
                        if PEOPLE_PIC := Attachment.objects.get_people_pic(ATT.ownername_id, PEOPLE_ATT.uuid, db):
                            default_image_path = PEOPLE_PIC.default_img_path
                            default_image_path = home_dir + default_image_path
                            from deepface import DeepFace
                            fr_results = DeepFace.verify(img1_path = default_image_path, img2_path = uploadfile)
                            PeopleEventlog.objects.update_fr_results(fr_results, pelogid, peopleid, db)
    except ValueError as v:
        log.error("face recogntion failed", exc_info=True)
    except Exception as e:
        log.error("something went wrong!", exc_info=True)
        self.retry(e)
        raise
    

@app.task(bind=True, default_retry_delay=300, max_retries=5)
def perform_adhocmutation_bgt(self, data, db='default'):
    rc, recordcount, traceback, msg= 0, 0, 'NA', ""
    try:
        log.info("perform_adhocmutation_bgt [start]")
        for record in data:
            details = record.pop('details')
            jobneedrecord = record
            log.info(f"details {details}")
            log.info(f'jobneedrecord {jobneedrecord}')

            with transaction.atomic(using = db):
                utils.set_db_for_router(db)
                if jobneedrecord['asset_id']==1:
                    #then it should be NEA
                    assetobjs = Asset.objects.filter(bu_id = jobneedrecord['bu_id'],
                                    assetcode = jobneedrecord['remarks'])
                    jobneedrecord['asset_id']= 1 if assetobjs.count() !=1 else assetobjs[0].id
                sqlQuery = "select * from fn_get_schedule_for_adhoc(%s, %s, %s, %s, %s)"
                args = [jobneedrecord['plandatetime'], jobneedrecord['bu_id'], jobneedrecord['people_id'], jobneedrecord['asset_id'], jobneedrecord['qset_id']]
                scheduletask = utils.runrawsql(sqlQuery, args, db=db)

                #have to update to scheduled task
                if(len(scheduletask) > 0):
                    jnid = scheduletask[0]['jobneedid']
                    recordcount+=1
                    obj = Jobneed.objects.get(id = jnid)
                    jobneedrecord.update({'performedby_id': jobneedrecord['people_id']})
                    record = clean_record(jobneedrecord)
                    jnsz = sz.JobneedSerializer(instance=obj,data=record)
                    if jnsz.is_valid(): 
                        isJnUpdated = jnsz.save()
                    else:
                        rc, traceback, msg = 1, jnsz.errors, 'Operation Failed'
                    
                    JND = JobneedDetails.objects.filter(jobneed_id = jnid).values()
                    for jnd in JND:
                        for dtl in details:
                            if jnd['question_id'] == dtl['question_id']:
                                obj = JobneedDetails.objects.get(uuid = dtl['uuid'])
                                record = clean_record(dtl)
                                jndsz = sz.JndSerializers(instance=obj, data = record)
                                if jndsz.is_valid():
                                    jndsz.save()
                    msg = "Scheduled Record (ADHOC) updated successfully!"
                
                #have to insert/create to adhoc task
                else:
                    record = clean_record(jobneedrecord)
                    jnsz = sz.JobneedSerializer(data = record)
                    
                    if jnsz.is_valid():
                        jninstance = jnsz.save()
                        log.debug(f'jninstance.is {jninstance.id}')
                        for dtl in details:
                            dtl.update({'jobneed_id':jninstance.id})
                            record = clean_record(dtl)
                            jndsz = sz.JndSerializers(data = record)
                            if jndsz.is_valid():
                                jndsz.save()
                        msg = "Record (ADHOC) inserted successfully!"
                    else:
                        rc, traceback = 1, jnsz.errors
                    if jobneedrecord['attachmentcount'] == 0:
                        #TODO send_email for ADHOC 
                        pass
                log.info(f'rc:{rc}, msg:{msg}, traceback:{traceback}, returncount:{recordcount}')
            #TODO send_email for Observation
                    
    except utils.NoDataInTheFileError as e:
        rc, traceback = 1, tb.format_exc()
        log.error('something went wrong', exc_info=True)
        raise
    except Exception as e:
        rc, traceback = 1, tb.format_exc()
        log.error('something went wrong', exc_info=True)
    return ServiceOutputType(rc=rc, recordcount = recordcount, msg = msg, traceback = traceback)