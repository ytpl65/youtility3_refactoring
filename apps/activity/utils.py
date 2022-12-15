import apps.activity.models as av
from django.db.models import Value
from django.db.models.functions import Concat
from django.db.models import Q
import apps.peoples.utils as putils
import json
import logging
log = logging.getLogger("__main__")
from datetime import datetime
import pytz

def get_assetincludes_choices():
    qset = av.Asset.objects.filter(
         ~Q(assetcode='NONE'), identifier='CHECKPOINT', enable = True).select_related(
            'parent').annotate(
            checkpoint = Concat(
                'assetname', Value(" ("), 'assetcode', Value(")")))
    return qset.values_list('id', 'checkpoint')

def get_assetsmartplace_choices():
    qset = av.Asset.objects.filter(
         ~Q(assetcode='NONE') & Q(identifier='SMARTPLACE') | Q(identifier='ASSET'), enable = True).select_related(
            'parent').annotate(
            checkpoint = Concat(
                'assetname', Value(" ("), 'assetcode', Value(")")))
    return qset.values_list('id', 'checkpoint')


def initialize_alerton_field(val, choices = False):
    raise NotImplementedError()

def validate_alertbelow(forms, data):
    min, alertbelow = float(data['min']), float(data['alertbelow'])
    msg = 'Alert below should be greater than minimum value.'
    if alertbelow < min: raise forms.ValidationError(msg)
    return alertbelow

def validate_alertabove(forms, data):
    max, alertabove = float(data['max']), float(data['alertabove'])
    msg = 'Alert above should be smaller than maximum value.'
    if alertabove > max: raise forms.ValidationError(msg)
    print("utils", alertabove)
    return alertabove    

def validate_options(forms, val):
    try:
        obj = json.loads(val)
    except ValueError as e:
        return val
    options = [i['value'] for i in obj]
    return json.dumps(options).replace('"', "").replace("[", "").replace("]", "")

def validate_alerton(forms, val):
    ic('validate_alerton', val)
    v1          = val.replace("'", "")
    v2          = v1.replace("[", "")
    v3          = v2.replace("]", "")
    vlist       = v3.split(",")
    list_string = json.dumps(vlist)
    list        = json.loads(list_string)
    return json.dumps([each_string for each_string in list]).replace('"', "").replace("[", "").replace("]", "")

def initialize_alertbelow_alertabove(instance, form):
    alerton, below, above, li = instance.alerton, "", "", []
    print(alerton)
    if alerton and ('<' in alerton or '>' in alerton):
        s1 = alerton.replace(">", "")
        s2 = s1.replace(",", "")
        s3 = s2.replace("<", "")
        li = s3.split(" ")
        print(li)
        form.fields['alertbelow'].initial = float(li[0])
        form.fields['alertabove'].initial = float(li[1])

def init_assetincludes(form):
    form.fields['assetincludes'].initial = form.instance.assetincldes


def insert_questions_to_qsetblng(assigned_questions, model, fields, request):
    from django.db import transaction
    try:
        with transaction.atomic():
            ic(assigned_questions)
            for ques in assigned_questions:
                log.info(f"""{" " * 8} saving question {ques[1]} for QuestionSet {fields['qsetname']} [started]""")

                qsetbng, created = model.objects.update_or_create(
                    question_id = ques[2], qset_id = fields['qset'], client_id = fields['client'],
                    defaults = { 
                    "seqno"       : ques[0],
                    "question_id"   : ques[2],
                    "answertype"   : ques[3],
                    "min"         : float(ques[4]),
                    "max"         : float(ques[5]),
                    "options"     : ques[6].replace('"', '') if isinstance(ques[6], str) else "",
                    "alerton"     : ques[7].replace('"', '') if isinstance(ques[7], str) else "",
                    "ismandatory" : ques[8],
                    "isavpt" : ques[9],
                    "avpttype" : ques[10],
                    "qset_id"   : fields['qset']}
                )
                qsetbng.save()
                log.debug(f"{qsetbng.cuser}, {qsetbng.muser}, {qsetbng.cdtz}, {qsetbng.mdtz}")
                putils.save_userinfo(qsetbng, request.user, request.session)
                log.debug(f"""{" " * 8} {created} question {ques[1]} for QuestionSet {fields['qsetname']} [ended]""")

    except Exception:
        log.critical("something went wrong", exc_info = True)
        raise

