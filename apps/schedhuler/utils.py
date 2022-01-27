import dataclasses
from django.db.models import Q
import apps.activity.models as am
from apps.tenants.middlewares import get_current_db_name
from django.core.exceptions import EmptyResultSet
from django.db import transaction
from logging import getLogger
from pprint import pformat
import apps.peoples.utils as putils
import apps.onboarding.utils as obutils
from datetime import datetime, timezone, timedelta
log = getLogger('__main__')

def create_job(jobs=None):
    startdtz = enddtz = msg = None
    F, d = {}, []
    with transaction.atomic(using=get_current_db_name()):
        if not jobs:
            jobs = am.Job.objects.filter(
                ~Q(jobname='NONE'),
                ~Q(assetid__runningstatus='SCRAPPED'),
                parent_id=1,
            ).select_related(
                "assetid", "groupid",
                "cuser", "muser", "qsetid", "peopleid",
            ).values_list(named=True)
        if not jobs:
            msg = "No jobs found schedhuling terminated"
            log.warn("%s" % (msg), exc_info=True)
            raise EmptyResultSet
        total_jobs = len(jobs)
        if total_jobs > 0 or jobs != None:
            log.info("processing jobs started found:= '%s' jobs" % (len(jobs)))
            for idx, job in enumerate(jobs):
                startdtz, enddtz = calculate_startdtz_enddtz(job)
                DT, is_cron = get_datetime_list(job.cron, startdtz, enddtz)
                F[str(job.id)] = is_cron
                status = insert_into_jn_and_jnd(job, DT)
                d.append({
                    "jobid"   : job.id,
                    "jobname" : job.jobname,
                    "cron"    : job.cron,
                    "iscron"  : is_cron,
                    "count"   : len(DT),
                    "status"  : status
                })
            if F:
                log.info("create_job() Failed job schedule list:= %s" %
                         (pformat(F)))
            log.info("createJob()[end-] [%s of %s] parent job:= %s | jobid:= %s | cron:= %s" %
                     (idx, (total_jobs - 1), job.jobname, job.id, job.cron))


def display_jobs_date_info(cdtz, mdtz, from_date, upto_date, ldtz):
    padd = "#"*8
    log.info("%s display_jobs_date_info [start] %s" % (padd, padd))
    log.info("created-on:= [%s] modified-on:=[%s]" % (cdtz, mdtz))
    log.info("valid-from:= [%s] valid-upto:=[%s]" %
             (from_date, upto_date))
    log.info("before lastgeneratedon:= [%s]" % (ldtz))
    log.info("%s display_jobs_date_info [end] %s" % (padd, padd))
    del padd
    


def calculate_startdtz_enddtz(job):
    log.info("calculating startdtz, enddtz for jobid:= [%s]" % (job.id))
    tzoffset     = job.ctzoffset 
    cdtz         = job.cdtz.replace(microsecond=0) + timedelta(minutes=tzoffset)
    mdtz         = job.mdtz.replace(microsecond=0)  + timedelta(minutes=tzoffset)
    vfrom        = job.from_date.replace(microsecond=0)  + timedelta(minutes=tzoffset)
    vupto        = job.upto_date.replace(microsecond=0) + timedelta(minutes=tzoffset)
    ldtz         = job.lastgeneratedon.replace(microsecond=0) + timedelta(minutes=tzoffset)
    display_jobs_date_info(cdtz, mdtz, vfrom, vupto, ldtz)
    current_date= datetime.utcnow().replace(tzinfo=timezone.utc).replace(microsecond=0)
    current_date= current_date + timedelta(minutes= tzoffset)

    if mdtz > cdtz:
        ldtz = current_date
        # delete all old record
        del_job(job.id)
    startdtz = vfrom

    if ldtz > vfrom:
        startdtz = ldtz
    if startdtz < current_date:
        startdtz = current_date
        ldtz     = current_date
    enddtz = ((current_date + timedelta(days=2)) - ldtz) + ldtz
    if vupto < enddtz:
        enddtz = vupto
    return startdtz, enddtz



