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


from pprint import pformat

from apps.attendance.models import PeopleEventlog
from .tasks import Messages
from .tasks import (
    get_json_data, get_model_or_form,
    get_or_create_dir)
from django.db import transaction
from logging import getLogger
log = getLogger('__main__')
from .types import ServiceOutputType
from django.db.utils import IntegrityError
from apps.service import serializers as sz
from apps.core import utils
from .validators import clean_record
from apps.activity.models import (Jobneed, JobneedDetails, Asset)
import traceback as tb

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



def update_record(details, jobneed, Jn, Jnd):
    alerttype = 'OBSERVATION'
    record = clean_record(jobneed)
    # ic((record)
    try:
        with transaction.atomic(using = utils.get_current_db_name()):
            instance = Jn.objects.get(uuid = record['uuid'])
            jn_parent_serializer = sz.JobneedSerializer(data = record, instance = instance)
            if jn_parent_serializer.is_valid():
                isJnUpdated = jn_parent_serializer.save()
            else: log.error(f"something went wrong!\n{jn_parent_serializer.errors} ", exc_info = True )
            isJndUpdated = update_jobneeddetails(details, Jnd)
            if isJnUpdated and  isJndUpdated:
                # utils.alert_email(input.jobneedid, alerttype)
                # TODO send observation email
                # TODO send deviation mail
                return True
    except Exception:
        log.error("update_record failed", exc_info = True)
        raise
    return False



def update_jobneeddetails(jobneeddetails, Jnd):
    if jobneeddetails:
        updated = 0
        for detail in jobneeddetails:
            record = clean_record(detail)
            instance = Jnd.objects.get(uuid = record['uuid'])
            jnd_ser = sz.JndSerializers(data = record, instance = instance)
            if jnd_ser.is_valid(): jnd_ser.save()
            updated += 1
        if len(jobneeddetails) == updated: return True 



def save_parent_childs(sz, jn_parent_serializer, child, M):
    log.info("save_parent_childs ............start")
    try:
        rc,  traceback= 0,  'NA'
        instance = None
        if jn_parent_serializer.is_valid():
            parent = jn_parent_serializer.save()
            allsaved = 0
            for ch in child:
                # ic((ch, type(child))
                details = ch.pop('details')
                # ic((details, type(details))
                ch.update({'parent_id':parent.id})
                child_serializer = sz.JobneedSerializer(data = clean_record(ch))

                if child_serializer.is_valid():
                    child_instance = child_serializer.save()
                    for dtl in details:
                        # ic((dtl, type(dtl))
                        dtl.update({'jobneed_id':child_instance.id})
                        ch_detail_serializer = sz.JndSerializers(data = clean_record(dtl))
                        if ch_detail_serializer.is_valid():
                            ch_detail_serializer.save()
                        else:
                            log.error(ch_detail_serializer.errors)
                            traceback, msg, rc = str(ch_detail_serializer.errors), M.INSERT_FAILED, 1
                    allsaved += 1
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
        log.error("something went wrong",exc_info = True)
        raise


