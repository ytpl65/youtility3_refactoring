from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
import traceback
import apps.service.utils as sutils
from apps.activity.models import JobneedDetails
from .serializers import InsertSerializer, JndSerializers, JobneedSerializer
from .validators import clean_record
from apps.attendance.models import PeopleEventlog
from apps.activity.models import Jobneed, Attachment
from apps.service.serializers import Messages
from apps.core.utils import get_current_db_name
from logging import getLogger


log = getLogger('__main__')
# Create your views here.
A = {'rc':0, 'reason': 'OK', 'msg':None, 'errors':None, 'returnid':None}
def get_model(tablename):
    match tablename:
        case "peopleeventlog":
            return PeopleEventlog
        case 'jobneed':
            return  Jobneed
        case 'attachment':
            return Attachment
        case _:
            return None



def perform_insertrecord(data):
    import json
    service_insert = json.loads(data['service_insert'])
    record = service_insert['record']
    tablename = service_insert['tablename']

    try:
        ser = InsertSerializer(data=clean_record(service_insert))
        if ser.is_valid():
            log.info(ser.data)
            model = get_model(tablename)
            with transaction.atomic(using=get_current_db_name()):
                obj = model.objects.create(**ser.data['record'])
                A['msg'], A['returnid'] = Messages.INSERT_SUCCESS, obj.id
        else:
            log.error(ser.errors)
            A['errors']= ser.errors
            log.error(ser.errors, exc_info=True)
            raise Exception(Messages.IMPROPER_DATA)
    except Exception as e:
        log.error('something went wrong', exc_info=True)
        A['rc'], A['reason'], A['msg'] = 1, e, Messages.INSERT_FAILED   
    return Response(A)




def perform_task_tour_update(data):
    try:
        with transaction.atomic(using=get_current_db_name()):
            import json
            service_tasktourupdate      = json.loads(data['service_tasktourupdate'])
            jobneeddetails_post_data = json.loads(data['jobneeddetails'])
            object                   = sutils.get_object(service_tasktourupdate['uuid'], Jobneed)
            jobneed_serializer       = JobneedSerializer(instance=object, data=clean_record(service_tasktourupdate))

            if jobneed_serializer.is_valid():
                jobneedparent = jobneed_serializer.save()

                allsaved = 0
                for detail in jobneeddetails_post_data:
                    object = sutils.get_object(detail['uuid'], JobneedDetails)
                    jobneeddetails_serializer = JndSerializers(instance=object, data = clean_record(detail))

                    if jobneeddetails_serializer.is_valid() and detail['jobneed_id'] == jobneedparent.id:
                        jobneeddetails_serializer.save()
                        allsaved+=1
                    else:
                        A['errors'], A['msg'], A['rc'] = jobneeddetails_serializer.errors, Messages.UPDATE_FAILED, 1
                        break
                if allsaved == len(jobneeddetails_post_data):
                    A['msg'] = Messages.UPDATE_SUCCESS
            else:
                A['errors'], A['msg'], A['rc'] = jobneed_serializer.errors, Messages.UPDATE_FAILED, 1
    except Exception as e:
        log.error('something went wrong', exc_info=True)
        A['rc'], A['reason'], A['msg'] = 1, traceback.format_exc(), Messages.UPDATE_FAILED
    return Response(A)



