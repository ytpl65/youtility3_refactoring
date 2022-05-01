from typing import Type
from charset_normalizer import from_path
import graphene
from apps.core import utils
from django.db import connections
from collections import namedtuple
from apps.activity.models import Asset, Jobneed, JobneedDetails, Question, QuestionSet, QuestionSetBelonging
from apps.peoples.models import Pgbelonging, Pgroup, People
from .types import (PeopleType,QSetType, QuestionType, QSetBlngType,PgBlngType,
TyType, TypeAssist, AssetType, JobneedMdtzAfter, JndType, PgroupType, SelectOutputType)


class Query(graphene.ObjectType):
    tadata = graphene.Field(SelectOutputType, keys = graphene.List(graphene.String, required=True))
    #tabyid = graphene.Field(TyType, id = graphene.String())
    get_assetdetails = graphene.Field(SelectOutputType, mdtz = graphene.String(required=True),
                                            buid = graphene.Int(required=True),)
    
    get_jobneedmodifiedafter = graphene.Field(SelectOutputType,
                                             peopleid = graphene.Int(required=True),
                                             buid = graphene.Int(required=True))
    
    get_jndmodifiedafter = graphene.Field(SelectOutputType,
                                         mdtz = graphene.String(required=True),
                                         jobneedids = graphene.String(required=True))
    
    get_typeassistmodifiedafter = graphene.Field(SelectOutputType,
                                                mdtz = graphene.String(required=True),
                                                clientid = graphene.Int(required=True))
    
    get_peoplemodifiedafter = graphene.Field(SelectOutputType,
                                            mdtz = graphene.String(required=True),
                                            buid = graphene.Int(required=True),)

    get_groupsmodifiedafter = graphene.Field(SelectOutputType, 
                                            mdtz = graphene.String(required=True),
                                            buid = graphene.Int(required=True))

    get_questionsmodifiedafter = graphene.Field(SelectOutputType, 
                                               mdtz=graphene.String(required=True))

    get_qsetmodifiedafter = graphene.Field(SelectOutputType,
                                          mdtz = graphene.String(required=True),
                                          buid = graphene.Int(required=True))   
    
    get_qsetbelongingmodifiedafter = graphene.Field(SelectOutputType,
                                          mdtz = graphene.String(required=True),
                                          buid = graphene.Int(required=True))
    
    get_pgbelongingmodifiedafter = graphene.Field(SelectOutputType,
                                          mdtz = graphene.String(required=True),
                                          buid = graphene.Int(required=True),
                                          peopleid = graphene.Int(required=True))
    
    

    def resolve_tadata(self, info, keys, **kwargs):
        data = TypeAssist.objects.values(*keys)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, ncols = len(keys), records = records,msg = msg)
        
    
    def resolve_tabyid(self, info, id):
        ta = TypeAssist.objects.raw(f"select * from typeassist where id = {id}")
        return ta[0] if ta else None
    
    
    def resolve_get_assetdetails(self, info, mdtz, buid):
        import json
        data =  Asset.objects.get_assetdetails(mdtz, buid)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    
    def resolve_get_jobneedmodifiedafter(self, info, peopleid, buid):
        return get_jobneedmodifiedafter(peopleid, buid)


    def resolve_get_jndmodifiedafter(self, info, mdtz, jobneedids):
        data = JobneedDetails.objects.get_jndmodifiedafter(mdtz, jobneedids)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    
    def resolve_get_typeassistmodifiedafter(self, info, mdtz, clientid):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        ic(mdtzinput)
        data = TypeAssist.objects.get_typeassist_modified_after(mdtzinput, clientid)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    def resolve_get_peoplemodifiedafter(self, info, mdtz, buid):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        data = People.objects.get_people_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, records = records,msg = msg)
        
        
    def resolve_get_groupsmodifiedafter(self, info, mdtz, buid):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        data = Pgroup.objects.get_groups_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, records = records,msg = msg)
        
        
    def resolve_get_questionsmodifiedafter(self, info, mdtz):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        data =  Question.objects.get_questions_modified_after(mdtz)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    
    def resolve_get_qsetmodifiedafter(self, info, mdtz, buid):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        data = QuestionSet.objects.get_qset_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, records = records,msg = msg)
        
    
    
    def resolve_get_qsetbelongingmodifiedafter(self, info, mdtz, buid):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        data = QuestionSetBelonging.objects.get_modified_after(mdtzinput, buid)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    
    def resolve_get_pgbelongingmodifiedafter(self, info, mdtz, buid, peopleid):
        from datetime import datetime
        mdtzinput = datetime.strptime(mdtz, "%Y-%m-%d %H:%M:%S")
        data = Pgbelonging.objects.get_modified_after(mdtzinput, peopleid, buid)
        records, count, msg = utils.get_select_output(data)
        return SelectOutputType(nrows = count, records = records,msg = msg)
    
    
    
def get_db_rows(sql, args=None):
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
    data_json = json.dumps(data, default=str)
    msg = f"Total {len(data)} records fetched successfully!"
    count = len(data)
    return SelectOutputType(records=data_json, msg=msg, nrows = count)

def get_jobneedmodifiedafter(peopleid, siteid):
    return get_db_rows("select * from fun_getjobneed(%s, %s)", args=[peopleid, siteid])