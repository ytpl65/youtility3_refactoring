from graphql import GraphQLError
from apps.service import serializers as sz
from apps.attendance.models import PeopleEventlog
from apps.activity.models import (Jobneed, JobneedDetails, Attachment, Asset, DeviceEventlog)
from apps.y_helpdesk.models import Ticket, EscalationMatrix
from apps.onboarding.models import TypeAssist
from apps.peoples.models import People
from apps.attendance.models import Tracking
from apps.core import utils
from django.db.utils import IntegrityError
from django.db import transaction
from django.db.models import Q
from .auth import Messages as AM
from .types import ServiceOutputType
import traceback as tb
from django.conf import settings
from .validators import clean_record
from pprint import pformat
from intelliwiz_config.celery import app
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import timedelta, datetime, timezone
from apps.core.raw_queries import get_query
log = get_task_logger('django')
import json

def correct_image_orientation(img):
    # Check the current orientation
    if hasattr(img, '_getexif'):
        orientation = 0x0112
        exif = img._getexif()
        orientation = exif.get(orientation, 1) if exif is not None else 1
    # Rotate the image based on the orientation
    if orientation == 3:
        img = img.rotate(180, expand=True)
    elif orientation == 6:
        img = img.rotate(270, expand=True)
    elif orientation == 8:
        img = img.rotate(90, expand=True)
    return img


def make_square(path1, path2):
    from PIL import Image
    try:
        # Open the first image
        img1 = Image.open(path1)
        # Get the aspect ratio
        width, height = img1.size
        aspect_ratio = width / height
        log.info(f"aspect ratio of image 1 is {aspect_ratio}")
        # If the aspect ratio is not 1:1
        if aspect_ratio != 1:
            # Resize the image to make it square
            new_size = (min(width, height), min(width, height))
            img1 = img1.resize(new_size)
            log.info(f'new aspect ratio of image1  is {new_size[0]} x {new_size[1]}')
        # Save the new square image
        img1 = correct_image_orientation(img1)
        img1.save(path1)
        # Repeat the process for the second image
        img2 = Image.open(path2)
        width, height = img2.size
        aspect_ratio = width / height
        log.info(f"aspect ratio of image 2 is {aspect_ratio}")
        if aspect_ratio != 1:
            new_size = (min(width, height), min(width, height))
            img2 = img2.resize(new_size)
            log.info(f'new aspect ratio of image2 is {new_size[0]} x {new_size[1]}')
        
        img2 = correct_image_orientation(img2)
        img2.save(path2)
    except FileNotFoundError:
        print("Error: One or both of the provided file paths do not exist.")
    except IOError:
        print("Error: One or both of the provided files are not images.")
    except Exception as e:
        print("Error: An unknown error occurred. while performing make_square(path1, path2)",e)



def insertrecord(record, tablename):
    try:
        if model := get_model_or_form(tablename):
            record = clean_record(record)
            log.info(f'record after cleaning {pformat(record)}')
            obj = model.objects.get(uuid = record['uuid'])
            model.objects.filter(uuid = obj.uuid).update(**record)
            return model.objects.get(uuid = record['uuid'])
    except model.DoesNotExist:
        return model.objects.create(**record)
    except Exception as e:
        log.error("something went wrong", exc_info = True)
        raise e


def get_model_or_form(tablename):
    if tablename == 'peopleeventlog':return PeopleEventlog
    if tablename == 'attachment': return Attachment
    if tablename == 'jobneed': return Jobneed
    if tablename == 'jobneeddetails': return JobneedDetails
    if tablename == 'deviceeventlog': return DeviceEventlog
    if tablename == 'ticket': return Ticket
    if tablename == 'asset': return Asset
    if tablename == 'tracking': return Tracking
    if tablename == 'typeassist': return TypeAssist


def get_or_create_dir(path):
    import os
    created = True
    if not os.path.exists(path):
        os.makedirs(path)
    else: created= False
    return created

def write_file_to_dir(filebuffer, uploadedfile):
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    path = default_storage.save(uploadedfile, ContentFile(filebuffer.read()))
    log.info("file is uploaded in file system successfully...")
    log.info(f'here is path of that file: {path}')



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



