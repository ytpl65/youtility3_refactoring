from api import serializers as sz
from apps.attendance.models import PeopleEventlog
from apps.activity.models import (Jobneed, JobneedDetails, Attachment)
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
log = getLogger('__main__')

def get_model_or_form(tablename):
    match tablename:
        case "peopleeventlog":
            return PeopleEventlog
        case 'jobneed':
            return  Jobneed
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
    try:
        with open(uploadedfile, 'wb+') as destination:
            for fb in filebuffer:
                for chunk in fb.chunks():
                    destination.write(chunk)
                    del chunk
                del fb
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
    
    
    
def perform_uploadattachment(input):
    rc, traceback = 0,  'NA'
    returnid = msg=None
    try:
        import os
        file_buffer = input.image
        filename = input.filename
        pelogid = input.pelogid
        peopleid = input.peopleid
        path = input.path
        home_dir = os.path.expanduser('~') + '/'
        filepath = home_dir + input.path
        uploadfile = f'{filepath}/{input.filename}'
        iscreated = get_or_create_dir(filepath)
        log.info(f'filepath is {iscreated}')
        write_file_to_dir(file_buffer, uploadfile)
        resp = perform_insertrecord(input)
        if pelogid!=1:
            if ATT := Attachment.objects.get_attachment_record(resp.data['returnid']):
                ic("len(ATT) > 0:")
                if PEOPLE_ATT := PeopleEventlog.objects.get_people_attachment(pelogid):
                    ic("if (len(PEOPLE_ATT)>0):")
                    ic(ATT.ownername_id, PEOPLE_ATT.people_id)
                    if PEOPLE_PIC := Attachment.objects.get_people_pic(ATT.ownername_id, PEOPLE_ATT.people_id):
                        default_image_path = PEOPLE_PIC.default_img_path
                        default_image_path = home_dir + default_image_path
                        from deepface import DeepFace
                        fr_results = DeepFace.verify(img1_path = default_image_path, img2_path = uploadfile)
                        PeopleEventlog.objects.update_fr_results(fr_results, pelogid, peopleid)
                        msg = f"""Face Recognition {"passed" if fr_results['verified'] else 'failed'}"""
    except Exception as e:
        rc, traceback, msg = 1, traceback.format_exc(), Messages.UPLOAD_FAILED
        log.error('something went wrong', exc_info=True)
    return ServiceOutputType(rc=rc, returnid = returnid, msg = msg, traceback = traceback)


@app.task(bind=True, default_retry_delay=1300, max_retries = 5)
def perform_insertrecord(file, tablename, request=None):
    log.info('perform_insertrecord [start]')
    rc, returnid, traceback= 0, 0, 'NA'
    instance = None
    
    
    try:
        data = get_json_data(file)
        model = get_model_or_form(tablename)
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
                for record in data:
                    record = clean_record(record)
                    log.info(f'record after cleaning {pformat(record)}')
                    instance = model.objects.create(**record)
                    returnid+=1
        except Exception:
            raise
        if returnid:
            msg = Messages.INSERT_SUCCESS
    except Exception as e:
        log.error("something went wrong!", exc_info=True)
        msg, rc, traceback = Messages.INSERT_FAILED, 1, tb.format_exc()
        self.retry(e)
    return  ServiceOutputType(rc=rc, returnid = returnid, msg = msg, traceback = traceback)


def get_json_data(file):
    import gzip
    import json
    try:
        ic(file, type(file))
        with gzip.open(file, 'rb') as f: 
            s = f.read().decode('utf-8')
            s = s.replace("'", "")
            json_data = json.loads(s) 
            return json_data
    except Exception as  e:
        log.error("File unzipping error", exc_info=True)
    return None, None

