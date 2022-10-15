import graphene
from apps.core import utils
from apps.activity.models import JobneedDetails, Question, QuestionSet, QuestionSetBelonging
from apps.onboarding.models import GeofenceMaster, Bt
from apps.peoples.models import Pgbelonging, Pgroup, People
from django.db import connections
from collections import namedtuple
from logging import getLogger
log = getLogger('__main__')
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
                                         mdtz = graphene.String(required = True),
                                         ctzoffset = graphene.Int(required = True),
                                         jobneedids = graphene.String(required = True))

    get_typeassistmodifiedafter = graphene.Field(SelectOutputType,
                                                mdtz = graphene.String(required = True),
                                                ctzoffset = graphene.Int(required = True),
                                                clientid = graphene.Int(required = True))

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

    getsitelist  = graphene.Field(SelectOutputType,
                                 clientid = graphene.Int(required = True),
                                 peopleid = graphene.Int(required = True))

    verifyclient = graphene.Field(VerifyClientOutput, clientcode = graphene.String(required = True))

    checkquery = graphene.Field(VerifyClientOutput)
    
    @staticmethod
    def resolve_tadata(self, info, keys, **kwargs):
        log.info('request for typeassist data...')
        data = TypeAssist.objects.values(*keys)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, ncols = len(keys), records = records,msg = msg)
    
    @staticmethod
    def resolve_checkquery(self, info):
        msg="vaishu is bitch"
        return VerifyClientOutput(msg = msg)

    @staticmethod
    def resolve_tabyid(self, info, id):
        log.info('request for typeassist data...')
        ta = TypeAssist.objects.raw("select * from typeassist where id = %s", [id])
        return ta[0] if ta else None

    @staticmethod
    def resolve_get_assetdetails(self, info, mdtz, ctzoffset, buid):
        mdtz = utils.getawaredatetime(mdtz, ctzoffset)
        log.info('request for assetdetails data...')
        return get_assetdetails(mdtz, buid)

    @staticmethod
    def resolve_get_jobneedmodifiedafter(self, info, peopleid, buid, clientid):
        log.info('request for jobneed-modified-after data...')
        return get_jobneedmodifiedafter(peopleid, buid, clientid)
    
    @staticmethod
    def resolve_get_externaltourmodifiedafter(self, info, peopleid, buid, clientid):
        log.info('request for exttour-jobneed-modified-after data...')
        return get_externaltouremodifiedafter(peopleid, buid, clientid)

    @staticmethod
    def resolve_get_jndmodifiedafter(self, info, mdtz, ctzoffset, jobneedids):
        log.info('request for jndmodifiedafter data...')
        mdtz = utils.getawaredatetime(mdtz, ctzoffset)
        data = JobneedDetails.objects.get_jndmodifiedafter(mdtz, jobneedids)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_typeassistmodifiedafter(self, info, mdtz, ctzoffset, clientid):
        log.info('request for typeassist-modified-after data...')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        ic(mdtzinput)
        data = TypeAssist.objects.get_typeassist_modified_after(mdtzinput, clientid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        ic(records)
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_peoplemodifiedafter(self, info, mdtz, ctzoffset, buid):
        log.info('request for people-modified-after data...')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = People.objects.get_people_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        ic(records)
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_groupsmodifiedafter(self, info, mdtz, ctzoffset, buid):
        log.info('request for groups-modified-after data...')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = Pgroup.objects.get_groups_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        ic(records)
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_questionsmodifiedafter(self, info, mdtz, ctzoffset):
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data =  Question.objects.get_questions_modified_after(mdtz)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_qsetmodifiedafter(self, info, mdtz, ctzoffset, buid):
        log.info('request for qset-modified-after data...')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = QuestionSet.objects.get_qset_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        ic(records)
        return SelectOutputType(nrows = count, records = records,msg = msg)


    @staticmethod
    def resolve_get_qsetbelongingmodifiedafter(self, info, mdtz, ctzoffset, buid):
        log.info('request for qsetbelonging-modified-after data...')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = QuestionSetBelonging.objects.get_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_pgbelongingmodifiedafter(self, info, mdtz, ctzoffset, buid, peopleid):
        log.info('request for pgbelonging-modified-after data...')
        mdtzinput = utils.getawaredatetime(mdtz, ctzoffset)
        data = Pgbelonging.objects.get_modified_after(mdtzinput, peopleid, buid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_get_gfs_for_siteids(self, info, siteids):
        log.info('request for getgeofence...')
        data = GeofenceMaster.objects.get_gfs_for_siteids(siteids)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_getsitelist(self, info, clientid, peopleid):
        log.info('request for sitelist..')
        data = Bt.objects.getsitelist(clientid, peopleid)
        records, count, msg = utils.get_select_output(data)
        log.info(f'{count} objects returned...')
        return SelectOutputType(nrows = count, records = records,msg = msg)

    @staticmethod
    def resolve_verifyclient(self,info, clientcode):
        print("function started")
        ic(clientcode)
        try:
            utils.set_db_for_router(clientcode.lower())
            Bt.objects.get(bucode = clientcode.upper(), enable = True)
            return VerifyClientOutput(msg = "VALID", url = f'{clientcode.lower()}.youtility.in')
        except utils.NoDbError as ex:
            try:
                utils.set_db_for_router('default')
                Bt.objects.get(bucode = clientcode.upper())
                return VerifyClientOutput(msg = "VALID", url = f'{clientcode.lower()}.youtility.in')
            except Bt.DoesNotExist as ex:
                return VerifyClientOutput(rc = 1, msg="INVALID")
        except Bt.DoesNotExist as ex:
            return VerifyClientOutput(rc = 1, msg="INVALID")


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
    log.info('request for jobneed-modified-after data...')
    return get_db_rows("select * from fun_getjobneed(%s, %s, %s)", args=[peopleid, siteid, clientid])

def get_externaltouremodifiedafter(peopleid, siteid, clientid):
    log.info('request for exttour-jobneed-modified-after data...')
    return get_db_rows("select * from fun_getexttourjobneed(%s, %s, %s)", args=[peopleid, siteid, clientid])

def get_assetdetails(mdtz, buid):
    log.info('request for assetdetails-modified-after data...')
    qset =  get_db_rows("select * from fn_getassetdetails(%s, %s)", args=[mdtz, buid])
    ic(qset)
    return qset