import graphene
from apps.core import utils
from apps.activity.models import JobneedDetails, Question, QuestionSet, QuestionSetBelonging, Location, Attachment
from apps.work_order_management.models import Vendor, Approver, Wom
from apps.y_helpdesk.models import Ticket
from apps.onboarding.models import GeofenceMaster, Bt, DownTimeHistory
from apps.peoples.models import Pgbelonging, Pgroup, People
from apps.attendance.models import PeopleEventlog
from django.db import connections
from django.db.models import Q
from apps.work_order_management.utils import check_all_approved, reject_workpermit
from collections import namedtuple
from logging import getLogger
from datetime import datetime, timedelta
from django.utils import timezone
log = getLogger('mobile_service_log')
import json
from .types import (VerifyClientOutput, DowntimeResponse,
TypeAssist, SelectOutputType, BasicOutput)

class Query(graphene.ObjectType):
    tadata = graphene.Field(SelectOutputType, keys = graphene.List(graphene.String, required = True))
    
    get_assetdetails = graphene.Field(SelectOutputType,
                                      mdtz = graphene.String(required = True),
                                      ctzoffset = graphene.Int(required = True),
                                      buid = graphene.Int(required = True),)

    get_jobneedmodifiedafter = graphene.Field(SelectOutputType,
                                             peopleid = graphene.Int(required = True),
                                             buid = graphene.Int(required = True),
                                             clientid = graphene.Int(required = True))
    
    get_externaltourmodifiedafter = graphene.Field(SelectOutputType,
                                             peopleid = graphene.Int(required = True),
                                             buid = graphene.Int(required = True),
                                             clientid = graphene.Int(required = True))

    get_jndmodifiedafter = graphene.Field(SelectOutputType,
                                         ctzoffset = graphene.Int(required = True),
                                         jobneedids = graphene.String(required = True))

    get_typeassistmodifiedafter = graphene.Field(SelectOutputType,
                                                mdtz = graphene.String(required = True),
                                                ctzoffset = graphene.Int(required = True),
                                                clientid = graphene.Int(required = True))
    
    get_locations = graphene.Field(SelectOutputType,
                                                mdtz = graphene.String(required = True),
                                                ctzoffset = graphene.Int(required = True),
                                                buid = graphene.Int(required = True))

    get_peoplemodifiedafter = graphene.Field(SelectOutputType,
                                            mdtz = graphene.String(required = True),
                                            ctzoffset = graphene.Int(required = True),
                                            buid = graphene.Int(required = True),)

    get_groupsmodifiedafter = graphene.Field(SelectOutputType, 
                                            mdtz = graphene.String(required = True),
                                            ctzoffset = graphene.Int(required = True),
                                            buid = graphene.Int(required = True))

    get_questionsmodifiedafter = graphene.Field(SelectOutputType, 
                                               mdtz = graphene.String(required = True),
                                               ctzoffset = graphene.Int(required = True))

    get_people_event_log_punch_ins = graphene.Field(SelectOutputType,
                                                    datefor = graphene.String(required=True),
                                                    buid = graphene.Int(required=True),
                                                    peopleid = graphene.Int(required=True))

    get_qsetmodifiedafter = graphene.Field(SelectOutputType,
                                          mdtz = graphene.String(required = True),
                                          ctzoffset = graphene.Int(required = True),
                                          buid = graphene.Int(required = True),
                                          clientid = graphene.Int(required=True))   

    get_qsetbelongingmodifiedafter = graphene.Field(SelectOutputType,
                                          mdtz = graphene.String(required = True),
                                          ctzoffset = graphene.Int(required = True),
                                          buid = graphene.Int(required = True))

    get_pgbelongingmodifiedafter = graphene.Field(SelectOutputType,
                                          mdtz = graphene.String(required = True),
                                          ctzoffset = graphene.Int(required = True),
                                          buid = graphene.Int(required = True),
                                          peopleid = graphene.Int(required = True))

    get_gfs_for_siteids = graphene.Field(SelectOutputType,
                                 siteids = graphene.List(graphene.Int))
    
    get_approvers = graphene.Field(
        SelectOutputType,
        buid = graphene.Int(required = True),
        clientid = graphene.Int(required = True),
    )

    get_peopleeventlog_history = graphene.Field(
        SelectOutputType,
        fromdate = graphene.String(required=True),
        todate = graphene.String(required=True),
                                            ctzoffset=graphene.Int(required=True),
                                            peopleid=graphene.Int(required=True),
                                            buid=graphene.Int(required=True),
                                            clientid=graphene.Int(required=True),
                                            peventtypeid=graphene.Int(required=True),
            
                                            )
    getsitelist  = graphene.Field(SelectOutputType,
                                 clientid = graphene.Int(required = True),
                                 peopleid = graphene.Int(required = True))
    
    get_tickets = graphene.Field(SelectOutputType,
                                 peopleid = graphene.Int(required=True),
                                 ctzoffset = graphene.Int(required=True),
                                 buid = graphene.Int(),
                                 clientid = graphene.Int(),
                                 mdtz = graphene.String(required=True))
    
    get_attachments = graphene.Field(SelectOutputType, 
                                     owner = graphene.String(required=True))

    verifyclient = graphene.Field(VerifyClientOutput, clientcode = graphene.String(required = True))

    checkquery = graphene.Field(VerifyClientOutput)
    
    get_vendors = graphene.Field(SelectOutputType,
                                 clientid = graphene.Int(required=True),
                                 mdtz = graphene.String(required=True),
                                 buid = graphene.Int(required=True),
                                 ctzoffset = graphene.Int(required=True))
    
    get_wom_records = graphene.Field(SelectOutputType,
                                workpermit = graphene.String(required=True),
                                peopleid = graphene.Int(required=True),
                                 buid = graphene.Int(),
                                 parentid = graphene.Int(),
                                 clientid = graphene.Int(),
                                 fromdate = graphene.String(required=True),
        todate = graphene.String(required=True),
                                     )

    approve_workpermit = graphene.Field(SelectOutputType,
                                wom_uuid = graphene.String(required=True),
                                peopleid = graphene.Int(required=True),
                                        )
    reject_workpermit = graphene.Field(SelectOutputType,
                                wom_uuid = graphene.String(required=True),
                                peopleid = graphene.Int(required=True),
                                        )
    
    send_email_verification_link = graphene.Field(BasicOutput,
                                clientcode = graphene.String(required=True),
                                loginid = graphene.String(required=True)
                                )
    get_superadmin_message = graphene.Field(
        DowntimeResponse,
        client_id = graphene.Int(required=True)
    )
    
    
    @staticmethod
    def resolve_send_email_verification_link(self, info, clientcode, loginid):
        user = People.objects.filter(loginid = loginid, client__bucode = clientcode).first()
        from django_email_verification import send_email
        try:
            send_email(user, info.context)
            rc, msg = 0, "Success"
        except Exception as e:
            rc, msg = 1, "Failed"
            log.critical("something went wrong", exc_info=True)
        return BasicOutput(rc=rc, msg=msg, email = user.email)
    
    @staticmethod
    def resolve_tadata(self, info, keys, **kwargs):
        log.info('\n\nrequest for typeassist data...')
        data = TypeAssist.objects.values(*keys)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, ncols = len(keys), records = records,msg = msg)
    
    @staticmethod
    def resolve_approve_workpermit(self, info, wom_uuid, peopleid):
        log.info("request for change wom status")
        log.info(f"inputs are {wom_uuid = } {peopleid = }")
        try:
            p = People.objects.filter(id = peopleid).first()
            if is_all_approved := check_all_approved(wom_uuid, p.peoplecode):
                    updated = Wom.objects.filter(uuid=wom_uuid).update(workpermit=Wom.WorkPermitStatus.APPROVED.value)
            rc, msg = 0, "success"
        except Exception as e:
            log.critical("something went wrong!", exc_info=True)
            rc, msg = 1, "failed"
        return BasicOutput(rc=rc, msg=msg)
    
    @staticmethod
    def resolve_reject_workpermit(self, info, wom_uuid, peopleid):
        try:
            p = People.objects.filter(id=peopleid).first()
            #w = Wom.objects.filter(id=id).first()
            Wom.objects.filter(uuid=wom_uuid).update(workpermit=Wom.WorkPermitStatus.REJECTED.value)
            reject_workpermit(wom_uuid, p.peoplecode)
            rc, msg = 0, "success"
        except Exception as e:
            log.critical("something went wrong", exc_info=True)
            rc, msg = 1, "failed"
        return BasicOutput(rc=rc, msg=msg)
        
        
    @staticmethod
    def resolve_get_tickets(self, info, peopleid, ctzoffset, buid, clientid, mdtz):
        log.info('request for get_tickets')
        data = Ticket.objects.get_tickets_for_mob(peopleid, buid, clientid, mdtz, ctzoffset)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count,  records = records,msg = msg)
    
    @staticmethod
    def resolve_checkquery(self, info):
        msg="vaishu is bitch"
        return VerifyClientOutput(msg = msg)
    
    def resolve_get_attachments(self, info, owner):
        log.info("request for attachments")
        data = Attachment.objects.get_attachements_for_mob(owner)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count,  records = records,msg = msg)
    
    @staticmethod
    def resolve_tabyid(self, info, id):
        log.info('\n\nrequest for typeassist data...')
        ta = TypeAssist.objects.raw("select * from typeassist where id = %s", [id])
        return ta[0] if ta else None

    @staticmethod
    def resolve_get_assetdetails(self, info, mdtz, ctzoffset, buid):
        mdtz = utils.getawaredatetime(mdtz, ctzoffset)
        log.info(f'\n\nrequest for assetdetails data...inputs: mdtz:{mdtz}, ctzoffset:{ctzoffset}, buid:{buid}')
        return get_assetdetails(mdtz, buid)

    @staticmethod
    def resolve_get_jobneedmodifiedafter(self, info, peopleid, buid, clientid):
        log.info(f'\n\nrequest for jobneed-modified-after inputs: peopleid:{peopleid}, buid:{buid}, clientid:{clientid}')
        return get_jobneedmodifiedafter(peopleid, buid, clientid)
    
    @staticmethod
    def resolve_get_externaltourmodifiedafter(self, info, peopleid, buid, clientid):
        log.info(f'\n\nrequest for exttour-jobneed-modified-after inputs : peopleid:{peopleid}, buid:{buid}, clientid:{clientid}')
        return get_externaltouremodifiedafter(peopleid, buid, clientid)

    @staticmethod
    def resolve_get_jndmodifiedafter(self, info, ctzoffset, jobneedids):
        log.info(f'\n\nrequest for jndmodifiedafter inputs : ctzoffset:{ctzoffset}, jobneedids:{jobneedids}')
        data = JobneedDetails.objects.get_jndmodifiedafter(jobneedids)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_typeassistmodifiedafter(self, info, mdtz, ctzoffset, clientid):
        log.info(f'\n\nrequest for typeassist-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, clientid:{clientid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = TypeAssist.objects.get_typeassist_modified_after(mdtzinput, clientid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    @staticmethod
    def resolve_get_locations(self, info, mdtz, ctzoffset, buid):
        log.info(f'\n\nrequest for location-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, clientid:{buid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = Location.objects.get_locations_modified_after(mdtzinput, buid, ctzoffset)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_peoplemodifiedafter(self, info, mdtz, ctzoffset, buid):
        log.info(f'\n\nrequest for people-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, buid:{buid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = People.objects.get_people_modified_after(mdtzinput, buid)
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
    def resolve_get_questionsmodifiedafter(self, info, mdtz, ctzoffset):
        log.info(f'\n\nrequest for questions-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data =  Question.objects.get_questions_modified_after(mdtz)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_qsetmodifiedafter(self, info, mdtz, ctzoffset, buid, clientid):
        log.info(f'\n\nrequest for qset-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, buid:{buid} , clientid: {clientid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = QuestionSet.objects.get_qset_modified_after(mdtzinput, buid, clientid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)


    @staticmethod
    def resolve_get_qsetbelongingmodifiedafter(self, info, mdtz, ctzoffset, buid):
        log.info(f'\n\nrequest for qsetbelonging-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, buid:{buid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = QuestionSetBelonging.objects.get_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_pgbelongingmodifiedafter(self, info, mdtz, ctzoffset, buid, peopleid):
        log.info(f'\n\nrequest for pgbelonging-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, buid:{buid}, peopleid:{peopleid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = Pgbelonging.objects.get_modified_after(mdtzinput, peopleid, buid)
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
        log.info(f'data:{data}')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_verifyclient(self,info, clientcode):
        try:
            url = utils.get_appropriate_client_url(clientcode)
            if not url: raise Exception
            return VerifyClientOutput(msg = "VALID", url=url)
        except Exception as ex:
            log.critical("something went wrong!", exc_info=True)
            return VerifyClientOutput(msg='INVALID', url=None, rc=1)
        
        
    
    def resolve_get_peopleeventlog_history(self, info, fromdate, todate, peopleid, buid, clientid, ctzoffset, peventtypeid):
        log.info(f'\n\nrequest for getgeofence inputs : {fromdate = } {todate=} {peopleid = } {buid = } { clientid = }')
        data = PeopleEventlog.objects.get_peopleeventlog_history(fromdate, todate, peopleid, buid, clientid, ctzoffset, peventtypeid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)
        
    def resolve_get_vendors(self, info, clientid, mdtz, buid, ctzoffset):
        log.info(f'\n\nrequest for get_vendors inputs :{clientid = } {mdtz = } {buid = } {ctzoffset = }')
        data = Vendor.objects.get_vendors_for_mobile(info.context, clientid, mdtz, buid, ctzoffset)
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    def resolve_get_people_event_log_punch_ins(self, info, datefor,  buid, peopleid):
        log.info(f'request get_people_event_log_punch_ins inputs are : {datefor = }  {buid = } {peopleid = }')
        data = PeopleEventlog.objects.get_people_event_log_punch_ins(datefor,  buid, peopleid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    def resolve_get_approvers(self, info, buid, clientid):
        log.info(f'request get_approvers inputs are : {buid = } {clientid = }')
        data = Approver.objects.get_approver_list_for_mobile(buid, clientid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    def resolve_get_wom_records(self, info, fromdate, todate, peopleid, workpermit, buid, clientid, parentid):
        log.info(f'request get_approvers inputs are : {buid = } {clientid = } {peopleid = } {parentid = } {workpermit = } {fromdate = } {todate = }')
        data = Wom.objects.get_wom_records_for_mobile(fromdate, todate, peopleid, workpermit, buid, clientid, parentid)
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

def get_db_rows(sql, args = None):
    import json
    cursor = connections[utils.get_current_db_name()].cursor()

    cursor.execute(sql, args)
    print(dir(cursor))
    columns = [col[0] for col in cursor.description]
    type_filter = ([desc[1] for desc in cursor.description])
    RowType = namedtuple('Row', columns)
    data = [
        RowType(*row)._asdict()
        for row in cursor.fetchall() ]

    cursor.close()
    data_json = json.dumps(data, default = str)
    msg = f"Total {len(data)} records fetched successfully!"
    count = len(data)
    log.info(f'{count} objects returned...')
    for rec in data:
        ic(rec['id'])
    return SelectOutputType(records = data_json, msg = msg, nrows = count)

def get_jobneedmodifiedafter(peopleid, siteid, clientid):
    return get_db_rows("select * from fun_getjobneed(%s, %s, %s)", args=[peopleid, siteid, clientid])

def get_externaltouremodifiedafter(peopleid, siteid, clientid):
    return get_db_rows("select * from fun_getexttourjobneed(%s, %s, %s)", args=[peopleid, siteid, clientid])

def get_assetdetails(mdtz, buid):
    return get_db_rows("select * from fn_getassetdetails(%s, %s)", args=[mdtz, buid])