def get_datetime_list(cron_exp, startdtz, enddtz):
    """
    calculates datetime_list for all jobs
    upon given starttime and endtime.
    """
    log.info("get_datetime_list(cron_exp, startdtz, enddtz) [start]")
    log.info("getting datetime list for cron:=%s, starttime:= '%s' and endtime:= '%s'" % (
        cron_exp, startdtz, enddtz))
    from croniter import croniter
    DT = []
    isValidCron = True
    cronDateTime = itr = None
    try:
        itr = croniter(cron_exp, startdtz)
        while True:
            cronDateTime = itr.get_next(datetime)
            if cronDateTime < enddtz:
                DT.append(cronDateTime)
            else:
                break
    except Exception as ex:
        log.error(
            'get_datetime_list(cron_exp, startdtz, enddtz) \
            Exception: [cronexp:= %s]croniter bad cron error:= %s'
            % (cron_exp, str(ex))
        )
        isValidCron = False
        log.error(
            'get_datetime_list(cron_exp, startdtz, enddtz) ERROR:', exc_info=True)
        raise ex
    if DT:
        log.info('Datetime list calculated are as follows:= %s' %
                 (pformat(DT, compact=True)))
    log.info("get_datetime_list(cron_exp, startdtz, enddtz) [end]")
    return DT, isValidCron


def dt_local_to_utc(tzoffset, data, mob_or_web):
    log.info('dt_local_to_utc [start]')
    dtlist= udt= cdt= dateFormate= None
    dateRegexMobile= r"[0-9]{4}-[0-9]{2}-[0-9]{02} [0-9]{02}:[0-9]{02}:[0-9]{02}"
    dateRegexWeb= r"[0-9]{2}-[A-Za-z]{3}-[0-9]{4} [0-9]{02}:[0-9]{02}"
    dateFormatMobile= "%Y-%m-%d %H:%M:%S"
    dateFormatWeb= "%d-%b-%Y %H:%M"


    if isinstance(data, dict):
        handle_dict_of_datetimes(dateFormatMobile, dateFormatWeb, data, tzoffset,
                                 dateRegexMobile, dateRegexWeb, mob_or_web)
        
    else:
        handle_list_of_datetimes(dateFormatMobile, dateFormatWeb, data,  tzoffset,
                                 dateRegexMobile, dateRegexWeb, mob_or_web)
    del dtlist, udt, cdt, dateFormate
    return data


def handle_dict_of_datetimes(dateFormatMobile, dateFormatWeb, data, tzoffset,
                            dateRegexMobile, dateRegexWeb, mob_or_web):
    import re
    for key, value in data.items():
        value= str(value)
        if mob_or_web.lower() == "mobile":
            dtlist= re.findall(dateRegexMobile, value)
            dateFormate= dateFormatMobile
        elif (
            mob_or_web.lower() != "mobile"
            and mob_or_web.lower() == "web"
            or mob_or_web.lower() != "mobile"
            and mob_or_web.lower() != "web"
            and mob_or_web.lower() == "cron"
        ):
            dtlist= re.findall(dateRegexWeb, value)
            dateFormate= dateFormatWeb
        dtlist= list(set(dtlist))
        if dtlist:
            log.info("dt_local_to_utc got all date: %s"%dtlist)
            try:
                tzoffset= int(tzoffset)
                for item_ in dtlist:
                    udt= cdt= None
                    try:
                        udt = (
                            datetime.datetime.strptime(
                                str(item_), dateFormate
                            )
                            .replace(tzinfo=timezone.utc)
                            .replace(microsecond=0)
                        )

                        cdt= udt - timedelta(minutes= tzoffset)
                        data[key] = str(data[key]).replace(str(item_), str(cdt))
                    except Exception as ex:
                        log.error("datetime parsing error", exc_info=True)
                        raise
            except ValueError:
                log.error("tzoffset parsing error", exc_info=True)
                raise
                
                
def handle_list_of_datetimes(dateFormatMobile, dateFormatWeb, data, tzoffset,
                            dateRegexMobile, dateRegexWeb, mob_or_web):
    import re
    if mob_or_web.lower() == "mobile":
        dtlist= re.findall(dateRegexMobile, str(data))
        dateFormate= dateFormatMobile
    elif (
        mob_or_web.lower() != "mobile"
        and mob_or_web.lower() == "web"
        or mob_or_web.lower() != "mobile"
        and mob_or_web.lower() != "web"
        and mob_or_web.lower() == "cron"
    ):
        dtlist= re.findall(dateRegexWeb, data)
        dateFormate= dateFormatWeb
    dtlist= list(set(dtlist))
    if dtlist:
        log.info("got all date %s"%(dtlist))
        try:
            tzoffset= int(tzoffset)
            for item in dtlist:
                udt= cdt= None
                try:
                    udt = (
                        datetime.datetime.strptime(str(item), dateFormate)
                        .replace(tzinfo=timezone.utc)
                        .replace(microsecond=0)
                    )

                    cdt= udt - timedelta(minutes= tzoffset)
                    data = str(data).replace(str(item), str(cdt))
                except Exception as ex:
                    log.error("datetime parsing error", exc_info=True)
                    raise
        except ValueError:
            log.error("tzoffset parsing error", exc_info=True)
            raise