def insertrecord(record, tablename):
    try:
        if model := get_model_or_form(tablename):
            record = clean_record(record)
            ic(record)
            log.info(f'record after cleaning\n {pformat(record)}')
            obj = model.objects.get(uuid = record['uuid'])
            model.objects.filter(uuid = obj.uuid).update(**record)
            log.info("record is already exist so updating it now..")
            ic("updating")
            return model.objects.get(uuid = record['uuid'])
    except model.DoesNotExist:
        ic("creating")
        log.info("record is not exist so creating new one..")
        return model.objects.create(**record)
    except Exception as e:
        log.error("something went wrong", exc_info = True)
        raise e

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
                    obj = model.objects.get(uuid = record['uuid'])
                    model.objects.filter(uuid = obj.uuid).update(**record)
                    log.info("record is already exist so updating it now..")
                    uuids.append(str(record['uuid']))
                except model.DoesNotExist:
                    log.info("record is not exist so creating new one..")
                    model.objects.create(**record)
                    uuids.append(str(record['uuid']))
    except Exception as e:
        log.error("something went wrong", exc_info = True)
        raise e
    return uuids

def call_service_based_on_filename(data, filename, db='default'):
    log.info(f'filename before calling {filename}')
    if filename == 'insertRecord.gz':
        log.info("calling insertrecord. service..")
        return perform_insertrecord_bgt.delay(data, db = db)
    if filename == 'updateTaskTour.gz':
        log.info("calling updateTaskTour service..")
        return perform_tasktourupdate_bgt.delay(data, db = db)
    if filename == 'uploadReport.gz':
        log.info("calling uploadReport service..")
        return perform_reportmutation_bgt.delay(data, db = db)
    if filename == 'adhocRecord.gz':
        log.info("calling adhocRecord service..")
        return perform_adhocmutation_bgt.delay(data, db = db)




def perform_uploadattachment(file, tablename, record, biodata):
    rc, traceback, resp = 0,  'NA', 0
    recordcount = msg = None
    # ic(file, tablename, record, type(record), biodata, type(biodata))
    log.info('perform_uploadattachment [start +]')
    try:
        import os

        file_buffer = file
        # ic(file_buffer, type(file_buffer))
        filename   = biodata['filename']
        pelogid    = biodata['pelog_id']
        peopleid   = biodata['people_id']
        path       = biodata['path']
        home_dir   = f'{settings.MEDIA_ROOT}/'
        filepath   = home_dir + path
        uploadfile = f'{filepath}/{filename}'
        db         = utils.get_current_db_name()
        log.info(f"file_buffer: '{file_buffer}' \npelogid: '{pelogid}' \npeopleid: '{peopleid}' \npath: {path} home_dir: '{home_dir}' \nfilepath: '{filepath}' \nuploadfile: '{uploadfile}'")

        with transaction.atomic(using = db):
            utils.set_db_for_router(db)
            log.info(f'router is connected to db:{db}')
            iscreated = get_or_create_dir(filepath)
            log.info(f'Is FilePath created? {iscreated}')
            write_file_to_dir(file_buffer, uploadfile)
            rc, traceback, msg = 0, tb.format_exc(), Messages.UPLOAD_SUCCESS
            recordcount = 1
            log.info('file uploaded success')
    except Exception as e:
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
        log.error('something went wrong', exc_info = True)

    try:
        obj = insertrecord(record, 'attachment')
        log.info(f'Attachment record inserted: {obj.filepath}')
        pel = PeopleEventlog.objects.get(id=int(pelogid))
        log.info(f'Event Type: {pel.peventtype.tacode}')
        if pel.peventtype.tacode in ['SELF', 'MARK']:
            from .tasks import perform_facerecognition_bgt
            results = perform_facerecognition_bgt.delay(pelogid, peopleid, obj.owner, home_dir, uploadfile, db)
            log.warning(f"face recognition status {results.state}")
    except Exception as e:
        log.error('something went wrong while performing face recognition', exc_info = True)
    return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)