def get_assignedsitedata(request):
    bu_list=[]
    from apps.onboarding.models import Bt
    try:
        data= Bt.objects.get_people_bu_list(request.user).values('id','bu','assignsites')
        print("get_assignedsitedata data", data)
        for x in data:
            print(x['assignsites'], x)
            bu_list.append(x['assignsites'])
        bu_list.append(request.user.bu_id)
        print("xxx", data.query ,bu_list)
    except Exception as e:
        log.error("get_assignedsitedata() exception: %s", (e))
        bu_list.append(request.user.bu_id)  
    return bu_list

def column_filter(col0, col1, col2, col3, col4,col5, colval0, colval1, colval2, colval3, colval4, colval5, start_utc):
    # sourcery skip: extract-duplicate-method, extract-method
    kwargs={}
    if colval0 !="" or colval1!="" or colval2 !="" or colval3!="" or colval4!="":
        print("1");
    if colval0 !="":
        val0 =colval0.split('(')[1].strip(')').strip()
        col0 = f'{col0}__icontains'
        kwargs[col0] = val0
    if colval2 !="":
        val2 =colval2.split('(')[1].strip(')').strip()
        print("ncal1",type(val2), val2)
        col2 = f'{col2}__icontains'
        kwargs[col2] = val2
    if colval3 !="":
        val3 =colval3.split('(')[1].strip(')').strip()
        col3 = f'{col3}__icontains'
        kwargs[col3] = val3
    if colval4 !="":
        val4 =colval4.split('(')[1].strip(')').strip()
        col4 = f'{col4}__icontains'
        kwargs[col4] = val4
    if colval5 !="":
        val5 =colval5.split('(')[1].strip(')').strip()
        col5 = f'{col5}__icontains'
        kwargs[col5] = val5    
    if colval1 !="":
        val1 =colval1.split('(')[1].strip(')').strip()
        if start_utc!='':
            val1 =val1.split('-')
            col1 = f'{col1}__range'
            mystr = ''.join(map(str, val1[1].strip())) + " 23:59"
            date_time_obj_start = datetime.strptime(val1[0].strip(), '%m/%d/%Y')
            date_time_obj_end = datetime.strptime(mystr, '%m/%d/%Y %H:%M')
            startdateobj= date_time_obj_start.astimezone(pytz.UTC).replace(microsecond=0)
            enddateobj= date_time_obj_end.astimezone(pytz.UTC).replace(microsecond=0)
            kwargs[col1] = [startdateobj, enddateobj]
        else:
            kwargs[col1] = val1
    return kwargs

def getdatatable_filter(request):
    print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
    col0= request.GET['columns[0][data]']
    col1= request.GET['columns[1][data]']
    col2= request.GET['columns[2][data]']
    col3= request.GET['columns[3][data]']
    col4= request.GET['columns[4][data]']
    col5= request.GET['columns[5][data]']
    colval0 =request.GET['columns[0][search][value]']
    colval1 =request.GET['columns[1][search][value]']
    colval2 =request.GET['columns[2][search][value]']
    colval3 =request.GET['columns[3][search][value]']
    colval4 =request.GET['columns[4][search][value]']
    colval5 =request.GET['columns[5][search][value]']
    length, start = int(request.GET['length']), int(request.GET['start'])
    return col0,col1,col2,col3,col4,col5,colval0,colval1,colval2,colval3,colval4, colval5,length,start



def datastatus(request, id_id):
    from datetime import datetime
    listObj = []
    for i in id_id.ticketlog['statusjbdata']:
        jsonelement= json.loads(i)
        if (jsonelement['performedby'] == jsonelement['assignedto']):
                print("@@@@@@@@@@@",jsonelement['performedby'],jsonelement['assignedto'])
                jsonelement['performedby']="You"
                jsonelement['assignedto']="Self"
        if (str(jsonelement['performedby'])== str(request.user)):  
            jsonelement['performedby']="You"
            print("yyyyyyyyyyyy", jsonelement['performedby'], request.user)
        x = jsonelement['datetime']
        date_time_obj = datetime.strptime(x, '%Y-%m-%d %H:%M:%S')
        jsonelement['datetime']=date_time_obj.strftime("%d %b %y %H:%M:%S")
        listObj.append(jsonelement)
    print("listObj",listObj)
    return listObj