def insert_into_jn_and_jnd(job, DT):
    log.info("insert_into_jn_and_jnd() [ start ]")
    NONE_JN  = get_or_create_none_jobneed()
    NONE_JB  = get_or_create_none_job()
    NONE_P   = putils.get_or_create_none_people()
    NONE_QSB = get_or_create_none_qsetblng()
    status   = None
    if len(DT) > 0:
        try:
            from django.utils.timezone import get_current_timezone
            tz = get_current_timezone()
            crontype = job.identifier
            jobstatus = 'ASSIGNED',
            jobtype = 'SCHEDULE',
            jobdesc = f'{job.jobname} :: {job.jobdesc}'
            asset = am.Asset.objects.get(id=job.assetid_id)
            multiplication_factor = asset.asset_json['mult_factor']
            mins = pdtz = edtz = peopleid = jnid = None
            parent = peopleid = -1

            mins = job.planduration + job.expirytime + job.gracetime
            peopleid = job.peopleid_id
            params   = {'jobstatus':jobstatus, 'jobtype':jobtype,
                        'm_factor':multiplication_factor, 'peopleid':peopleid,
                        'NONE_P':NONE_P, 'jobdesc':jobdesc, 'NONE_JN':NONE_JN}
            for dt in DT:
                dtstr = dt_local_to_utc(job.ctzoffset, str(dt.strftime("%d-%b-%Y %H:%M")), "cron")
                dt   = datetime.strptime(dtstr[:16], "%Y-%m-%d %H:%M")
                pdtz = params['pdtz'] = dt
                edtz = params['edtz'] = dt + timedelta(minutes=mins)
                jn = insert_into_jn_for_parent(job, params)
                insert_update_jobneeddetails(jn.id, job, parent=True)
                if isinstance(jn, am.Jobneed):
                    log.info("createJob() parent jobneedid:= %s" % (jn.id))
                    if crontype == 'INTERNALTOUR':
                        edtz = create_child_tasks(
                            job, pdtz, peopleid, jn.id, jobstatus, jobtype)
                        if edtz is not None:
                            jn = am.Jobneed.objects.filter(id=jn.id).update(
                                expirydatetime=edtz
                            )
                            if jn <= 0:
                                raise ValueError
            update_lastgeneratedon(job, pdtz)
        except Exception as ex:
            status = 'failed'
            log.error('insert_into_jn_and_jnd() ERROR', exc_info=True)
            raise ex
        else:
            status = "success"
        log.info("insert_into_jn_and_jnd() [ End ]")
        return status


def insert_into_jn_for_parent(job, params):
    try:
        jn = am.Jobneed.objects.create(
            jobid_id       = job.id,            parent             = params['NONE_JN'],
            jobdesc        = params['jobdesc'], plandatetime       = params['pdtz'],
            expirydatetime = params['edtz'],    gracetime          = job.gracetime,
            assetid_id     = job.assetid_id,    qsetid_id          = job.qsetid_id,
            aatop_id       = job.aatop_id,      peopleid_id        = params['peopleid'],
            groupid_id     = job.groupid_id,    frequency          = 'NONE',
            priority       = job.priority,      jobstatus          = params['jobstatus'],
            performed_by   = params['NONE_P'],  jobtype            = params['jobtype'],
            scantype       = job.scantype,      identifier         = job.identifier,
            cuser_id       = job.cuser_id,      muser_id           = job.muser_id,
            buid_id        = job.buid_id,       ticket_category_id = job.ticket_category_id,
            gpslocation    = '0.0,0.0',         remarks            = '',
            slno           = 0,                 mult_factor        = params['m_factor'],
            clientid_id    = job.clientid_id,   ctzoffset          = job.ctzoffset,
        )
    except Exception:
        raise
    else:
        return jn




def insert_update_jobneeddetails(jnid, job, parent=False):
    log.info("insert_update_jobneeddetails() [START]")
    from django.utils.timezone import get_current_timezone
    tz = get_current_timezone()
    try:
        am.JobneedDetails.objects.get(jobneedid_id=jnid).delete()
    except am.JobneedDetails.DoesNotExist:
        pass
    try:
        if not parent:
            qsb = am.QuestionSetBelonging.objects.select_related(
                'quesid').filter(
                    qsetid_id=job.qsetid_id).order_by(
                        'slno').values_list(named=True)
        else:
            qsb = get_or_create_none_qsetblng()
        if not qsb:
            log.error("No Checklist Found failed to schedhule job",
                      exc_info=True)
            raise EmptyResultSet
        else:
            insert_into_jnd(qsb, job, jnid)
    except Exception:
        raise
    log.info("insert_update_jobneeddetails() [END]")
    