@app.task(bind = True, default_retry_delay = 300, max_retries = 5)
def perform_insertrecord_bgt(self, data, request = None, filebased = True, db='default'):
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

    rc, recordcount, traceback= 1, 0, 'NA'
    instance = None
    from .utils import save_addr_for_point
    try:
        if len(data) == 0: raise utils.NoRecordsFound
        with transaction.atomic(using = db):
            utils.set_db_for_router(db)
            log.info(f"router is connected to {db}")
            for record in data:
                tablename = record.pop('tablename')
                log.info(f'tablename: {tablename}')
                obj = insertrecord(record, tablename)
                if hasattr(obj, 'geojson'): save_addr_for_point(obj)
                if all([tablename == 'peopleeventlog',
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
    log.info(f'rc:{rc}, msg:{msg}, traceback:{traceback}, returncount:{recordcount}')
    return  ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)

def save_linestring_and_update_pelrecord(obj):
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
            obj.save()
            log.info("save linestring is saved..")
    except Exception as e:
        log.info('ERROR while saving line string', exc_info = True)
        raise

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
        log.error("File unzipping error", exc_info = True)
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

def update_record(details, jobneed_record, Jn, Jnd, db):
    from .utils import get_readable_addr_from_point, alert_sendmail
    alerttype = 'OBSERVATION'
    record = clean_record(jobneed_record)
    # ic((record)
    try:
        log.info(f"from function update_record() the router is connected to db {db}")
        instance = Jn.objects.get(uuid = record['uuid'])
        jn_parent_serializer = sz.JobneedSerializer(data = record, instance = instance)
        if jn_parent_serializer.is_valid():
            jobneed = jn_parent_serializer.save()
            jobneed.geojson['gpslocation'] = get_readable_addr_from_point(jobneed.gpslocation)
            jobneed.save()
            log.info(f"parent jobneed with this pk:{jobneed.pk} is valid and saved successfully")
            if isJndUpdated := update_jobneeddetails(details, Jnd):
                log.info('parent jobneed and its details are updated successully')
                if jobneed.alerts and jobneed.attachmentcount == 0:
                    alert_sendmail(jobneed, 'observation')
                    alert_sendmail(jobneed, 'deviation')
                return True
        else:
            log.error(f"parent jobneed record has some errors\n{jn_parent_serializer.errors} ", exc_info = True )
    except Exception:
        log.error('something went wrong', exc_info= True)
        raise

def update_jobneeddetails(jobneeddetails, Jnd, db):
    try:
        if jobneeddetails:
            updated = 0
            for detail in jobneeddetails:
                record = clean_record(detail)
                log.info(f'JND record after cleaning\n {pformat(record)}')
                instance = Jnd.objects.get(uuid = record['uuid'])
                jnd_ser = sz.JndSerializers(data = record, instance = instance)
                if jnd_ser.is_valid():
                    jnd = jnd_ser.save()
                    updated += 1
                else:
                    log.error(f'JND record with this uuid: {record["uuid"]} has some errors!\n {jnd_ser.errors}', exc_info=True)
            if len(jobneeddetails) == updated:
                log.info(f"All {updated} JND record are  updated successfully")
                return True
            else:
                log.warning(f'failed to update all {len(jobneeddetails)} JND records')
    except Exception as e:
        log.error('jobneed details record failed to save', exc_info = True)
        raise


@app.task(bind = True, default_retry_delay = 300, max_retries = 5)
def perform_tasktourupdate_bgt(self, data, request = None, db='default'):
    log.info("perform_tasktourupdate [start]")
    rc, recordcount, traceback= 1, 0, 'NA'
    instance, msg = None, ""

    try:
        # ic((data)
        if len(data) == 0: raise utils.NoRecordsFound
        log.info(f'total {len(data)} records found for task tour update')
        log.info(f'data: {pformat(data)}')
        for record in data:
            details = record.pop('details')
            jobneed = record
            with transaction.atomic(using = db):
                utils.set_db_for_router(db)
                log.info(f'router is connected to db{db}')
                if updated :=  update_record(details, jobneed, Jobneed, JobneedDetails, db):
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
    log.info(f'rc:{rc}, msg:{msg}, traceback:{traceback}, returncount:{recordcount}')
    return ServiceOutputType(rc = rc, msg = msg, recordcount = recordcount, traceback = traceback)


@app.task(bind = True, default_retry_delay = 300, max_retries = 5)
def perform_reportmutation_bgt(self, data, db='default'):
    rc, recordcount, traceback= 1, 0, 'NA'
    instance = None
    try:
        log.info('perform_reportmutation_bgt [start +]')
        if len(data) == 0: raise utils.NoRecordsFound
        for record in data:
            child = record.pop('child', None)
            parent = record
            try:
                with transaction.atomic(using = db):
                    utils.set_db_for_router(db)
                    log.info(f'the router is connected to db {db}')
                    if child and len(child) > 0 and parent:
                        jobneed_parent_post_data = parent
                        log.info(f'the parent record {pformat(jobneed_parent_post_data)}')
                        jn_parent_serializer = sz.JobneedSerializer(data = clean_record(jobneed_parent_post_data))
                        rc,  traceback, msg = save_parent_childs(sz, jn_parent_serializer, child, Messages, db)
                        if rc == 0: recordcount += 1
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
    log.info(f'rc:{rc}, msg:{msg}, traceback:{traceback}, returncount:{recordcount}')
    return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)


