import graphene
from apps.core import utils
from apps.activity.models import JobneedDetails, Question, QuestionSet, QuestionSetBelonging, Location, Attachment
from apps.work_order_management.models import Vendor
from apps.y_helpdesk.models import Ticket
from apps.onboarding.models import GeofenceMaster, Bt
from apps.peoples.models import Pgbelonging, Pgroup, People
from apps.attendance.models import PeopleEventlog
from django.db import connections
from django.db.models import Q
from collections import namedtuple
from logging import getLogger
log = getLogger('mobile_service_log')
import json
from .types import (VerifyClientOutput,
TypeAssist, SelectOutputType)

class Query(graphene.ObjectType):
    tadata = graphene.Field(SelectOutputType, keys = graphene.List(graphene.String, required = True))
    # tabyid = graphene.Field(TyType, id = graphene.String())
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

    get_qsetmodifiedafter = graphene.Field(SelectOutputType,
                                          mdtz = graphene.String(required = True),
                                          ctzoffset = graphene.Int(required = True),
                                          buid = graphene.Int(required = True))   

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

    get_attendance_history = graphene.Field(SelectOutputType,
                                            mdtz = graphene.String(required = True),
                                            ctzoffset = graphene.Int(required = True),
                                            peopleid = graphene.Int(required=True),
                                            buid = graphene.Int(required=True),
                                            clientid = graphene.Int(required=True),
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
    
    @staticmethod
    def resolve_tadata(self, info, keys, **kwargs):
        log.info('\n\nrequest for typeassist data...')
        
        data = TypeAssist.objects.values(*keys)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, ncols = len(keys), records = records,msg = msg)
    
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
    def resolve_get_qsetmodifiedafter(self, info, mdtz, ctzoffset, buid):
        log.info(f'\n\nrequest for qset-modified-after inputs : mdtz:{mdtz}, ctzoffset:{ctzoffset}, buid:{buid}')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = QuestionSet.objects.get_qset_modified_after(mdtzinput, buid)
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
            utils.set_db_for_router(clientcode.lower())
            bt = Bt.objects.get(bucode = clientcode.upper(), enable = True)
            return VerifyClientOutput(msg = "VALID", url = f'{clientcode.lower()}.youtility.in', client_id = bt.id)
        except utils.NoDbError as ex:
            try:
                utils.set_db_for_router('default')
                Bt.objects.get(bucode = clientcode.upper())
                return VerifyClientOutput(msg = "VALID", url = f'{clientcode.lower()}.youtility.in')
            except Bt.DoesNotExist as ex:
                return VerifyClientOutput(rc = 1, msg="INVALID")
        except Bt.DoesNotExist as ex:
            return VerifyClientOutput(rc = 1, msg="INVALID")
        
    
    def resolve_get_attendance_history(self, info, mdtz, peopleid, buid, clientid, ctzoffset):
        log.info(f'\n\nrequest for getgeofence inputs : {mdtz = }  {peopleid = } {buid = } { clientid = }')
        data = PeopleEventlog.objects.get_attendance_history(mdtz, peopleid, buid, clientid, ctzoffset)
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)
        
    def resolve_get_vendors(self, info, clientid, mdtz, buid, ctzoffset):
        log.info(f'\n\nrequest for get_vendors inputs :{clientid = } {mdtz = } {buid = } {ctzoffset = }')
        data = Vendor.objects.get_vendors_for_mobile(info.context, clientid, mdtz, buid, ctzoffset)
        records, count, msg = utils.get_select_output(data)
        log.info(f'total {count} objects returned')
        return SelectOutputType(nrows = count, records = records,msg = msg)


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
    ic(count)
    return SelectOutputType(records = data_json, msg = msg, nrows = count)

def get_jobneedmodifiedafter(peopleid, siteid, clientid):
    return get_db_rows("select * from fun_getjobneed(%s, %s, %s)", args=[peopleid, siteid, clientid])

def get_externaltouremodifiedafter(peopleid, siteid, clientid):
    return get_db_rows("select * from fun_getexttourjobneed(%s, %s, %s)", args=[peopleid, siteid, clientid])

def get_assetdetails(mdtz, buid):
    return get_db_rows("select * from fn_getassetdetails(%s, %s)", args=[mdtz, buid])