def insert_into_jnd(qsb, job, jnid):
    log.info("insert_into_jnd() [START]")
    try:
        if not isinstance(qsb, am.QuestionSetBelonging):
            qsb = qsb[0]
        am.JobneedDetails.objects.create(
            slno       = qsb.slno,       quesid_id    = qsb.quesid_id,
            answertype = qsb.answertype, max          = qsb.max,
            min        = qsb.min,        alerton      = qsb.alerton,
            options    = qsb.options,    jobneedid_id = jnid,
            cuser_id   = job.cuser_id,   muser_id     = job.muser_id,)
    except Exception:
        raise
    log.info("insert_into_jnd() [END]")
    

   
    
def create_child_tasks(job, _pdtz, _peopleid, jnid, _jobstatus, _jobtype):
    try:
        prev_edtz = None
        NONE_P = putils.get_or_create_none_people()
        from django.utils.timezone import get_current_timezone
        tz = get_current_timezone()
        mins = pdtz = edtz = None
        R = am.Job.objects.filter(
            parent_id=job.id).order_by(
                'slno').values_list(named=True)
        log.info("create_child_tasks() total child job:=%s" % (len(R)))
        prev_edtz = _pdtz
        params = {'_jobdesc':"", 'jnid':jnid, 'pdtz':None, 'edtz':None,
                  '_peopleid':_peopleid, '_jobstatus':_jobstatus, '_jobtype':_jobtype,
                  'm_factor':None, 'idx':None, 'NONE_P':NONE_P}
        for idx, r in enumerate(R):
            log.info("create_child_tasks() [%s] child job:= %s | jobid:= %s | cron:= %s" % (
                idx, r.jobname, r.id, r.cron))
            asset = am.Asset.objects.get(id=r.assetid_id)
            params['m_factor'] = asset.asset_json['mult_factor']
            _assetname = asset.assetname

            mins = job.planduration + r.expirytime + job.gracetime
            params['_peopleid'] = r.aaatop_id
            params['_jobdesc'] = f"{r.jobname} :: {_assetname}"
            if idx == 0:
                pdtz = params['pdtz'] = prev_edtz
            else:
                pdtz = params['pdtz'] = prev_edtz - \
                    timedelta(minutes=r.expirytime + job.gracetime)
            edtz = params['edtz'] = pdtz + timedelta(minutes=mins)
            prev_edtz = edtz
            params['idx'] = idx
            jn = insert_into_jn_for_child(job, params, r)
            insert_update_jobneeddetails(jn.id, r)
    except Exception:
        log.error(
            "create_child_tasks() ERROR failed to create task's", exc_info=True)
        raise
    else:
        log.info("create_child_tasks() successfully created [ END ]")
        return edtz
 
 
 
def insert_into_jn_for_child(job, params, r):
    try:
        jn = am.Jobneed.objects.create(
            jobid_id       = job.id,             parent_id          = params['jnid'],
            jobdesc        = params['_jobdesc'], plandatetime       = params['pdtz'],
            expirydatetime = params['edtz'],     gracetime          = job.gracetime,
            assetid_id     = r.assetid_id,       qsetid_id          = r.qsetid_id,
            aatop_id       = r.aatop_id,         peopleid_id        = params['_peopleid'],
            groupid_id     = job.groupid_id,     frequency          = 'NONE',
            priority       = r.priority,         jobstatus          = params['_jobstatus'],
            clientid_id    = r.clientid_id,      jobtype            = params['_jobtype'],
            scantype       = job.scantype,       identifier         = job.identifier,
            cuser_id       = r.cuser_id,         muser_id           = r.muser_id,
            buid_id        = r.buid_id,          ticket_category_id = r.ticket_category_id,
            gpslocation    = '0.0,0.0',          remarks            = '',
            slno           = params['idx'],      mult_factor        = params['m_factor'],
            performed_by   = params['NONE_P'],   ctzoffset         =  r.ctzoffset
            )
    except Exception:
        raise
    else:
        return jn