def save_parent_childs(sz, jn_parent_serializer, child, M, db):
    log.info("save_parent_childs ............start")
    try:
        rc, traceback= 0,  'NA'
        instance = None
        if jn_parent_serializer.is_valid():
            parent = jn_parent_serializer.save()
            log.info('parent record for report mutation saved')
            allsaved = 0
            log.info(f'Total {len(child)} child records found for report mutation')
            for ch in child:
                # ic((ch, type(child))
                details = ch.pop('details')
                # ic((details, type(details))
                log.info(f'Total {len(details)} detail records found for the chid with this uuid:{ch["uuid"]}')
                ch.update({'parent_id':parent.id})
                child_serializer = sz.JobneedSerializer(data = clean_record(ch))

                if child_serializer.is_valid():
                    child_instance = child_serializer.save()
                    log.info(f'child instance saved its pk is {child_instance.id}')
                    for dtl in details:
                        # ic((dtl, type(dtl))
                        dtl.update({'jobneed_id':child_instance.id})
                        ch_detail_serializer = sz.JndSerializers(data = clean_record(dtl))
                        if ch_detail_serializer.is_valid():
                            ch_dtl = ch_detail_serializer.save()
                        else:
                            log.error(f"detail record of this child uuid:{child_instance.uuid} has some errors: {ch_detail_serializer.errors}")
                            traceback, msg, rc = str(ch_detail_serializer.errors), M.INSERT_FAILED, 1
                    allsaved += 1

                else:
                    log.error(f'child record has some errors:{child_serializer.errors}')
                    traceback, msg, rc = str(child_serializer.errors), M.INSERT_FAILED, 1
            if allsaved == len(child):
                log.info(f'all childs:{len(child)} and its details records are saved successfully...')
                msg= M.INSERT_SUCCESS
        else:
            log.error(jn_parent_serializer.errors)
            traceback, msg, rc = str(jn_parent_serializer.errors), M.INSERT_FAILED, 1
        log.info("save_parent_childs ............end")
        log.info(f'rc:{rc} traceback {traceback} msg {msg} is the response being returned')
        return rc, traceback, msg
    except Exception:
        log.error("something went wrong",exc_info = True)
        raise

@app.task(bind = True, default_retry_delay = 300, max_retries = 5, name='Face recognition')
def perform_facerecognition_bgt(self, pel_uuid, peopleid, db='default'):
    # sourcery skip: remove-redundant-except-handler
    result = {'story':"perform_facerecognition_bgt()\n","traceback":""}
    result['story'] += f"inputs are {pel_uuid = } {peopleid = }, {db = }\n"
    try:
        log.info("perform_facerecognition ...start [+]")
        with transaction.atomic(using=utils.get_current_db_name()):
            utils.set_db_for_router(db)
            if pel_uuid not in [None,'NONE', '', 1]  and peopleid not in [None, 'NONE', 1, ""]:
                #people event pic
                pel_att = Attachment.objects.get_people_pic(pel_uuid, db)
                #people default profile pic
                people_obj = People.objects.get(id=peopleid)
                default_peopleimg = f'{settings.MEDIA_ROOT}/{people_obj.peopleimg.url.replace("/youtility4_media/", "")}'
                if default_peopleimg and pel_att.people_event_pic:
                    images_info = f"default image path:{default_peopleimg} and uploaded file path:{pel_att.people_event_pic}"
                    log.info(f'{images_info}')
                    result['story'] += f'{images_info}\n'
                    from deepface import DeepFace
                    make_square(default_peopleimg, pel_att.people_event_pic)
                    fr_results = DeepFace.verify(img1_path=default_peopleimg, img2_path=pel_att.people_event_pic, enforce_detection=False)
                    log.info(f"deepface verification completed and results are {fr_results}")
                    result['story'] += f"deepface verification completed and results are {fr_results}\n"
                    if PeopleEventlog.objects.update_fr_results(fr_results, pel_uuid, peopleid, db):
                        log.info("updation of fr_results in peopleeventlog is completed...")
    except ValueError as v:
        log.error("face recogntion image not found or face is not there...", exc_info = True)
        result['traceback'] += f'{tb.format_exc()}'
    except Exception as e:
        log.error("something went wrong! while performing face-recogntion in background", exc_info = True)
        result['traceback'] += f'{tb.format_exc()}'
        self.retry(e)
        raise