def perform_tasktourupdate(file, request):
    log.info("perform_tasktourupdate [start]")
    rc, recordcount, traceback= 0, 0, 'NA'
    instance, msg = None, ""

    try:
        data = get_json_data(file)
        ic(data)
        for record in data:
            details = record.pop('details')
            jobneed = record
            with transaction.atomic(using = utils.get_current_db_name()):
                if updated :=  update_record(details, jobneed, Jobneed, JobneedDetails):
                    recordcount += 1

    except IntegrityError as e:
        log.error("Database Error", exc_info = True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED

    except Exception as e:
        log.error('Something went wrong', exc_info = True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    return ServiceOutputType(rc = rc, msg = msg, recordcount = recordcount, traceback = traceback)


def perform_insertrecord(file, request = None, filebased = True):
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
    rc, recordcount, traceback= 0, 0, 'NA'
    instance = None
    try:
        data = get_json_data(file) if filebased else [file]
        # ic(data)
        with transaction.atomic(using = utils.get_current_db_name()):

            for record in data:
                tablename = record.pop('tablename')
                ic(tablename)
                obj = insertrecord(record, tablename)
                ic(obj)
                allconditions = [
                    hasattr(obj, 'peventtype'), hasattr(obj, 'endlocation'), 
                    hasattr(obj, 'punchintime'), hasattr(obj, 'punchouttime')]

                if all(allconditions) and all([tablename == 'peopleeventlog',
                        obj.peventtype.tacode in ('CONVEYANCE', 'AUDIT'),
                        obj.endlocation,obj.punchouttime, obj.punchintime]):
                    log.info("save line string is started")
                    save_linestring_and_update_pelrecord(obj)

                # model = get_model_or_form(tablename)

                # log.info(f'record after cleaning {pformat(record)}')
                # instance = model.objects.create(**record)
                recordcount += 1
        if recordcount:
            msg = Messages.INSERT_SUCCESS
    except Exception as e:
        log.error("something went wrong!", exc_info = True)
        msg, rc, traceback = Messages.INSERT_FAILED, 1, tb.format_exc()
    return  ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)

def save_linestring_and_update_pelrecord(obj):
    from apps.attendance.models import Tracking
    from django.contrib.gis.geos import LineString
    try:

        bet_objs = Tracking.objects.filter(reference = obj.uuid)
        line = [[coord for coord in obj.gpslocation] for obj in bet_objs]
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


def perform_reportmutation(file):
    rc, recordcount, traceback= 0, 0, 'NA'
    instance = None
    try:
        if data := get_json_data(file):
            for record in data:
                child = record.pop('child', None)
                parent = record
                try:
                    with transaction.atomic(using = utils.get_current_db_name()):
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
                    log.error('something went wrong', exc_info = True)
                    raise
    except Exception as e:
        msg, traceback, rc = Messages.INSERT_FAILED, tb.format_exc(), 1
        log.error('something went wrong', exc_info = True)
    return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)


def perform_adhocmutation(file):  # sourcery skip: remove-empty-nested-block, remove-redundant-if, remove-redundant-pass
    rc, recordcount, traceback, msg= 0, 0, 'NA', ""
    try:
        if not (data := get_json_data(file)):
            raise utils.NoDataInTheFileError

        db = utils.get_current_db_name()
        log.info(f"{len(data)} Number of records found in the file")
        for record in data:
            details = record.pop('details')
            jobneedrecord = record
            ic(details)
            ic(jobneedrecord)

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


def update_adhoc_record(scheduletask, jobneedrecord, details):
    rc, recordcount, traceback, msg= 0, 0, 'NA', ""
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
    recordcount += 1
    msg = "Scheduled Record (ADHOC) updated successfully!"
    return rc, traceback, msg, recordcount

def insert_adhoc_record(jobneedrecord, details):
    rc, recordcount, traceback, msg= 0, 0, 'NA', ""
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
    else:
        rc, traceback = 1, jnsz.errors
    return rc, traceback, msg, recordcount

def perform_uploadattachment(file,  record, biodata):
    rc, traceback, resp = 0,  'NA', 0
    recordcount = msg = None
    ic(biodata)
    # ic(file, tablename, record, type(record), biodata, type(biodata))
    try:
        log.info("perform_uploadattachment [start+########################]")
        import os

        file_buffer = file
        filename    = biodata['filename']
        peloguuid   = biodata['pelog_id']
        peopleid    = biodata['people_id']
        path        = biodata['path']
        home_dir    = '/var/www/redmine.youtility.in'+'/'
        filepath    = home_dir + path
        uploadfile  = f'{filepath}/{filename}'
        db          = utils.get_current_db_name()
        
        log.info(f"file_buffer: '{file_buffer}' \npelogid: '{peloguuid}' \npeopleid: '{peopleid}' \npath: {path} home_dir: '{home_dir}' \nfilepath: '{filepath}' \nuploadfile: '{uploadfile}'")
        
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
        obj = insertrecord(record, 'attachment')
        log.info(f'Attachment record inserted: {obj.filepath}')
        pel = PeopleEventlog.objects.get(uuid=peloguuid)
        log.info(f'Event Type: {pel.peventtype.tacode}')
        if pel.peventtype.tacode in ['SELF', 'MARK']:
            from .tasks import perform_facerecognition_bgt
            results = perform_facerecognition_bgt.delay(peloguuid, peopleid, obj.owner, home_dir, uploadfile, db)
            log.warning(f"face recognition status {results.state}")
    except Exception as e:
        log.error('something went wrong while performing face recognition', exc_info = True)
    return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)