def job_fields(job, checkpoint):
    return { 
        'jobname'     : job.jobname,        'jobdesc'        : job.jobdesc,
        'cron'        : job.cron,           'identifier'     : job.identifier,
        'expirytime'  : int(checkpoint[5]), 'lastgeneratedon': job.lastgeneratedon,
        'priority'    : job.priority,       'qsetid_id'      : checkpoint[3],
        'groupid_id'  : job.groupid_id,     'gfid'           : job.gfid_id,
        'endtime'     : job.endtime,        'ticket_category': job.ticket_category,
        'from_date'   : job.from_date,      'upto_date'      : job.upto_date,
        'planduration': job.planduration,   'gracetime'      : job.gracetime,
        'assetid_id'  : checkpoint[1],      'frequency'      : job.frequency,
        'peopleid_id' : job.peopleid_id,    'starttime'      : job.starttime,
        'parent_id'   : job.id,             'slno'           : checkpoint[0],
        'scantype'    : job.scantype,
    }
    
def get_or_create_none_job():
    from datetime import datetime, timezone
    date = datetime(1970,1,1,00,00,00).replace(tzinfo=timezone.utc)
    obj, _ = am.Job.objects.filter(Q(jobname='NONE') | Q(jobname='None')).get_or_create(
        jobname = 'NONE',
        defaults={
            'jobname'     : 'NONE',    'jobdesc'        : 'NONE',
            'from_date'   : date,      'upto_date'      : date,
            'cron'        : "no_cron", 'lastgeneratedon': date,
            'planduration': 0,         'expirytime'     : 0,
            'gracetime'   : 0,         'priority'       : 'LOW',
            'slno'        : -1,        'scantype'       : 'SKIP'
        }
    )
    return obj


def get_or_create_none_jobneed():
    from datetime import datetime, timezone
    date = datetime(1970,1,1,00,00,00).replace(tzinfo=timezone.utc)
    obj, _ = am.Jobneed.objects.filter(Q(jobdesc = 'NONE')).get_or_create(
        defaults={
            'jobdesc'          : "NONE", 'plandatetime': date,
            'expirydatetime'   : date,   'gracetime'   : 0,
            'recievedon_server': date,   'slno'        : -1,
            'scantype'         : "NONE"
        }
    )
    return obj


def get_or_create_none_qset():
    obj, _ = am.QuestionSet.objects.filter(
        Q(qset_name = 'NONE') | Q(qset_name = 'None')).get_or_create(
        qset_name = 'NONE',
        defaults={
            'qset_name':"NONE"}
    )
    return obj

def get_or_create_none_question():
    obj, _ = am.Question.objects.filter(
        Q(ques_name = 'NONE')).get_or_create(
        ques_name = 'NONE',
        defaults = {
            'ques_name':"NONE"}
    )
    return obj


def get_or_create_none_qsetblng():
    obj, _ = am.QuestionSetBelonging.objects.filter(
        Q(slno = 999)| Q(answertype = 'NUMERIC')).get_or_create(
        slno = 999,
        defaults = {
            'qsetid'     : get_or_create_none_qset(),
            'quesid'     : get_or_create_none_question(),
            'answertype' : 'NUMERIC',
            'ismandatory': False}
    )
    return obj

def get_or_create_none_asset():
    obj, _ = am.Asset.objects.filter(
        Q(assetcode = 'NONE') | Q(assetname='NONE')).get_or_create(
        assetcode = 'NONE',
        defaults={
            'assetcode'    : "NONE", 'assetname' : 'NONE',
            'iscritical'   : False,  'identifier': 'NONE',
            'runningstatus': 'SCRAPPED'
        }
    )
    return obj

def to_local(val):
    from django.utils.timezone import get_current_timezone
    return val.astimezone(get_current_timezone()).strftime('%d-%b-%Y %H:%M')

def delete_from_job(jobid, checkpointId, checklistId):
    try:
        am.Job.objects.get(
            parent     = int(jobid),
            assetid_id = int(checkpointId),
            qsetid_id  = int(checklistId)).delete()
    except Exception:
        raise


def delete_from_jobneed(parentjobid, checkpointId, checklistId):
    try:
        am.Jobneed.objects.get(
            parent     = int(parentjobid),
            assetid_id = int(checkpointId),
            qsetid_id  = int(checklistId)).delete()
    except Exception:
        raise


def update_lastgeneratedon(job, pdtz):
    try:
        log.info('update_lastgeneratedon [start]')
        rec = am.Job.objects.filter(id=job.id).update(
            lastgeneratedon=pdtz
        )
        if rec:
            log.info("after lastgenreatedon:=%s" % (pdtz))
        log.info('update_lastgeneratedon [end]')
    except Exception:
        raise


def send_email_notication(err):
    pass


def del_job(id):
    pass