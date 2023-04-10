from pprint import pformat
from apps.attendance.models import PeopleEventlog
from django.db import transaction
from .types import ServiceOutputType
from django.db.utils import IntegrityError
from apps.service import serializers as sz
from django.contrib.gis.geos import GEOSGeometry
from apps.core import utils
from .validators import clean_record
from apps.activity.models import (Jobneed, JobneedDetails, Asset)
import traceback as tb
from django.core.mail import send_mail, EmailMessage
from apps.y_helpdesk.models import Ticket
from intelliwiz_config.celery import app
from django.conf import settings
from .auth import Messages as AM
from django.apps import apps
from logging import getLogger
log = getLogger('mobile_service_log')   

from apps.work_order_management import utils as wutils

class Messages(AM):
    INSERT_SUCCESS = "Inserted Successfully!"
    UPDATE_SUCCESS = "Updated Successfully!"
    IMPROPER_DATA = "Failed to insert incorrect tablname or size of columns and rows doesn't match",
    WRONG_OPERATION = "Wrong operation 'id' is passed during insertion!"
    DBERROR = "Integrity Error!"
    INSERT_FAILED = "Failed to insert something went wrong!"
    UPDATE_FAILED = "Failed to Update something went wrong!"
    NOT_INTIATED = "Insert cannot be initated not provided necessary data"
    UPLOAD_FAILED = "Upload Failed!"
    NOTFOUND = "Unable to find people with this pelogid"
    START = "Mutation start"
    END = "Mutation end"
    ADHOCFAILED = 'Adhoc service failed'
    NODETAILS = ' Unable to find any details record against site/incident report'
    REPORTSFAILED = 'Failed to generate jasper reports'
    UPLOAD_SUCCESS = 'Uploaded Successfully!'


# utility functions
def insertrecord_json(records, tablename):
    uuids = []
    try:
        if model := get_model_or_form(tablename):
            for record in records:
                record = json.loads(record)
                record = json.loads(record)
                record = clean_record(record)
                log.info(f'record after cleaning\n {pformat(record)}')
                try:
                    obj = model.objects.get(uuid=record['uuid'])
                    model.objects.filter(uuid=obj.uuid).update(**record)
                    log.info("record is already exist so updating it now..")
                    uuids.append(str(record['uuid']))
                except model.DoesNotExist:
                    log.info("record is not exist so creating new one..")
                    model.objects.create(**record)
                    uuids.append(str(record['uuid']))
    except Exception as e:
        log.error("something went wrong", exc_info=True)
        raise e
    return uuids



def get_or_create_dir(path):
    import os
    created = True
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        created = False
    return created

def get_json_data(file):
    import gzip
    import json
    try:
        # ic((file, type(file))
        with gzip.open(file, 'rb') as f:
            s = f.read().decode('utf-8')
            s = s.replace("'", "")
            if isTrackingRecord := s.startswith('{'):
                log.info("Tracking record found")
                arr = s.split('?')
                s = json.dumps(arr)
            return json.loads(s)
    except Exception as e:
        log.error("File unzipping error", exc_info=True)
    return None, None


def get_model_or_form(tablename):
    if tablename == 'peopleeventlog':
        return apps.get_model('attendance', 'PeopleEventlog')
    if tablename == 'attachment':
        return  apps.get_model('activity', 'Attachment')
    if tablename == 'jobneed':
        return apps.get_model('activity', 'Jobneed')
    if tablename == 'jobneeddetails':
        return apps.get_model('activity', 'JobneedDetails')
    if tablename == 'deviceeventlog':
        return apps.get_model('activity', 'DeviceEventlog')
    if tablename == 'ticket':
        return apps.get_model('y_helpdesk', 'Ticket')
    if tablename == 'asset':
        return  apps.get_model('activity', 'Asset')
    if tablename == 'tracking':
        return apps.get_model('attendance', 'Tracking')
    if tablename == 'typeassist':
        return apps.get_model('onboarding', 'TypeAssist')
    if tablename == 'wom':
        return apps.get_model('work_order_management', 'Wom')
    if tablename == 'womdetails':
        return apps.get_model('work_order_management', 'WomDetails')
    if tablename == 'business unit':
        return apps.get_model('onboarding', 'Bt')