@app.task(bind = True, default_retry_delay = 300, max_retries = 5)
def perform_adhocmutation_bgt(self, data, db='default'):
    rc, recordcount, traceback, msg= 1, 0, 'NA', ""
    try:
        log.info("perform_adhocmutation_bgt [start]")
        for record in data:
            details = record.pop('details')
            jobneedrecord = record
            log.info(f"details {details}")
            log.info(f'jobneedrecord {jobneedrecord}')

            with transaction.atomic(using = db):
                utils.set_db_for_router(db)
                log.info(f'router is connected to db:{db}')
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
                    jnid = scheduletask[0]['jobneedid']
                    recordcount += 1
                    obj = Jobneed.objects.get(id = jnid)
                    jobneedrecord.update({'performedby_id': jobneedrecord['people_id']})
                    record = clean_record(jobneedrecord)
                    jnsz = sz.JobneedSerializer(instance = obj,data = record)
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
                                jndsz = sz.JndSerializers(instance = obj, data = record)
                                if jndsz.is_valid():
                                    jndsz.save()
                    msg = "Scheduled Record (ADHOC) updated successfully!"
                    log.info(f'{msg}')

                # have to insert/create to adhoc task
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
                        log.info(f'{msg}')
                    else:
                        rc, traceback = 1, jnsz.errors
                    if jobneedrecord['attachmentcount'] == 0:
                        # TODO send_email for ADHOC 
                        pass
            # TODO send_email for Observation

    except utils.NoDataInTheFileError as e:
        rc, traceback = 1, tb.format_exc()
        log.error('something went wrong', exc_info = True)
        raise
    except Exception as e:
        rc, traceback = 1, tb.format_exc()
        log.error('something went wrong', exc_info = True)
    log.info(f'rc:{rc}, msg:{msg}, traceback:{traceback}, returncount:{recordcount}')
    return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)




@shared_task(name="schedule_ppm_jobs")
def create_ppm_job(jobid=None):
    F, d = {}, []
    #resp = {'story':"", 'traceback':""}
    startdtz = enddtz = msg = resp = None
    from apps.activity.models import Job, Asset
    from apps.schedhuler.utils import (calculate_startdtz_enddtz_for_ppm, get_datetime_list,
                                       insert_into_jn_and_jnd, get_readable_dates, create_ppm_reminder)
    result = {'story':"", "traceback":""}
    
    try:
        #atomic transaction
        with transaction.atomic(using=utils.get_current_db_name()):
            if jobid:
                jobs = Job.objects.filter(id = jobid).values(*utils.JobFields.fields)
            else:
                jobs = Job.objects.filter(
                    ~Q(jobname='NONE'),
                    ~Q(asset__runningstatus = Asset.RunningStatus.SCRAPPED),
                    identifier = Job.Identifier.PPM.value,
                    parent_id = 1
                ).select_related('asset', 'pgroup', 'cuser', 'muser', 'people', 'qset').values(
                    *utils.JobFields.fields
                )
            


            if not jobs:
                msg = "No jobs found schedhuling terminated"
                result['story'] += f"{msg}\n"
                log.warning(f"{msg}", exc_info = True)
            total_jobs = len(jobs)

            if total_jobs > 0 and jobs is not None:
                log.info("processing jobs started found:= '%s' jobs", (len(jobs)))
                result['story'] += f"total jobs found {total_jobs}\n"
                for job in jobs:
                    startdtz, enddtz = calculate_startdtz_enddtz_for_ppm(job)
                    log.debug(f"Jobs to be schedhuled from startdatetime {startdtz} to enddatetime {enddtz}")
                    DT, is_cron, resp = get_datetime_list(job['cron'], startdtz, enddtz, resp)
                    log.debug(
                        "Jobneed will going to create for all this datetimes\n %s", (pformat(get_readable_dates(DT))))
                    if not is_cron: F[str(job['id'])] = job['cron']
                    status, resp = insert_into_jn_and_jnd(job, DT, resp)
                    if status:
                        d.append({
                            "job"   : job['id'],
                            "jobname" : job['jobname'],
                            "cron"    : job['cron'],
                            "iscron"  : is_cron,
                            "count"   : len(DT),
                            "status"  : status
                        })
                create_ppm_reminder(d)
                if F:
                    result['story'] += f'create_ppm_job failed job schedule list {pformat(F)}\n'
                    log.info(f"create_ppm_job Failed job schedule list:={pformat(F)}")
                    for key, value in list(F.items()):
                        log.info(f"create_ppm_job job_id: {key} | cron: {value}")
    except Exception as e:
        log.error("something went wrong create_ppm_job", exc_info=True)
        
    return resp if jobid else None
        
                
