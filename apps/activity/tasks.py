# import string
# from apps.activity.models import Jobneed, JobneedDetails
# from django.contrib.auth.models import User
# from django.utils.crypto import get_random_string
# from celery.utils.log import get_task_logger
# log = get_task_logger(__name__)
# from api.types import ServiceOutputType
# from django.db import transaction
# from apps.core import utils
# from intelliwiz_config.celery import app
# from django.db.utils import IntegrityError
# from api import serializers as sz
# from api.validators import clean_record
# from pprint import pformat
# import traceback as tb
# from api.tasks import Messages, get_json_data, get_model_or_form

# @app.task(bind = True, default_retry_delay = 300, max_retries = 5)
# def create_random_user_accounts(total):
#     for _ in range(total):
#         print("task execution started...")
#         username = f'user_{get_random_string(10, string.ascii_letters)}'
#         email = f'{username}@example.com'
#         password = get_random_string(50)
#         User.objects.create_user(username = username, email = email, password = password)
#     return f'{total} random users created with success!'

# @app.task(bind = True, default_retry_delay = 300, max_retries = 5)
# def add(self, x, y):
#     import time
#     time.sleep(10)
#     return x+y

# @app.task(bind = True, default_retry_delay = 300, max_retries = 5)
# def perform_facerecognition_bgt(self, pelogid, peopleid, ownerid, home_dir, uploadfile, db='default'):
#     from apps.activity.models import Attachment
#     from apps.attendance.models import PeopleEventlog
#     from django.db import transaction
#     from apps.core import utils

#     log.info("perform_facerecognition ...start [+]")
#     log.info(f'parameters are {pelogid} {peopleid} {ownerid} {type(ownerid)} {home_dir} {uploadfile}')
#     try:
#         with transaction.atomic(using = utils.get_current_db_name()):
#             if pelogid !=  1:
#                 if ATT := Attachment.objects.get_attachment_record(ownerid, db):
#                     if PEOPLE_ATT := PeopleEventlog.objects.get_people_attachment(pelogid, db):
#                         if PEOPLE_PIC := Attachment.objects.get_people_pic(ATT.ownername_id, PEOPLE_ATT.uuid, db):
#                             default_image_path = PEOPLE_PIC.default_img_path
#                             default_image_path = home_dir + default_image_path
#                             from deepface import DeepFace
#                             fr_results = DeepFace.verify(img1_path = default_image_path, img2_path = uploadfile)
#                             PeopleEventlog.objects.update_fr_results(fr_results, pelogid, peopleid, db)
#     except ValueError as v:
#         log.error("face recogntion failed", exc_info = True)
#     except Exception as e:
#         log.error("something went wrong!", exc_info = True)
#         self.retry(e)
#         raise

# @app.task(bind = True, default_retry_delay = 300, max_retries = 5)  
# def perform_insertrecord_bgt(file, tablename, request = None, filebased = True, db='default'):
#     """
#     Insert records in specified tablename.

#     Args:
#         file (file|json): file object| json data
#         tablename (str): name of table
#         request (http wsgi request, optional): request object. Defaults to None.
#         filebased (bool, optional): type of data, file (True) or json (False) Defaults to True.

#     Returns:
#         ServiceOutputType: rc, recordcount, msg, traceback
#     """    
#     log.info('perform_insertrecord [start]')
#     rc, recordcount, traceback= 0, 0, 'NA'
#     instance = None
#     try:
#         if filebased:
#             data = get_json_data(file)
#             model = get_model_or_form(tablename)
#         else:
#             data = [file]
#         # ic(data)
#         model = get_model_or_form(tablename)
#         try:
#             with transaction.atomic(using = utils.get_current_db_name()):
#                 for record in data:
#                     record = clean_record(record)
#                     log.info(f'record after cleaning {pformat(record)}')
#                     instance = model.objects.create(**record).using(db)
#                     recordcount += 1
#         except Exception:
#             raise
#         if recordcount:
#             msg = Messages.INSERT_SUCCESS
#     except Exception as e:
#         log.error("something went wrong!", exc_info = True)
#         msg, rc, traceback = Messages.INSERT_FAILED, 1, tb.format_exc()
#     return  ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)

# @app.task(bind = True, default_retry_delay = 300, max_retries = 5)
# def perform_tasktourupdate_bgt(file, request, db='default'):
#     log.info("perform_tasktourupdate [start]")
#     rc, recordcount, traceback= 0, 0, 'NA'
#     instance, msg = None, ""

#     try:
#         data = get_json_data(file)
#         # ic(data)
#         for record in data:
#             details = record.pop('details')
#             jobneed = record
#             with transaction.atomic(using = utils.get_current_db_name()):
#                 if updated :=  update_record(details, jobneed, Jobneed, JobneedDetails, db):
#                     recordcount += 1

#     except IntegrityError as e:
#         log.error("Database Error", exc_info = True)
#         rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED

#     except Exception as e:
#         log.error('Something went wrong', exc_info = True)
#         rc, traceback, msg = 1, tb.format_exc(), Messages.UPLOAD_FAILED
#     return ServiceOutputType(rc = rc, msg = msg, recordcount = recordcount, traceback = traceback)

# def update_record(details, jobneed, Jn, Jnd, db):
#     alerttype = 'OBSERVATION'
#     record = clean_record(jobneed)
#     # ic(record)
#     try:
#         with transaction.atomic(using = utils.get_current_db_name()):
#             instance = Jn.objects.get(uuid = record['uuid'])
#             jn_parent_serializer = sz.JobneedSerializer(data = record, instance = instance)
#             if jn_parent_serializer.is_valid(): 
#                 isJnUpdated = jn_parent_serializer.save(using = db)
#             else: log.error(f"something went wrong!\n{jn_parent_serializer.errors} ", exc_info = True )
#             isJndUpdated = update_jobneeddetails(details, Jnd, db)
#             if isJnUpdated and  isJndUpdated:
#                 # utils.alert_email(input.jobneedid, alerttype)# # 
#                 #TODO send observation email
#                 #TODO send deviation mail
#                 return True
#     except Exception:
#         raise

# def update_jobneeddetails(jobneeddetails, Jnd, db):
#     if jobneeddetails:
#         updated = 0
#         for detail in jobneeddetails:
#             record = clean_record(detail)
#             instance = Jnd.objects.get(uuid = record['uuid'])
#             jnd_ser = sz.JndSerializers(data = record, instance = instance)
#             if jnd_ser.is_valid(): jnd_ser.save(using = db)
#             updated += 1
#         if len(jobneeddetails) == updated: return True 

# @app.task(bind = True, default_retry_delay = 300, max_retries = 5)
# def perform_reportmutation_bgt(file, db='default'):
#     rc, recordcount, traceback= 0, 0, 'NA'
#     instance = None
#     try:
#         if data := get_json_data(file):
#             for record in data:
#                 child = record.pop('child', None)
#                 parent = record
#                 try:
#                     with transaction.atomic(using = utils.get_current_db_name()):
#                         if child and len(child) > 0 and parent:
#                             jobneed_parent_post_data = parent
#                             jn_parent_serializer = sz.JobneedSerializer(data = clean_record(jobneed_parent_post_data))
#                             rc,  traceback, msg = save_parent_childs(sz, jn_parent_serializer, child, Messages, db)
#                             if rc == 0: recordcount += 1
#                             # ic(recordcount)
#                         else:
#                             log.error(Messages.NODETAILS)
#                             msg, rc = Messages.NODETAILS, 1
#                 except Exception as e:
#                     log.error('something went wrong', exc_info = True)
#                     raise
#     except Exception as e:
#         msg, traceback, rc = Messages.INSERT_FAILED, tb.format_exc(), 1
#         log.error('something went wrong', exc_info = True)
#     return ServiceOutputType(rc = rc, recordcount = recordcount, msg = msg, traceback = traceback)



# def save_parent_childs(sz, jn_parent_serializer, child, M, db):
#     log.info("save_parent_childs ............start")
#     try:
#         rc,  traceback= 0,  'NA'
#         instance = None
#         if jn_parent_serializer.is_valid():
#             parent = jn_parent_serializer.save(using = db)
#             allsaved = 0
#             for ch in child:
#                 # ic(ch, type(child))
#                 details = ch.pop('details')
#                 # ic(details, type(details))
#                 ch.update({'parent_id':parent.id})
#                 child_serializer = sz.JobneedSerializer(data = clean_record(ch))

#                 if child_serializer.is_valid():
#                     child_instance = child_serializer.save(using = db)
#                     for dtl in details:
#                         # ic(dtl, type(dtl))
#                         dtl.update({'jobneed_id':child_instance.id})
#                         ch_detail_serializer = sz.JndSerializers(data = clean_record(dtl))
#                         if ch_detail_serializer.is_valid():
#                             ch_detail_serializer.save(using = db)
#                         else:
#                             log.error(ch_detail_serializer.errors)
#                             traceback, msg, rc = str(ch_detail_serializer.errors), M.INSERT_FAILED, 1
#                     allsaved += 1
#                 else:
#                     log.error(child_serializer.errors)
#                     traceback, msg, rc = str(child_serializer.errors), M.INSERT_FAILED, 1
#             if allsaved == len(child):
#                 msg= M.INSERT_SUCCESS
#         else:
#             log.error(jn_parent_serializer.errors)
#             traceback, msg, rc = str(jn_parent_serializer.errors), M.INSERT_FAILED, 1
#         log.info("save_parent_childs ............end")
#         return rc, traceback, msg
#     except Exception:
#         log.error("something went wrong",exc_info = True)
#         raise