def get_object(uuid, model):
    try:
        return model.objects.get(uuid = uuid)
    except model.DoesNotExist as e:
        raise Exception from e

def save_jobneeddetails(data):
    import json
    jobneeddetails_post_data = json.loads(data['jobneeddetails'])


def get_or_create_dir(path):
    import os
    created = True
    if not os.path.exists(path):
        os.makedirs(path)
    else: created= False
    return created

def write_file_to_dir(filebuffer, uploadedfilepath):
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    path = default_storage.save(uploadedfilepath, ContentFile(filebuffer.read()))
    log.info(f"file saved to {path}")


def insertrecord(record, tablename):
    try:
        if model := get_model_or_form(tablename):
            record = clean_record(record)
            log.info(f'record after cleaning\n {pformat(record)}')
            if model.objects.filter(uuid = record['uuid']).exists():
                model.objects.filter(uuid = record['uuid']).update(**record)
                log.info("record is already exist so updating it now..")
                return model.objects.get(uuid = record['uuid'])
            else:
                log.info("record does not exist so creating it now..")
                return model.objects.create(**record)        
    except Exception as e:
        log.error("something went wrong while inserting/updating record", exc_info = True)
        raise e



def update_record(details, jobneed_record, JnModel, JndModel):
    '''
    takes details(jobneeddetails list), jobneed_record, JnModel, JndModel
    updates both jobneed and its jobneeddetails
    '''
    record = clean_record(jobneed_record)
    try:
        instance = JnModel.objects.get(uuid = record['uuid'])
        jn_parent_serializer = sz.JobneedSerializer(data = record, instance = instance)
        if jn_parent_serializer.is_valid():
            jobneed = jn_parent_serializer.save()
            jobneed.geojson['gpslocation'] = get_readable_addr_from_point(jobneed.gpslocation)
            jobneed.save()
            log.info("parent jobneed is valid and saved successfully")
            if jobneed.jobstatus == 'AUTOCLOSED' and len(details) == 0:
                return True
            elif isJndUpdated := update_jobneeddetails(details, JndModel):
                log.info('parent jobneed and its details are updated successully')
                alert_sendmail(jobneed, 'observation', atts=True)
                alert_sendmail(jobneed, 'deviation', atts=True)
                return True
        else: 
            log.error(f"parent jobneed record has some errors\n{jn_parent_serializer.errors} ", exc_info = True )
    except Exception:
        log.error("update_record failed", exc_info = True)
        raise
    return False



def update_jobneeddetails(jobneeddetails, JndModel):
    try:
        if jobneeddetails:
            updated = 0
            log.info(f'total {len(jobneeddetails)} JND records found')
            for detail in jobneeddetails:
                record = clean_record(detail)
                log.info(f'JND record after cleaning\n {pformat(record)}')
                instance = JndModel.objects.get(uuid = record['uuid'])
                jnd_ser = sz.JndSerializers(data = record, instance = instance)
                if jnd_ser.is_valid(): 
                    jnd_ser.save()
                    updated += 1
                else:
                    log.error(f'JND record with this uuid: {record["uuid"]} has some errors!\n {jnd_ser.errors}', exc_info=True)
            if len(jobneeddetails) == updated: 
                log.info(f'All {updated} JND records are updated successfully')
                return True
            else:
                log.warning(f'failed to update all {len(jobneeddetails)} JND records')
    except Exception as e:
        log.error('jobneed details record failed to save', exc_info= True)
        raise