def getEmails(R):
    raise NotImplementedError()

def getjobneedrecord():
    raise NotImplementedError()

def send_alert_mails_if_any(attdata):
    getjobneedrecord()
    pass

def alert_observation(pk):
    body=""
    jobneedRecord = Jobneed.objects.get_jobneed_observation(pk)
    log.info(f'jobneedRecord {"Found" if jobneedRecord.count() else "Not found"}')
    if jobneedRecord:
        toemails = getEmails(jobneedRecord[0])
        subject= f"[READINGS ALERT] Site: {jobneedRecord[0].bu.buname}, {jobneedRecord[0].asset.identifier.taname}: [{jobneedRecord[0].asset.assetcode}] {jobneedRecord[0].asset.assetname} - readings out of range"
        if jndRecords := JobneedDetails.objects.get_jnd_observation(jobneedRecord[0].id):
            tdStyle = "width='120' style='background:#abe7ed;font-weight:bold;font-size:16px'"
            body+= "<br><b>Some readings were out of permissible limits. Details are below...</b><br/><br/>"
            body+= "<table style='background:#eef1f5' cellpadding='8' cellspacing='2'>"
            body += f'<tr><td {tdStyle}>Site</td><td>{jndRecords[0]["buname"]}</td></tr>'
            body += f'<tr><td {tdStyle}>{jndRecords[0]["asset_identifier"]}</td><td>[{jndRecords[0]["assetcode"]}] {jndRecords[0]["assetname"]}</td></tr>'

            body += f'<tr><td {tdStyle}>Performed by</td><td>[{jndRecords[0]["peoplecode"]}] {jndRecords[0]["peoplename"]}</td></tr>'

            body+= "<tr><td colspan= 2>"
            body+= "<table style='background:#EEF1F5;' cellpadding = 8 cellspacing = 2 border = 1>"
            body+= "<tr style='background:#ABE7ED;font-weight:bold;font-size:14px;'><th>Slno</th><th>Question</th><th>Answer</th><th>Option</th><th>Min</th><th>Max</th><th>Alert On</th><tr>"
            for rd in enumerate(jndRecords):
                body+= "<tr %s>"     %("style='color:red;'" if rd[1]["alerts"] is True else "")
                body += f"<td>{rd.seqno}</td>"
                body += f"<td>{rd.questionname}</td>"
                body += f"<td>{rd.answer}</td>"
                body += f"<td>{rd.option}</td>"
                body += f"<td>{rd.min}</td>"
                body += f"<td>{rd.max}</td>"
                body += f"<td>{rd.alerton}</td>"
                body+= "</tr>"
            body+= "</table>"
            body+= "</td></tr></table>"
        log.info(f'alert_observation body {body}')
        # TODO sendEmail()
        if jobneedRecord[0].iscritical:
            ticketdesc = f"[READINGS ALERT] {jobneedRecord[0].asset.identifier.taname}: [{jobneedRecord[0].asset.assetcode}]{jobneedRecord[0].asset.assetname} - readings out of range" 
            # TODO createTicket
            # TODO snedTicketEmail()