def sendTicketMail(ticketid, oper):
    try:
        ticketdata = av.Ticket.objects.send_ticket_mail(ticketid)
        # print("ticketdata", ticketdata)
        records = [{'cdtz': record.createdon, 'ticketlog': record.ticketlog, 'modifiedon': record.modifiedon, 'status': record.status, 'ticketdesc': record.ticketdesc, 'ticketno': record.ticketno, 'creatoremail': record.creatoremail, 'modifiermail': record.modifiermail, 'modifiername': record.modifiername, 'peopleemail': record.peopleemail, 'pgroupemail': record.pgroupemail, 'tescalationtemplate': record.tescalationtemplate, 'priority': record.priority, 'peoplename': record.peoplename, 'next_escalation': record.next_escalation, 'creatorid': record.creatorid, 'modifierid': record.modifierid, 'assignedtopeople_id': record.assignedtopeople_id, 'assignedtogroup_id': record.assignedtogroup_id, 'groupname': record.groupname, 'buname': record.buname, 'level': record.level, 'comments':record.comments} for record in ticketdata]
        sendEscalationTicketMail(records, oper, 'WEB')
    except Exception as e:
        logger.error("sendTicketMail() exception: %s", e)
        

def savejsonbdata(request, id_id, asset, location):
    if str(id_id.assignedtogroup) != "NONE":
        assignedto = id_id.assignedtogroup
    elif str(id_id.assignedtopeople) != "NONE":
        assignedto = id_id.assignedtopeople
    ticketlog = {'performedby': id_id.performedby, 'status': id_id.status, 'datetime': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'comments': id_id.comments, 'assignedto': assignedto, 'asset': asset, 'location': location}

    id_id.ticketlog['statusjbdata'].append(json.dumps(ticketlog, default=str))
    return id_id

def increment_ticket_number():
    last_ticket = av.Ticket.objects.order_by('ticketno').last()
    if not last_ticket:
        return '1'
    print(last_ticket)
    last_id = last_ticket.ticketno
    return last_id +1

def converttodict(cursor,sqlquery):
    from collections import namedtuple
    records = []
    columns = rows =  record = None
    cursor.execute(sqlquery)
    rows    = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    for r in rows:
        record = namedtuple("Record", columns)
        records.append(dict(**dict(list(zip(columns, r)))))
    return records

def childlist_viewdata(request, hostname):
    from django.db import connections
    ticketno = request.GET['ticketno']
    column = request.GET.get('order[0][column]')
    print("childlist_viewdata column", column)
    columnname = request.GET.get(f'columns[{column}][data]')
    columnsort = request.GET.get('order[0][dir]')
    print("list_viewdata", columnname)
    length, start = int(request.GET['length']), int(request.GET['start'])
    with connections[hostname].cursor() as cursor: 
        cursor = connections[hostname].cursor()
        if columnsort != 'asc': 
            sqlquery = ticketevents_query(ticketno,columnsort,columnname)
            records = converttodict(cursor,sqlquery)
            print(' list_viwdata desccc')
        else: 
            sqlquery = ticketevents_query(ticketno,columnsort,columnname)
            records = converttodict(cursor,sqlquery)
    return records, length, start


def ticketevents_query(ticketno,columnsort,columnname):
    sqlquery =  """select  e.id as eid, d.devicename, d.ipaddress, ta.taname as type, e.source, e.cdtz, COUNT(att.id) AS attachment__count
                from 
                ( select id, bu_id, ticketno, events, unnest(string_to_array(events, ',')::bigint[])as eventid  from ticket where ticketno='%s' ) ticket 
                inner join event e on ticket.eventid = e.id	
                inner join typeassist ta on e.eventtype_id = ta.id 
                inner join device d on e.device_id = d.id 
                inner join attachment att on e.id = att.event_id
                inner join bt b on ticket.bu_id = b.id
                GROUP BY e.id, d.devicename, d.ipaddress, ta.taname ORDER BY %s %s  """ %(ticketno ,columnname, columnsort, )
    print("sqlqqqqqqqqqqqq", sqlquery)
    return sqlquery

def list_viewdata(request, model, fields, kwargs):
    column = request.GET.get('order[0][column]')
    columnname = request.GET.get(f'columns[{column}][data]')
    columnsort = request.GET.get('order[0][dir]')
    length, start = int(request.GET['length']), int(request.GET['start'])
    objects = model.objects.filter(bu=request.session['bu_id'],**kwargs).values(*fields)
    if columnsort != 'asc': 
        objects = objects.order_by(f'-{columnname}')
    else: objects = objects.order_by(columnname)
    count = objects.count()
    filtered = count
    jsondata = {'data': list(objects[start:start + length])}
    return  length, start, objects