@shared_task(name="send_reminder_emails")
def send_reminder_email():
    #get all reminders which are not sent
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.core.mail import  EmailMessage
    from apps.reminder.models import Reminder

    resp = {'story':"", "traceback":""}
    reminders = Reminder.objects.get_all_due_reminders()
    resp['story'] += f"total due reminders are: {len(reminders)}\n"
    log.info(f"total due reminders are {len(reminders)}")
    try:
        for rem in reminders:
            resp['story'] += f"processing reminder with id: {rem['id']}"
            emails = utils.get_email_addresses([rem['people_id'], rem['cuser_id'], rem['muser_id']], [rem['group_id']])
            resp['story'] += f"emails recipents are as follows {emails}\n"
            recipents = list(set(emails + rem['mailids'].split(',')))
            subject = f"Reminder For {rem['job__jobname']}"
            context = {'job':rem['job__jobname'], 'plandatetime':rem['pdate'], 'jobdesc':rem['job__jobdesc'],
                    'creator':rem['cuser__peoplename'],'modifier':rem['muser__peoplename']}
            html_message = render_to_string('reminder_mail.html', context=context)
            resp['story'] += f"context in email template is {context}\n"
            log.info(f"Sending reminder mail with subject {subject}")
            msg = EmailMessage()
            msg.subject = subject
            msg.body  = html_message
            msg.from_email = settings.EMAIL_HOST_USER
            msg.to = recipents
            msg.content_subtype = 'html'
            msg.send()
            log.info(f"Reminder mail sent to {recipents} with subject {subject}")
    except Exception as e:
        log.error("Error while sending reminder email")
        resp['traceback'] = tb.format_exc()

    return resp

def send_email(subject, body):
    pass



def create_ticket_for_autoclose(jobneedrecord, ticketdesc):
    try:
        tkt, _ =  Ticket.objects.get_or_create(
            bu_id=jobneedrecord['bu_id'],
            status="NEW",
            client_id=jobneedrecord['client_id'],
            ticketcategory_id=jobneedrecord['ticketcategory_id'],
            ticketsource=Ticket.TicketSource.SYSTEMGENERATED,
            ticketdesc=ticketdesc,
            priority=jobneedrecord['priority'],
            
        )
        return Ticket.objects.filter(
            id = tkt.id
        ).select_related('bu', 'client', 'escalationtemplate').values(
            'ticketcategory_id', 'client_id', 'level', 'bu_id', 'id',
            'cdtz', 'ctzoffset'
        ).first()
    except Exception as e:
        log.error("something went wrong in create_ticket_for_autoclose", exc_info=True)
        
        
def update_job_autoclose_status(record):
    obj = Jobneed.objects.get(id=record['id'])
    obj.mdtz = datetime.now(timezone.utc)
    obj.jobstatus = 'AUTOCLOSED'
    obj.other_info['email_sent'] = record['ticketcategory__tacode'] == 'AUTOCLOSENOTIFY'
    obj.other_info['ticket_generated'] = record['ticketcategory__tacode'] == 'RAISETICKETNOTIFY'
    obj.other_info['autoclosed_by_server'] = True
    obj.save()
    
        
def get_escalation_of_ticket(tkt):
    if tkt:
        return EscalationMatrix.objects.filter(
            bu_id = tkt['bu_id'],
            escalationtemplate_id = tkt['ticketcategory_id'],
            client_id = tkt['client_id'],
            level = tkt['level'] + 1
        ).select_related('escalationtemplate', 'client', 'bu').values(
            'level', 'frequencyvalue', 'frequency'
        ).order_by('level').first() or []
    return []

