import graphene
from apps.core import utils
from apps.activity.models.job_model import Jobneed, JobneedDetails
from apps.activity.models.question_model import QuestionSetBelonging, QuestionSet, Question
from apps.activity.models.attachment_model import Attachment
from apps.activity.models.location_model import Location
from apps.work_order_management.models import Vendor, Approver, Wom
from apps.y_helpdesk.models import Ticket
from apps.onboarding.models import GeofenceMaster, DownTimeHistory,Shift
from apps.peoples.models import Pgbelonging, Pgroup, People
from apps.attendance.models import PeopleEventlog
from django.db import connections
from apps.work_order_management.utils import check_all_approved, reject_workpermit,check_all_verified
from collections import namedtuple
from logging import getLogger
from contextlib import closing
from django.utils import timezone
log = getLogger('mobile_service_log')
import json
from pprint import pformat
from .types import (VerifyClientOutput, DowntimeResponse,GetPdfUrl,
TypeAssist, SelectOutputType, BasicOutput)

class Query(graphene.ObjectType):
    
    get_locations = graphene.Field(SelectOutputType,
                                                mdtz = graphene.String(required = True),
                                                ctzoffset = graphene.Int(required = True),
                                                buid = graphene.Int(required = True))


    get_groupsmodifiedafter = graphene.Field(SelectOutputType, 
                                            mdtz = graphene.String(required = True),
                                            ctzoffset = graphene.Int(required = True),
                                            buid = graphene.Int(required = True))



    get_gfs_for_siteids = graphene.Field(SelectOutputType,
                                 siteids = graphene.List(graphene.Int))
    
    
    get_shifts = graphene.Field(SelectOutputType,
        mdtz = graphene.String(required=True),
        buid = graphene.Int(required = True),
        clientid = graphene.Int(required = True))
    

    getsitelist  = graphene.Field(SelectOutputType,
                                 clientid = graphene.Int(required = True),
                                 peopleid = graphene.Int(required = True))


    verifyclient = graphene.Field(VerifyClientOutput, clientcode = graphene.String(required = True))

    send_email_verification_link = graphene.Field(BasicOutput,
                                clientcode = graphene.String(required=True),
                                loginid = graphene.String(required=True)
                                )
    get_superadmin_message = graphene.Field(
        DowntimeResponse,
        client_id = graphene.Int(required=True)
    )
    get_site_visited_log = graphene.Field(SelectOutputType,
                                 clientid = graphene.Int(required = True),
                                 peopleid = graphene.Int(required = True),
                                 ctzoffset = graphene.Int(required=True))
    

    
    @staticmethod
    def resolve_send_email_verification_link(self, info, clientcode, loginid):
        user = People.objects.filter(loginid = loginid, client__bucode = clientcode).first()
        from django_email_verification import send_email
        try:
            if user:
                send_email(user, info.context)
                rc, msg = 0, "Success"
            else:
                rc, msg = 1, "Failed"
        except Exception as e:
            rc, msg = 1, "Failed"
            log.critical("something went wrong", exc_info=True)
        return BasicOutput(rc=rc, msg=msg, email = user.email)
        
    
    @staticmethod
    def resolve_get_locations(self, info, mdtz, ctzoffset, buid):
        log.info(f'\n\nrequest for location-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, clientid:{buid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = Location.objects.get_locations_modified_after(mdtzinput, buid, ctzoffset)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)


    @staticmethod
    def resolve_get_groupsmodifiedafter(self, info, mdtz, ctzoffset, buid):
        log.info(f'\n\nrequest for groups-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, buid:{buid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = Pgroup.objects.get_groups_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)


    @staticmethod
    def resolve_get_gfs_for_siteids(self, info, siteids):
        log.info(f'\n\nrequest for getgeofence inputs : siteids:{siteids}')
        data = GeofenceMaster.objects.get_gfs_for_siteids(siteids)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_getsitelist(self, info, clientid, peopleid):
        log.info(f'\n\nrequest for sitelis inputs : clientid:{clientid}, peopleid:{peopleid}')
        data = Pgbelonging.objects.get_assigned_sites_to_people(peopleid, forservice=True)
        #change bupreferences back to json
        for i in range(len(data)):
            data[i]['bupreferences'] = json.dumps(data[i]['bupreferences'])
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_verifyclient(self,info, clientcode):
        try:
            url = utils.get_appropriate_client_url(clientcode)
            if not url: raise ValueError
            return VerifyClientOutput(msg = "VALID", url=url)
        except ValueError as e:
            log.error(f"url not found for the specified {clientcode=}")
            return VerifyClientOutput(msg='INVALID', url=None, rc=1)
        except Exception as ex:
            log.critical("something went wrong!", exc_info=True)
            return VerifyClientOutput(msg='INVALID', url=None, rc=1)

    
    def resolve_get_shifts(self,info,buid,clientid,mdtz):
        log.info(f'request get shifts input are: {buid} {clientid}')
        data = Shift.objects.get_shift_data(buid,clientid,mdtz)
        print("Data: ",data,type(data))
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    
    def resolve_get_superadmin_message(self, info, client_id):
        log.info(f'resolve_get_superadmin_message {client_id = }')
        record = DownTimeHistory.objects.filter(client_id=client_id).values('reason', 'starttime', 'endtime').order_by('-cdtz').first()
        if timezone.now() < record['endtime']:
            return DowntimeResponse(
                message=record['reason'],
                startDateTime=record['starttime'],
                endDateTime = record['endtime'])
        else:
            return DowntimeResponse(
                message=""
            )
    def resolve_get_site_visited_log(self, info, clientid, peopleid, ctzoffset):
        log.info(f'resolve_get_sitevisited_log {clientid = } {peopleid = } {ctzoffset = }')
        data = PeopleEventlog.objects.get_sitevisited_log(clientid, peopleid, ctzoffset)
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)

def get_db_rows(sql, args=None):
    try:
        # Define the batch size for fetchmany
        batch_size = 100  # Adjust this based on your needs and memory constraints

        # Using context manager to handle the cursor
        with closing(connections[utils.get_current_db_name()].cursor()) as cursor:
            cursor.execute(sql, args)
            columns = [col[0] for col in cursor.description]
            RowType = namedtuple('Row', columns)

            # Initialize an empty list to collect all rows
            data = []
            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break
                data.extend([RowType(*row)._asdict() for row in batch])

        # Convert the list of dictionaries to JSON
        data_json = json.dumps(data, default=str)
        count = len(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(records=data_json, msg=f"Total {count} records fetched successfully!", nrows=count)
    except Exception as e:
        log.error("Failed to fetch data", exc_info=True)
        # Optionally re-raise or handle the error appropriately


def get_externaltouremodifiedafter(peopleid, siteid, clientid):
    return get_db_rows("select * from fun_getexttourjobneed(%s, %s, %s)", args=[peopleid, siteid, clientid])

def get_assetdetails(mdtz, buid):
    return get_db_rows("select * from fn_getassetdetails(%s, %s)", args=[mdtz, buid])