def save_parent_childs(sz, jn_parent_serializer, child, M):
    log.info("save_parent_childs ............start")
    try:
        rc,  traceback= 0,  'NA'
        instance = None
        if jn_parent_serializer.is_valid():
            parent = jn_parent_serializer.save()
            log.info('parent record for report mutation saved')
            allsaved = 0
            log.info(f'Total {len(child)} child records found for report mutation')
            for ch in child:
                details = ch.pop('details')
                log.info(f'Total {len(details)} detail records found for the chid with this uuid:{ch["uuid"]}')
                ch.update({'parent_id':parent.id})
                child_serializer = sz.JobneedSerializer(data = clean_record(ch))

                if child_serializer.is_valid():
                    child_instance = child_serializer.save()
                    log.info(f"child record with this uuid: {child_instance.uuid} saved for report mutation")
                    for dtl in details:
                        dtl.update({'jobneed_id':child_instance.id})
                        ch_detail_serializer = sz.JndSerializers(data = clean_record(dtl))
                        if ch_detail_serializer.is_valid():
                            ch_detail_serializer.save()
                        else:
                            log.error(f"detail record of this child uuid:{child_instance.uuid} has some errors: {ch_detail_serializer.errors}")
                            traceback, msg, rc = str(ch_detail_serializer.errors), M.INSERT_FAILED, 1
                    allsaved += 1
                else:
                    log.error(f'child record has some errors:{child_serializer.errors}')
                    traceback, msg, rc = str(child_serializer.errors), M.INSERT_FAILED, 1
            if allsaved == len(child):
                msg= M.INSERT_SUCCESS
                log.info(f'All {allsaved} child records saved successfully')
        else:
            log.error(jn_parent_serializer.errors)
            traceback, msg, rc = str(jn_parent_serializer.errors), M.INSERT_FAILED, 1
        log.info("save_parent_childs ............end")
        return rc, traceback, msg
    except Exception:
        log.error("something went wrong",exc_info = True)
        raise


def save_linestring_and_update_pelrecord(obj):
    # sourcery skip: identity-comprehension
    from apps.attendance.models import Tracking
    from django.contrib.gis.geos import LineString
    try:

        bet_objs = Tracking.objects.filter(reference = obj.uuid).order_by('receiveddate')
        line = [[coord for coord in obj.gpslocation] for obj in bet_objs]
        if len(line) > 1:
            ls = LineString(line, srid = 4326)
            # transform spherical mercator projection system
            ls.transform(3857)
            d = round(ls.length / 1000)
            obj.distance = d
            ls.transform(4326)
            obj.journeypath = ls
            obj.geojson['startlocation'] = get_readable_addr_from_point(obj.startlocation)
            obj.geojson['endlocation'] = get_readable_addr_from_point(obj.endlocation)
            obj.save()
            #bet_objs.delete()
            log.info("save linestring is saved..")
            
    except Exception as e:
        log.info('ERROR while saving line string', exc_info = True)
        raise




def update_adhoc_record(scheduletask, jobneedrecord, details):
    rc, recordcount, traceback, msg= 1, 0, 'NA', ""
    jnid = scheduletask[0]['jobneedid']
    recordcount += 1
    obj = Jobneed.objects.get(id = jnid)
    jobneedrecord.update({'performedby_id': jobneedrecord['people_id']})
    record = clean_record(jobneedrecord)
    jnsz = sz.JobneedSerializer(instance = obj,data = record)
    if jnsz.is_valid(): 
        isJnUpdated = jnsz.save()
        rc=0
    else:
        rc, traceback, msg = 1, jnsz.errors, 'Operation Failed'

    JND = JobneedDetails.objects.filter(jobneed_id = jnid).values()
    for jnd in JND:
        for dtl in details:
            if jnd['question_id'] == dtl['question_id']:
                obj = JobneedDetails.objects.get(uuid = dtl['uuid'])
                record = clean_record(dtl)
                jndsz = sz.JndSerializers(instance = obj, data = record)
                if jndsz.is_valid():
                    jndsz.save()
    recordcount += 1
    rc=0
    msg = "Scheduled Record (ADHOC) updated successfully!"
    return rc, traceback, msg, recordcount