def perform_template_report_insert(data):
    import json
    service_templatereport = json.loads(data['service_templatereport'])
    child = service_templatereport.pop('child', None)
    parent = service_templatereport or None
    try:
        with transaction.atomic(using=get_current_db_name()):

            if child and len(child) > 0 and parent:
                jobneed_parent_post_data = parent
                jn_parent_serializer = JobneedSerializer(data=clean_record(jobneed_parent_post_data))

                if jn_parent_serializer.is_valid():
                    parent = jn_parent_serializer.save()
                    allsaved=0
                    for ch in child:
                        details = ch.pop('details')
                        ch.update({'parent_id':parent.id})
                        child_serializer = JobneedSerializer(data=clean_record(ch))

                        if child_serializer.is_valid():
                            child_instance = child_serializer.save()
                            for dtl in details:
                                dtl.update({'jobneed_id':child_instance.id})
                                ch_detail_serializer = JndSerializers(data=clean_record(dtl))
                                if ch_detail_serializer.is_valid():
                                   ch_detail_serializer.save()
                                else:
                                    log.error(ch_detail_serializer.errors)
                                    A['errors'], A['msg'], A['rc'] = ch_detail_serializer.errors, Messages.INSERT_FAILED, 1
                            allsaved+=1
                        else:
                            log.error(child_serializer.errors)
                            A['errors'], A['msg'], A['rc'] = child_serializer.errors, Messages.INSERT_FAILED, 1
                    if allsaved == len(child):
                        A['msg'], A['returnid'] = Messages.INSERT_SUCCESS, parent.id
                        A['reason'] = A['errors'] = None
                else:
                    log.error(jn_parent_serializer.errors)
                    A['errors'], A['msg'], A['rc'] = jn_parent_serializer.errors, Messages.INSERT_FAILED, 1
            else:
                log.error(Messages.NODETAILS)
                A['reason'], A['rc'] = Messages.NODETAILS, 1
    except Exception as e:
        A['msg'], A['reason'], A['rc'] = Messages.INSERT_FAILED, traceback.format_exc(), 1
        log.error('something went wrong', exc_info=True)
    return Response(A)


def perform_attachment_upload(request):
    import os
    try:
        log.info("perform_attachment_upload called")
        import json
        service_uploadattachment = json.loads(request.data['service_uploadattachment'])
        service_insert = json.loads(request.data['service_insert'])
        ic(service_uploadattachment, service_insert)
        file_buffer     = request.FILES.getlist('image')
        home_dir        = os.path.expanduser('~')+'/'
        attachment_data = service_uploadattachment
        pelogid         = attachment_data['pelog_id']
        peopleid        = attachment_data['people_id']
        filename        = attachment_data['filename']
        path            = attachment_data['path']
        filepath        = home_dir + path
        uploadfile      = f'{filepath}/{filename}'

        iscreated = sutils.get_or_create_dir(filepath)
        log.info(f'filepath is {iscreated}')
        sutils.write_file_to_dir(file_buffer, uploadfile)
        resp = perform_insertrecord(request.data)
        ic(resp.data)
        A['msg'] = f'Attachment {Messages.INSERT_SUCCESS}'
        A['errors'] = A['reason'] = None
        A['rc'] = 0
        if pelogid!=1:
            if ATT := Attachment.objects.get_attachment_record(resp.data['returnid']):
                if PEOPLE_ATT := PeopleEventlog.objects.get_people_attachment(pelogid):
                    ic(ATT.ownername_id, PEOPLE_ATT.people_id)
                    if PEOPLE_PIC := Attachment.objects.get_people_pic(ATT.ownername_id, PEOPLE_ATT.people_id):
                        default_image_path = PEOPLE_PIC.default_img_path
                        default_image_path = home_dir + default_image_path
                        from deepface import DeepFace
                        fr_results = DeepFace.verify(img1_path = default_image_path, img2_path = uploadfile)
                        PeopleEventlog.objects.update_fr_results(fr_results, pelogid, peopleid)
                        A['msg'] = f"""Face Recognition {"passed" if fr_results['verified'] else 'failed'}"""
                        A['errors'] = A['reason'] = None
                        A['rc'] = 0
                        ic(A)
    except Exception as e:
        A['rc'], A['reason'], A['msg'] = 1, traceback.format_exc(), Messages.UPLOAD_FAILED
        log.error('something went wrong', exc_info=True)
    return Response(A)


class InsertRecord(APIView):
    """
    Inserts record in given table after validations
    """
    def post(self, request, format=None):
        ic(request.data)
        return perform_insertrecord(request.data)




class TaskTourUpdate(APIView):
    """
    Updates Task Tour activities
    """
    def post(self, request, format=None):
        return perform_task_tour_update(request.data)


class TemplateReports(APIView):

    def post(self, request, format=None):
        ic(request.data)
        return perform_template_report_insert(request.data)



class AttachmentUpload(APIView):
    """
    Compares uploaded & default image of people
    and save the uploaded file in filesystem db
    Perform fr based attendance.
    """

    def post(self, request, format=None):
        return perform_attachment_upload(request)



def alert_observation(pkid, event):
    pass



class TestLoginREquired(APIView):
    """
    Updates Task Tour activities
    """
    def get(self, request, format=None):
        return Response(data={"text": "Helloworld"})