def alert_report(pk):
    body=''
    hdata = Jobneed.objects.get_jobneed_for_report(pk)
    if len(hdata) >0:
        bdata = Jobneed.objects.get_hdata_for_report(pk)
        if len(bdata) >0:
            subject= f"[{hdata[0].idenfiername} ALERT] Site: {hdata[0].buname} | {hdata[0].jobdesc} - audit responses out of range"
            tdstyle = "width='120' style='background:#abe7ed;font-weight:bold;font-size:16px'"
            body += "<br><b>Some audit responses were out of permissible limits. Details are below...</b><br/><br/>"
            body += "<table style='background:#eef1f5' cellpadding='8' cellspacing='2'>"
            body+= f"<tr><td {tdstyle}>Site</td><td>{hdata[0].buname}</td></tr>"
            body+= f"<tr><td {tdstyle}>{hdata[0].identifiername}</td><td>{hdata[0].jobdesc}</td></tr>"
            body+= f"<tr><td {tdstyle}>Surveyor</td><td>[{hdata[0].peoplename}] {hdata[0].peoplename}</td></tr>"
            body+= f"<tr><td {tdstyle}>Datetime</td><td>{hdata[0].cplandatetime} (24Hr)</td></tr>"
            body+= "<tr><td colspan= 2>"
            body+= "<table style='background:#EEF1F5;' cellpadding = 8 cellspacing = 2 border = 1>"
            body += "<tr style='background:#ABE7ED;font-weight:bold;font-size:14px;'><th>Slno</th><th>Question</th><th>Answer</th><th>Option</th><th>Min</th><th>Max</th><th>Alert On</th></tr>"

            toemails = getEmails(hdata[0])
            prevsec= ""
            flag= False
            for bd in bdata:
                if prevsec == "" or prevsec != bd["jobdesc"]:
                    prevsec= bd["jobdesc"]
                    flag= True
                if flag:
                    body+= "<tr style='background: #F0F0F0;font-weight:bold;font-size:14px;'><td colspan='7'>[%s] %s</td></tr>" %(bd["pseqno"], bd["jobdesc"])
                body+= "<tr {}>".format("style='color:red;'" if bd["alerts"] is True else "")
                body+= f"<td>{bd['cseqno']}</td>"
                body+= f"<td>{bd['questionname']}</td>"
                body+= f"<td>{bd['answer']}</td>"
                body+= f"<td>{bd['option']}</td>"
                body+= f"<td>{bd['min']}</td>"
                body+= f"<td>{bd['max']}</td>"
                body+= f"<td>{bd['alerton']}</td>"
                body+= "</tr>"
                flag= False
            body+= "</table>"
            body+= "</td></tr></table>"
            # TODO send_emaill()


def alert_deviation(pk):
    R = Jobneed.objects.get_deviation_jn(pk)
    if R.count() > 0:
        toemails = getEmails(R)
        subject =  f"[DEVIATION ALERT] Route Deviation by Patrol Officer [{R[0].peoplename}]"
        body = f'<br><b>There has been a Route Deviation by Patrol Officer {R[0].peoplename} at {R[0].plandatetime} (24Hrs) to {R[0].assetname} </b><br/>'
        body+= "<br>Given below are details of the Patrol Officer.<br/><br/>"
        body+= "<table style='background:#eef1f5' cellpadding='8' cellspacing='2'>"
        tdstyle = "width='120' style='background:#abe7ed;font-weight:bold;font-size:16px"
        body+= f"<tr><td {tdstyle}>Description</td><td>%s</td></tr>"
        body+= f"<tr><td {tdstyle}>Planned On</td><td>%s</td></tr>"
        body+= f"<tr><td {tdstyle}>Performed On</td><td>%s</td></tr>"
        body+= f"<tr><td {tdstyle}>Checkpoint</td><td>%s</td></tr>"
        body+= f"<tr><td {tdstyle}>Code</td><td>%s</td></tr>"
        body+= f"<tr><td {tdstyle}>Name</td><td>%s</td></tr>"
        body+= f"<tr><td {tdstyle}>Mobile</td><td>%s</td></tr>"
        body+= "</table>"
        # TODO send_email()