def insert_adhoc_record(jobneedrecord, details):
    rc, recordcount, traceback, msg= 1, 0, 'NA', ""
    record = clean_record(jobneedrecord)
    jnsz = sz.JobneedSerializer(data = record)

    if jnsz.is_valid():
        jninstance = jnsz.save()
        for dtl in details:
            dtl.update({'jobneed_id':jninstance.id})
            record = clean_record(dtl)
            jndsz = sz.JndSerializers(data = record)
            if jndsz.is_valid():
                jndsz.save()
        msg = "Record (ADHOC) inserted successfully!"
        recordcount += 1
        rc=0
    else:
        rc, traceback = 1, jnsz.errors
    return rc, traceback, msg, recordcount




def get_email_recipients(jobneed):
    from apps.peoples.models import People
    from apps.onboarding.models import Bt
    
    #get email of siteincharge
    siemails = People.objects.get_siteincharge_emails(jobneed.bu_id)
    #get email of client admins
    adm_emails = People.objects.get_admin_emails(jobneed.client_id)
    return list(siemails) + list(adm_emails)
    

def get_context_for_mailtemplate(jobneed, subject):
    from apps.activity.models import JobneedDetails
    from datetime import timedelta
    when = jobneed.endtime + timedelta(minutes=jobneed.ctzoffset)
    return  {
        'details'     : list(JobneedDetails.objects.get_e_tour_checklist_details(jobneedid=jobneed.id)),
        'when'        : when.strftime("%d-%m-%Y %H:%M"),
        'tourtype'    : jobneed.identifier,
        'performedby' : jobneed.performedby.peoplename,
        'site'        : jobneed.bu.buname,
        'subject'     : subject,
        'jobdesc': jobneed.jobdesc
    }


def alert_sendmail(obj, event, atts=False):
    '''
    takes uuid, ownername (which is the model name) and event (observation or deviation)
    gets the record from model if record has alerts set to true then send mail based on event
    '''
    if event == 'observation': alert_observation(obj, atts)
    if event == 'deviation': alert_deviation(obj, atts)


def add_attachments(jobneed, msg):
    from django.conf import settings
    JND = JobneedDetails.objects.filter(jobneed_id = jobneed.id)

    jnd_atts = []
    for jnd in JND:
        if att := list(JobneedDetails.objects.getAttachmentJND(jnd.id)):
            jnd_atts.append(att[0])
    jn_atts = list(Jobneed.objects.getAttachmentJobneed(jobneed.id))
    total_atts = jn_atts + jnd_atts
    for att in total_atts:
        msg.attach_file(f"{settings.MEDIA_ROOT}/{att['filepath']}{att['filename']}")
        log.info("attachments are attached....")
    return msg
    
    


def alert_observation(jobneed, atts=False):
    from django.template.loader import render_to_string

    try:
        if jobneed.alerts:
            recipents = get_email_recipients(jobneed)
            if jobneed.identifier == 'EXTERNALTOUR':
                subject = f"[READINGS ALERT] Site with Sol Id: [{jobneed.bu.solid}], {jobneed.bu.buname} having checklist [{jobneed.qset.qsetname}] - readings out of range"
            elif jobneed.identifier == 'INTERNALTOUR':
                subject = f"[READINGS ALERT] Checkpoint with Name: {jobneed.asset.assetname} at Site: {jobneed.bu.buname} having checklist [{jobneed.qset.qsetname}] - readings out of range"
            else:
                subject = f"[READINGS ALERT] Site with Name: {jobneed.bu.buname} having checklist [{jobneed.qset.qsetname}] - readings out of range"
            context = get_context_for_mailtemplate(jobneed, subject)

            html_message = render_to_string('observation_mail.html', context)
            log.info(f"Sending alert mail with subject {subject}")
            msg = EmailMessage()
            msg.subject = subject
            msg.body  = html_message
            msg.from_email = settings.EMAIL_HOST_USER
            msg.to = recipents
            msg.content_subtype = 'html'
            if atts:
                log.info('Attachments are going to attach')
                #add attachments to msg
                msg = add_attachments(jobneed, msg)
            msg.send()
            log.info(f"Alert mail sent to {recipents} with subject {subject}")
    except Exception as e:
        log.error("Error while sending alert mail", exc_info=True)
        
        

