def get_object(uuid, model):
    try:
        return model.objects.get(uuid = uuid)
    except model.DoesNotExist as e:
        raise Exception from e
    
    
def save_jobneeddetails(data):
    import json
    jobneeddetails_post_data = json.loads(data['jobneeddetails'])
    

        
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
        #ic(path)
    except Exception:
        raise



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
from graphql import GraphQLError
from apps.core import utils
from .validators import clean_record
from apps.activity.models import (Job, Jobneed, JobneedDetails, Attachment, Asset)
import traceback as tb


def insertrecord_for_att(record, tablename):
    try:
        if model := get_model_or_form(tablename):
            record = clean_record(record)
            obj = model.objects.create(**record)
            return obj.id
        raise GraphQLError(Messages.IMPROPER_DATA)
    except Exception as e:
        raise e




def update_record(details, jobneed, Jn, Jnd):
    alerttype = 'OBSERVATION'
    record = clean_record(jobneed)
    #ic((record)
    try:
        with transaction.atomic(using=utils.get_current_db_name()):
            instance = Jn.objects.get(uuid = record['uuid'])
            jn_parent_serializer = sz.JobneedSerializer(data=record, instance=instance)
            if jn_parent_serializer.is_valid(): 
                isJnUpdated = jn_parent_serializer.save()
            else: log.error(f"something went wrong!\n{jn_parent_serializer.errors} ", exc_info=True )
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
            instance = Jnd.objects.get(uuid = record['uuid'])
            jnd_ser = sz.JndSerializers(data=record, instance=instance)
            if jnd_ser.is_valid(): jnd_ser.save()
            updated+=1
        if len(jobneeddetails) == updated: return True 




def save_parent_childs(sz, jn_parent_serializer, child, M):
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
                            ch_detail_serializer.save()
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



def perform_tasktourupdate(file, request):
    log.info("perform_tasktourupdate [start]")
    rc, recordcount, traceback= 0, 0, 'NA'
    instance, msg = None, ""

    try:
        data = get_json_data(file)
        #ic((data)
        for record in data:
            details = record.pop('details')
            jobneed = record
            with transaction.atomic(using=utils.get_current_db_name()):
                if updated :=  update_record(details, jobneed, Jobneed, JobneedDetails):
                    recordcount+=1
    
    except IntegrityError as e:
        log.error("Database Error", exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    
    except Exception as e:
        log.error('Something went wrong', exc_info=True)
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
    return ServiceOutputType(rc=rc, msg=msg, recordcount=recordcount, traceback=traceback)



def perform_insertrecord(file, request=None, filebased=True):
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
    from pprint import pformat
    try:
        data = get_json_data(file) if filebased else [file]
        #ic(data)
        try:
            with transaction.atomic(using=utils.get_current_db_name()):
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



def perform_reportmutation(file):
    rc, recordcount, traceback= 0, 0, 'NA'
    instance = None
    try:
        if data := get_json_data(file):
            for record in data:
                child = record.pop('child', None)
                parent = record
                try:
                    with transaction.atomic(using=utils.get_current_db_name()):
                        if child and len(child) > 0 and parent:
                            jobneed_parent_post_data = parent
                            jn_parent_serializer = sz.JobneedSerializer(data=clean_record(jobneed_parent_post_data))
                            rc,  traceback, msg = save_parent_childs(sz, jn_parent_serializer, child, Messages)
                            if rc == 0: recordcount+=1
                            #ic((recordcount)
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



def perform_adhocmutation(file):
    rc, recordcount, traceback, msg= 0, 0, 'NA', ""
    
    try:
        if data:= get_json_data(file):
            for record in data:
                details = record.pop('details')
                jobneedrecord = record
                with transaction.atomic(using = utils.get_current_db_name()):
                    if jobneedrecord['asset_id']==1:
                        #then it should be NEA
                        assetobjs = Asset.objects.filter(bu_id = jobneedrecord['bu_id'],
                                          assetcode = jobneedrecord['remarks'],
                                          )
                        jobneedrecord['asset_id']= 1 if assetobjs.count() !=1 else assetobjs[0].id
        else:
            raise utils.NoDataInTheFileError
            
    except utils.NoDataInTheFileError as e:
        rc, traceback = 1, tb.format_exc()
    except Exception as e:
        pass
    return ServiceOutputType(rc=rc, recordcount = recordcount, msg = msg, traceback = traceback)
    

        


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
            resp = insertrecord_for_att(record, tablename)
            rc, traceback, msg = 0, tb.format_exc(), Messages.UPLOAD_SUCCESS
            recordcount = 1
        from .tasks import perform_facerecognition
        results = perform_facerecognition.delay(pelogid, peopleid, resp, home_dir, uploadfile, db)
        log.warn(f"face recognition status {results.state}")
    except Exception as e:
        rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
        log.error('something went wrong', exc_info=True)
    return ServiceOutputType(rc=rc, recordcount = recordcount, msg = msg, traceback = traceback)


def getEmails(R):
    pass




def alert_observation(pk):
    body=""
    try:
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
                body+= "<table style='background:#EEF1F5;' cellpadding=8 cellspacing=2 border=1>"
                body+= "<tr style='background:#ABE7ED;font-weight:bold;font-size:14px;'><th>Slno</th><th>Question</th><th>Answer</th><th>Option</th><th>Min</th><th>Max</th><th>Alert On</th><tr>"
                for rd in enumerate(jndRecords):
                    body+= "<tr %s>"     %("style='color:red;'" if rd[1]["alerts"] == True else "")
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
            #TODO sendEmail()
            if jobneedRecord[0].iscritical:
                ticketdesc = f"[READINGS ALERT] {jobneedRecord[0].asset.identifier.taname}: [{jobneedRecord[0].asset.assetcode}]{jobneedRecord[0].asset.assetname} - readings out of range" 
                #TODO createTicket
                #TODO snedTicketEmail()
    except Exception as e:
        raise

    


def alert_report(pk):
    body=''
    try:
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
                body+= "<table style='background:#EEF1F5;' cellpadding=8 cellspacing=2 border=1>"
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
                    body+= "<tr {}>".format("style='color:red;'" if bd["alerts"] == True else "")
                    body+= f"<td>{bd['cseqno']}</td>"
                    body+= f"<td>{bd['questionname']}</td>"
                    body+= f"<td>{bd['answer']}</td>"
                    body+= f"<td>{bd['option']}</td>"
                    body+= f"<td>{bd['min']}</td>"
                    body+= f"<td>{bd['max']}</td>"
                    body+= f"<td>{bd['alerton']}</td>"
                    body+= "</tr>"
                    flag= False
                    del bd
                body+= "</table>"
                body+= "</td></tr></table>"
                #TODO send_emaill()
    except Exception as e:
        raise
                


def alert_deviation(pk):
    try:
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
            #TODO send_email()
    except Exception:
        raise