@shared_task(name="auto_close_jobs")
def autoclose_job():
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.core.mail import  EmailMessage
    try:
        #get all expired jobs
        resp = {'story':"", 'traceback':""}
        expired = Jobneed.objects.get_expired_jobs()
        resp['story'] += f'total expired jobs = {len(expired)}\n'
        context = {}
        with transaction.atomic(using=utils.get_current_db_name()):
            resp['story'] += f"using database: {utils.get_current_db_name()}\n"
            for rec in expired:
                resp['story'] += f"processing record with id= {rec['id']}\n" 
                resp['story'] += f"record category is {rec['ticketcategory__tacode']}\n" 
                
                if rec['ticketcategory__tacode'] in ['AUTOCLOSENOTIFY', 'RAISETICKETNOTIFY']:
                    
                    log.info("notifying through email...")
                    pdate = rec["plandatetime"] + timedelta(minutes=rec['ctzoffset'])
                    pdate = pdate.strftime("%d-%b-%Y %H:%M")
                    edate = rec["expirydatetime"] + timedelta(minutes=rec['ctzoffset'])
                    edate = edate.strftime("%d-%b-%Y %H:%M")
                    
                    subject = f'AUTOCLOSE {"TOUR" if rec["identifier"] in  ["INTERNALTOUR", "EXTERNALTOUR"] else rec["identifier"] } planned on \
                    {pdate} not reported in time'
                    context = {
                        'subject'         : subject,
                        'buname'          : rec['bu__buname'],
                        'plan_dt'         : pdate,
                        'creatorname'     : rec['cuser__peoplename'],
                        'assignedto'      : rec['assignedto'],
                        'exp_dt'          : edate,
                        'show_ticket_body': False,
                        'identifier':rec['identifier'],
                        'jobdesc':rec['jobdesc']
                    }
                    

                    emails = utils.get_email_addresses([rec['people_id'], rec['cuser_id'], rec['muser_id']], [rec['pgroup_id']], [rec['bu_id']])
                    resp['story'] += f"email recipents are as follows {emails}\n"
                    log.info(f"recipents are as follows...{emails}")
                    msg = EmailMessage()
                    msg.subject = subject
                    msg.from_email = settings.EMAIL_HOST_USER
                    msg.to = emails
                    msg.content_subtype = 'html'

                    if rec['ticketcategory__tacode'] == 'RAISETICKETNOTIFY':
                        log.info("ticket needs to be generated")
                        context['show_ticket_body'] = True
                        jobdesc = f'AUTOCLOSE {"TOUR" if rec["identifier"] in  ["INTERNALTOUR", "EXTERNALTOUR"] else rec["identifier"] } \
                        planned on {pdate} not reported in time'
                        #DB OPERATION
                        ticket_data = create_ticket_for_autoclose(rec, jobdesc)
                        log.info(f'{ticket_data}')
                        if esc := get_escalation_of_ticket(ticket_data):
                            context['escalation'] = True
                            context['next_escalation'] = f"{esc['frequencyvalue']} {esc['frequency']}"
                        created_at = ticket_data['cdtz'] + timedelta(minutes=ticket_data['ctzoffset'])
                        created_at = created_at.strftime("%d-%b-%Y %H:%M")
                        
                        context['ticketno']       = ticket_data['id']
                        context['tjobdesc']       = jobdesc
                        context['categoryname']   = rec['ticketcategory__taname']
                        context['priority']       = rec['priority']
                        context['status']         = 'NEW'
                        context['tcreatedby']     = rec['cuser__peoplename']
                        context['created_at']     = created_at
                        context['tkt_assignedto'] = rec['assignedto']

                    html_message = render_to_string('autoclose_mail.html', context=context)
                    resp['story'] += f"context in email template is {context}\n"
                    msg.body = html_message
                    msg.send()
                    log.info(f"mail sent, record_id:{rec['id']}")
                update_job_autoclose_status(rec)
                
    except Exception as e:
        log.error(f'context in the template:{context}')
        log.error("something went wrong while running autoclose_job()", exc_info=True)
        resp['traceback'] += f"{tb.format_exc()}"
    return resp



def update_ticket_log(id, item, result):
    try:
        t = Ticket.objects.get(id=id)
        t.ticketlog['ticket_history'].append(item)
        t.save()
        result['story']+="ticketlog saved"
    except Exception as e:
        log.error("something went wron while saving ticketlog", exc_info=True)
        result['traceback'] = f"{tb.format_exc()}"
    return result