def alert_deviation(uuid, ownername):
    pass



def get_readable_addr_from_point(point):
    import googlemaps
    try:
        if hasattr(point, 'coords') and point.coords[0] not in [0.0, "0.0"]:
            gmaps = googlemaps.Client(key='AIzaSyDVbA53nxHKUOHdyIqnVPD01aOlTitfVO0')
            result = gmaps.reverse_geocode(point.coords[::-1])
            log.info("reverse geocoding complete, results returned")
            return result[0]['formatted_address']
        log.info("Not a valid point, returned empty string")
        return ""
    except Exception as e:
        log.error("something went wrong while reverse geocoding", exc_info=True)
        return ""
    
def save_addr_for_point(obj):
    if hasattr(obj, 'gpslocation'):
        obj.geojson['gpslocation'] = get_readable_addr_from_point(obj.gpslocation)
    if hasattr(obj, 'startlocation'):
        obj.geojson['startlocation'] = get_readable_addr_from_point(obj.startlocation)
    if hasattr(obj, 'endlocation'):
        obj.geojson['endlocation'] = get_readable_addr_from_point(obj.endlocation)
    obj.save()
    
def call_service_based_on_filename(data, filename, db='default', request=None, user=None):
    log.info(f'filename before calling {filename}')
    if filename == 'insertRecord.gz':
        log.info("calling insertrecord. service..")
        return perform_insertrecord.delay(file=data, db = db, bg=True, userid=user)
    if filename == 'updateTaskTour.gz':
        log.info("calling updateTaskTour service..")
        return perform_tasktourupdate.delay(file=data, db = db, bg=True)
    if filename == 'uploadReport.gz':
        log.info("calling uploadReport service..")
        return perform_reportmutation.delay(file=data, db = db, bg=True)
    if filename == 'adhocRecord.gz':
        log.info("calling adhocRecord service..")
        return perform_adhocmutation.delay(file=data, db = db, bg=True)
    


def get_user_instance(id):
    log.info(f"people id: {id} type: {type(id)}")
    from apps.peoples.models import People
    return People.objects.get(id = int(id))