def update_record(details, jobneed, Jn, Jnd):
    alerttype = 'OBSERVATION'
    record = clean_record(jobneed)
    ic(record)
    try:
        with transaction.atomic(using=utils.get_current_db_name()):
            isJnUpdated = Jn.objects.filter(
                uuid = record['uuid']).update(**record)
            isJndUpdated = update_jobneeddetails(details, Jnd)
            if isJnUpdated and  isJndUpdated:
                #utils.alert_email(input.jobneedid, alerttype)
                #TODO send observation email
                #TODO send deviation mail
                return True
    except Exception:
        raise


def update_jobneeddetails(jobneeddetails, Jnd):
    if jobneeddetails:
        updated=0
        for detail in jobneeddetails:
            record = clean_record(detail)
            ic(record)
            Jnd.objects.filter(uuid = detail['uuid']).update(**record)
            updated+=1
        if len(jobneeddetails) == updated: return True 


@app.task(bind=True, default_retry_delay=1300, max_retries = 5)
def perform_tasktourupdate(file, request):
    log.info("perform_tasktourupdate [start]")
    rc, returnid, traceback= 0, None, 'NA'
    instance, msg = None, ""

    try:
        data = get_json_data(file)
        ic(data)
        details = data.pop('details')
        jobneed = data
        ic(jobneed)
        ic(details)
        if updated :=  update_record(details, jobneed, Jobneed, JobneedDetails):
            msg, returnid = Messages.UPDATE_SUCCESS, updated
    
    except IntegrityError as e:
        log.error("Database Error", exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    
    except Exception as e:
        log.error('Something went wrong', exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
        self.retry(e)
    return ServiceOutputType(rc=rc, msg=msg, returnid=returnid, traceback=traceback)



def perform_reportmutation(file):
    rc, returnid, traceback= 0, None, 'NA'
    instance = None
    try:
        data = get_json_data(file)
        ic(data)
        if data:
            child = data.pop('child', None)
            parent = data
            try:
                with transaction.atomic(using=utils.get_current_db_name()):
                    if child and len(child) > 0 and parent:
                        jobneed_parent_post_data = parent
                        jn_parent_serializer = sz.JobneedSerializer(data=clean_record(jobneed_parent_post_data))
                        rc, returnid, traceback, msg = save_parent_childs(sz, jn_parent_serializer, child, Messages)
                    else:
                        log.error(Messages.NODETAILS)
                        msg, rc = Messages.NODETAILS, 1
            except Exception as e:
                raise
    except Exception as e:
        msg, traceback, rc = Messages.INSERT_FAILED, tb.format_exc(), 1
        log.error('something went wrong', exc_info=True)
    return ServiceOutputType(rc=rc, msg=msg, returnid=returnid, traceback=traceback)


def save_parent_childs(sz, jn_parent_serializer, child, M):
    rc, returnid, traceback= 0, None, 'NA'
    instance = None
    if jn_parent_serializer.is_valid():
        parent = jn_parent_serializer.save()
        allsaved=0
        for ch in child:
            ic(ch, type(child))
            details = ch.pop('details')
            ic(details, type(details))
            ch.update({'parent_id':parent.id})
            child_serializer = sz.JobneedSerializer(data=clean_record(ch))
            
            if child_serializer.is_valid():
                child_instance = child_serializer.save()
                for dtl in details:
                    ic(dtl, type(dtl))
                    dtl.update({'jobneed_id':child_instance.id})
                    ch_detail_serializer = sz.JndSerializers(data=clean_record(dtl))
                    if ch_detail_serializer.is_valid():
                        ch_detail_serializer.save()
                    else:
                        log.error(ch_detail_serializer.errors)
                        traceback, msg, rc = str(ch_detail_serializer.errors), M.INSERT_FAILED, 1
                allsaved+=1
            else:
                log.error(child_serializer.errors)
                traceback, msg, rc = str(child_serializer.errors), M.INSERT_FAILED, 1
        if allsaved == len(child):
            msg, returnid = M.INSERT_SUCCESS, parent.id
    else:
        log.error(jn_parent_serializer.errors)
        traceback, msg, rc = str(jn_parent_serializer.errors), M.INSERT_FAILED, 1
    return rc, returnid, traceback, msg