def send_escalation_ticket_email(tkt, result):
    #get records for email sending
    records = utils.runrawsql(get_query('ticketmail'), [tkt['id']])
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.core.mail import  EmailMessage
    try:
        for rec in records:
            subject = f"Escalation Level {rec['level']}: Ticket Number {rec['id']}"
            toemails = []
            if rec['creatorid'] != 1: toemails.append(rec['creatoremail'])
            if rec['modifierid'] != 1: toemails.append(rec['modifiermail'])
            if rec['assignedtopeople_id'] not in [1, None]: toemails.append(rec['peopleemail'])
            if rec['assignedtogroup_id'] not in [1, None]: toemails.append(rec['pgroupemail'])
            if rec['notify'] not in [1, None, ""]: toemails.append(rec['notifyemail'].replace(" ", ''))
            msg = EmailMessage()
            context = {
                'desc'       : rec['ticketdesc'],
                'template'   : rec['tescalationtemplate'],
                'priority'   : rec['priority'],
                'status'     : rec['status'],
                'createdon'  : str(rec['cdtz'] + timedelta(hours=5, minutes=30))[:19],
                'modifiedon' : str(rec['mdtz'] + timedelta(hours=5, minutes=30))[:19],
                'modifiedby' : rec['modifiername'],
                'assignedto' : str(rec["peoplename"]) if (rec["assignedtopeople_id"] not in [1, " ", None]) else str(rec["groupname"]),
                'comments'   : "NA" if rec["comments"] == '' else str(rec["comments"]),
                'isescalated': "True",
                'escdetails' : "NA" if rec["body"] == '' else str(rec["body"]),
                'escin'      : f'{rec["frequencyvalue"]} {rec["frequency"]}',
                'level'      : rec['level'],
                'next_esc'   : rec['next_escalation'],
                'subject'    : subject
            }
            html_message = render_to_string('ticket_email.html', context=context)
            msg.body = html_message
            msg.subject = subject
            msg.from_email = settings.EMAIL_HOST_USER
            msg.content_subtype = 'html'
            msg.to = toemails
            msg.send()
            log.info(f"mail sent, record_id:{rec['id']}")
    except Exception as e:
        log.error("something went wrong while sending escalation email", exc_info=True)
        result['traceback'] = tb.format_exc()
    return result
                
            
            
            


def update_ticket_data(tickets, result):
    from django.utils import timezone
    now = timezone.now().replace(microsecond=0, second=0)
    import json
    if tickets: result['story']+="updating ticket data started"
    for tkt in tickets:
        ic(tkt)
        #update tkt level, mdtz, modigiedon
        if tkt['escgrpid'] in [1, '1', None] and tkt['escpersonid'] in [1, '1', None]:
            assignedperson_id = tkt['assignedtopeople']
            assignedtogroup_id = tkt['assignedtogroup']
        else:
            assignedperson_id = tkt['escpersonid']
            assignedtogroup_id = tkt['escgrpid']
        ticketlog = json.loads(tkt['ticketlog'])
        history_item = {
            "people_id"     :tkt['cuser_id'],
            "when"          : str(now),
            "who"           : tkt['who'],
            "action"        : "created",
            "details"       : [f"Ticket is escalated from level {tkt['level']} to {tkt['level']+1}"],
            "previous_state": ticketlog['ticket_history'][-1]['previous_state'] if ticketlog['ticket_history'] else {},
        }

        if t := Ticket.objects.filter(id=tkt['id']).update(
            mdtz=tkt['exp_time'],
            modifieddatetime=tkt['exp_time'],
            level=tkt['level'] + 1,
            assignedtopeople_id=assignedperson_id,
            assignedtogroup_id=assignedtogroup_id,
            isescalated=True,
        ):
            
            result['story'] += f"ticket updated with these values mdtz & modifieddatetime \
            {tkt['exp_time']} {tkt['level'] = } {assignedperson_id = } {assignedtogroup_id = } level= {tkt['level']+1}"
            result = update_ticket_log(tkt['id'], history_item, result)
            result = send_escalation_ticket_email(tkt, result)
    return result
        



@shared_task(name="ticket_escalation")
def ticket_escalation():
    result = {}

    try:
        #get all records of tickets which can be escalated
        tickets = utils.runrawsql(get_query('get_ticketlist_for_escalation'))
        result['story'] = f"Total tickets found for escalation are {len(tickets)}\n"
        #update ticket_history, assignments to people & groups, level, mdtz, modifiedon
        result = update_ticket_data(tickets, result)
    except Exception as e:
        log.error("somwthing went wrong while ticket escalation", exc_info=True)
        result['traceback'] = tb.format_exc()
    return result
        