@app.task(bind = True, default_retry_delay = 300, max_retries = 5)
def perform_tasktourupdate(self, file, request=None, db='default', bg=False):
    rc, recordcount, traceback= 1, 0, 'NA'
    instance, msg = None, ""

    try:
        log.info(
            f"""perform_tasktourupdate(file = {file}, bg = {bg}, db = {db} runnning in {'background' if bg else "foreground"})"""
        )
        data = file if bg else get_json_data(file)
        log.info(f'data: {pformat(data)}')
        if len(data) == 0: raise utils.NoRecordsFound
        log.info(f'total {len(data)} records found for task tour update')
        for record in data:
            details = record.pop('details')
            jobneed = record
            with transaction.atomic(using = db):
                if isupdated :=  update_record(details, jobneed, Jobneed, JobneedDetails):
                    recordcount += 1
                    log.info(f'{recordcount} task/tour updated successfully')
        if len(data) == recordcount:
            msg = Messages.UPDATE_SUCCESS
            log.info(f'All {recordcount} task/tour records are updated successfully')
            rc=0
    except utils.NoRecordsFound as e:
        log.warning('No records found for task/tour update', exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    except IntegrityError as e:
        log.error("Database Error", exc_info = True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    except Exception as e:
        log.error('Something went wrong', exc_info = True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    return ServiceOutputType(rc = rc, msg = msg, recordcount = recordcount, traceback = traceback)


@app.task(bind = True, default_retry_delay = 300, max_retries = 5)
def perform_insertrecord(self, file, request = None, db='default', filebased = True, bg=False, userid=None):
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
    rc, recordcount, traceback= 1, 0, 'NA'
    instance = None
    log.info(
            f"""perform_insertrecord(file = {file}, bg = {bg}, db = {db}, filebased = {filebased} {request = } { userid = } runnning in {'background' if bg else "foreground"})"""
        )
    try:
        
        if bg:
            data = file
        else:
            data = get_json_data(file) if filebased else [file]
        log.info(f'data = {pformat(data)} and length of data {len(data)}')
        
        if len(data) == 0: raise utils.NoRecordsFound
        with transaction.atomic(using = db):

            for record in data:
                tablename = record.pop('tablename')
                obj = insertrecord(record, tablename)
                user = get_user_instance(userid or request.user.id)
                if tablename == 'ticket' and isinstance(obj, Ticket): utils.store_ticket_history(
                    instance = obj, request=request, user=user)
                if tablename == 'wom': wutils.notify_wo_creation(id = obj.id)
                allconditions = [
                    hasattr(obj, 'peventtype'), hasattr(obj, 'endlocation'), 
                    hasattr(obj, 'punchintime'), hasattr(obj, 'punchouttime')]

                if all(allconditions) and all([tablename == 'peopleeventlog',
                        obj.peventtype.tacode in ('CONVEYANCE', 'AUDIT'),
                        obj.endlocation,obj.punchouttime, obj.punchintime]):
                    log.info("save line string is started")
                    save_linestring_and_update_pelrecord(obj)
                recordcount += 1
                log.info(f'{recordcount} record inserted successfully')
        if len(data) == recordcount:
            msg = Messages.INSERT_SUCCESS
            log.info(f'All {recordcount} records are inserted successfully')
            rc=0
    except utils.NoRecordsFound as e:
        log.warning('No records found for insertrecord service', exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.INSERT_FAILED
    except Exception as e:
        log.error("something went wrong!", exc_info = True)
        msg, rc, traceback = Messages.INSERT_FAILED, 1, tb.format_exc()
    return  ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)



@app.task(bind = True, default_retry_delay = 300, max_retries = 5)
def perform_reportmutation(self, file, db= 'default', bg=False):
    rc, recordcount, traceback= 1, 0, 'NA'
    instance = None
    try:
        log.info(
            f"""perform_reportmutation(file = {file}, bg = {bg}, db = {db}, runnning in {'background' if bg else "foreground"})"""
        )
        data = file if bg else get_json_data(file)
        log.info(f'data: {pformat(data)}')
        if len(data) == 0: raise utils.NoRecordsFound
        log.info(f"'data = {pformat(data)} {len(data)} Number of records found in the file")
        for record in data:
            child = record.pop('child', None)
            parent = record
            try:
                with transaction.atomic(using = db):
                    if child and len(child) > 0 and parent:
                        jobneed_parent_post_data = parent
                        jn_parent_serializer = sz.JobneedSerializer(data = clean_record(jobneed_parent_post_data))
                        rc,  traceback, msg = save_parent_childs(sz, jn_parent_serializer, child, Messages)
                        if rc == 0: recordcount += 1
                        # ic((recordcount)
                    else:
                        log.error(Messages.NODETAILS)
                        msg, rc = Messages.NODETAILS, 1
            except Exception as e:
                log.error('something went wrong while saving \
                          parent and child for report mutations', exc_info = True)
                raise
        if len(data) == recordcount:
            msg = Messages.UPDATE_SUCCESS
            log.info(f'All {recordcount} report records are updated successfully')
            rc=0
    except utils.NoRecordsFound as e:
        log.warning('No records found for report mutation', exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    except Exception as e:
        msg, traceback, rc = Messages.INSERT_FAILED, tb.format_exc(), 1
        log.error('something went wrong', exc_info = True)
    return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)


@app.task(bind = True, default_retry_delay = 300, max_retries = 5)
def perform_adhocmutation(self, file, db='default', bg=False):  # sourcery skip: remove-empty-nested-block, remove-redundant-if, remove-redundant-pass
    rc, recordcount, traceback, msg= 1, 0, 'NA', ""
    try:
        log.info(
            f"""perform_adhocmutation(file = {file}, bg = {bg}, db = {db}, runnning in {'background' if bg else "foreground"})"""
        )
        if bg:
            data = file
        elif not (data := get_json_data(file)):
            raise utils.NoDataInTheFileError
        log.info(f"'data = {pformat(data)} {len(data)} Number of records found in the file")
        for record in data:
            details = record.pop('details')
            jobneedrecord = record

            with transaction.atomic(using = db):
                if jobneedrecord['asset_id'] ==  1:
                    # then it should be NEA
                    assetobjs = Asset.objects.filter(bu_id = jobneedrecord['bu_id'],
                                    assetcode = jobneedrecord['remarks'])
                    jobneedrecord['asset_id']= 1 if assetobjs.count()  !=  1 else assetobjs[0].id
                sqlQuery = "select * from fn_get_schedule_for_adhoc(%s, %s, %s, %s, %s)"
                args = [jobneedrecord['plandatetime'], jobneedrecord['bu_id'], jobneedrecord['people_id'], jobneedrecord['asset_id'], jobneedrecord['qset_id']]
                scheduletask = utils.runrawsql(sqlQuery, args, db = db)

                # have to update to scheduled task
                if(len(scheduletask) > 0):
                    rc, traceback, msg, recordcount = update_adhoc_record(scheduletask, jobneedrecord, details)
                # have to insert/create to adhoc task
                else:
                    rc, traceback, msg, recordcount = insert_adhoc_record(jobneedrecord, details)
                if jobneedrecord['attachmentcount'] == 0:
                    # TODO send_email for ADHOC 
                    pass
            # TODO send_email for Observation

    except utils.NoDataInTheFileError as e:
        rc, traceback = 1, tb.format_exc()
        log.error('No data in the file error', exc_info = True)
        raise
    except Exception as e:
        rc, traceback = 1, tb.format_exc()
        log.error('something went wrong', exc_info = True)
    return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)


def perform_uploadattachment(file,  record, biodata):
    rc, traceback, resp = 0,  'NA', 0
    recordcount = msg = None
    # ic(file, tablename, record, type(record), biodata, type(biodata))
    

    file_buffer = file
    filename    = biodata['filename']
    peopleid    = biodata['people_id']
    path        = biodata['path']
    ownerid     = biodata['owner']
    onwername   = biodata['ownername']
    home_dir    = f'{settings.MEDIA_ROOT}/'
    filepath    = home_dir + path
    uploadfile  = f'{filepath}/{filename}'
    db          = utils.get_current_db_name()
    
    log.info(f"file_buffer: '{file_buffer}' \n'onwername':{onwername}, \nownerid: '{ownerid}' \npeopleid: '{peopleid}' \npath: {path} \nhome_dir: '{home_dir}' \nfilepath: '{filepath}' \nuploadfile: '{uploadfile}'")
    try:
        with transaction.atomic(using = db):
            iscreated = get_or_create_dir(filepath)
            log.info(f'Is FilePath created? {iscreated}')
            write_file_to_dir(file_buffer, uploadfile)
            #send_alert_mails_if_any(obj)
            rc, traceback, msg = 0, tb.format_exc(), Messages.UPLOAD_SUCCESS
            recordcount = 1
            log.info('file uploaded success')
    except Exception as e:
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
        log.error('something went wrong', exc_info = True)
    try:
        if record.get('localfilepath'): record.pop('localfilepath')
        obj = insertrecord(record, 'attachment')
        log.info(f'Attachment record inserted: {obj.filepath}')
        
        log.info(f"ownername:{onwername} and owner:{ownerid}")
        model = get_model_or_form(onwername.lower())
        eobj = model.objects.get(uuid=ownerid)
        log.info(f"object retrived of type {type(eobj)}")
        

        if hasattr(eobj, 'peventtype'): log.info(f'Event Type: {eobj.peventtype.tacode}')
        if hasattr(eobj, 'peventtype') and eobj.peventtype.tacode in ['SELF', 'MARK']:
            from .tasks import perform_facerecognition_bgt
            results = perform_facerecognition_bgt.delay(ownerid, peopleid, db)
            log.warning(f"face recognition status {results.state}")
    except Exception as e:
        log.error('something went wrong while perform_uploadattachment', exc_info = True)
    return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)


