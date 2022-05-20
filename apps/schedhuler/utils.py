from django.db.models import Q
import apps.activity.models as am
from django.core.exceptions import EmptyResultSet
from django.db import transaction
from django.http import Http404, response as rp
from logging import getLogger
from pprint import pformat
from apps.core import utils
from datetime import datetime, timezone, timedelta
log = getLogger('__main__')

def create_job(jobs=None):
    startdtz = enddtz = msg = resp = None
    F, d = {}, []
    
    from django.utils.timezone import get_current_timezone
    tzoffset     = get_current_timezone().utcoffset(datetime.utcnow()).seconds // 60
    tz = get_current_timezone()
    with transaction.atomic(using=utils.get_current_db_name()):
        if not jobs:
            jobs = am.Job.objects.filter(
                ~Q(jobname='NONE'),
                ~Q(asset__runningstatus=am.Asset.RunningStatus.SCRAPPED),
                parent_id=1,
            ).select_related(
                "asset", "pgroup",
                "cuser", "muser", "qset", "people",
            ).values_list(named=True)
        
        if not jobs:
            msg = "No jobs found schedhuling terminated"
            resp = rp.JsonResponse("%s"%(msg), status=404)
            log.warn("%s" % (msg), exc_info=True)
            raise EmptyResultSet
        total_jobs = len(jobs)
        
        if total_jobs > 0 or jobs != None:
            log.info("processing jobs started found:= '%s' jobs" % (len(jobs)))
            for idx, job in enumerate(jobs):
                startdtz, enddtz = calculate_startdtz_enddtz(job, tzoffset, tz)
                log.debug(
                    "Jobs to be schedhuled from startdatetime %s to enddatetime %s"%(startdtz, enddtz)
                )
                DT, is_cron, resp = get_datetime_list(job.cron, startdtz, enddtz, resp)
                log.debug(
                    "Jobneed will going to create for all this datetimes\n %s"%(pformat(get_readable_dates(DT)))
                )
                F[str(job.id)] = is_cron
                status, resp = insert_into_jn_and_jnd(job, DT, tzoffset, resp)
                d.append({
                    "job"   : job.id,
                    "jobname" : job.jobname,
                    "cron"    : job.cron,
                    "iscron"  : is_cron,
                    "count"   : len(DT),
                    "status"  : status
                })
            if F:
                log.info("create_job() Failed job schedule list:= %s" %
                         (pformat(F)))
            log.info("createJob()[end-] [%s of %s] parent job:= %s | job:= %s | cron:= %s" %
                     (idx, (total_jobs - 1), job.jobname, job.id, job.cron))
        ic("resp in createjob()", resp)
    return resp


def display_jobs_date_info(cdtz, mdtz, fromdate, uptodate, ldtz):
    padd = "#"*8
    log.info("%s display_jobs_date_info [start] %s" % (padd, padd))
    log.info("created-on:= [%s] modified-on:=[%s]" % (cdtz, mdtz))
    log.info("valid-from:= [%s] valid-upto:=[%s]" %
             (fromdate, uptodate))
    log.info("before lastgeneratedon:= [%s]" % (ldtz))
    log.info("%s display_jobs_date_info [end] %s" % (padd, padd))
    del padd

def get_readable_dates(dt_list):
    if (isinstance(dt_list, list)):
        return [dt.strftime("%d-%b-%Y %H:%M") for dt in dt_list]


def calculate_startdtz_enddtz(job, tzoffset, tz):
    """
    this function determines or calculates what is 
    the plandatetime & expirydatetime of a job for next 2 days or upto
    uptodate.
    """
    
    log.info("calculating startdtz, enddtz for job:= [%s]" % (job.id))
    
    cdtz         = job.cdtz.replace(microsecond=0, tzinfo=tz) + timedelta(minutes=tzoffset)
    mdtz         = job.mdtz.replace(microsecond=0, tzinfo=tz)  + timedelta(minutes=tzoffset)
    vfrom        = job.fromdate.replace(microsecond=0, tzinfo=tz)  + timedelta(minutes=tzoffset)
    vupto        = job.uptodate.replace(microsecond=0, tzinfo=tz) + timedelta(minutes=tzoffset)
    ldtz         = job.lastgeneratedon.replace(microsecond=0, tzinfo=tz) + timedelta(minutes=tzoffset)
    # tzoffset     = job.ctzoffset 
    # cdtz         = job.cdtz.replace(microsecond=0) 
    # mdtz         = job.mdtz.replace(microsecond=0)  
    # vfrom        = job.fromdate.replace(microsecond=0)  
    # vupto        = job.uptodate.replace(microsecond=0) 
    # ldtz         = job.lastgeneratedon.replace(microsecond=0) 
    # display_jobs_date_info(cdtz, mdtz, vfrom, vupto, ldtz)
    current_date= datetime.utcnow().replace(tzinfo=timezone.utc).replace(microsecond=0)
    current_date= current_date.replace(tzinfo=tz) + timedelta(minutes= tzoffset)

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



def get_datetime_list(cron_exp, startdtz, enddtz, resp):
    """
        this function calculates and returns array of next starttime
        for every day upto enddatetime based on given cron expression.
        Eg: 
        returning all starttime's from 1/01/20xx --> 3/01/20xx based on cron exp.
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
        resp = rp.JsonResponse({"errors":"Bad Cron Error"}, status = 404)
        isValidCron = False
        log.error(
            'get_datetime_list(cron_exp, startdtz, enddtz) ERROR:', exc_info=True)
        raise ex from ex
    if DT:
        log.info('Datetime list calculated are as follows:= %s' %
                 (pformat(DT, compact=True)))
    log.info("get_datetime_list(cron_exp, startdtz, enddtz) [end]")
    ic("resp in get_datetime_list()", resp)
    return DT, isValidCron, resp


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
        if dtlist := list(set(dtlist)):
            log.info("dt_local_to_utc got all date: %s"%dtlist)
            try:
                tzoffset= int(tzoffset)
                for item_ in dtlist:
                    udt= cdt= None
                    try:
                        udt = (
                            datetime.strptime(
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
    if dtlist := list(set(dtlist)):
        log.info("got all date %s"%(dtlist))
        try:
            tzoffset= int(tzoffset)
            for item in dtlist:
                udt= cdt= None
                try:
                    udt = (
                        datetime.strptime(str(item), dateFormate)
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


def insert_into_jn_and_jnd(job, DT, tzoffset, resp):
    """
        calculates expirydatetime for every dt in 'DT' list and
        inserts into jobneed and jobneed-details for all dates
        in 'DT' list.
    """
    log.info("insert_into_jn_and_jnd() [ start ]")
    status   = None
    if len(DT) > 0:
        try:
            NONE_JN  = utils.get_or_create_none_jobneed()
            NONE_P   = utils.get_or_create_none_people()
            crontype = job.identifier
            jobstatus = am.Jobneed.JobStatus.ASSIGNED,
            jobtype = am.Jobneed.JobType.SCHEDULE,
            jobdesc = f'{job.jobname} :: {job.jobdesc}'
            asset = am.Asset.objects.get(id=job.asset_id)
            multiplication_factor = asset.asset_json['multifactor']
            mins = pdtz = edtz = people = jnid = None
            parent = people = -1

            mins = job.planduration + job.expirytime + job.gracetime
            people = job.people_id
            params   = {
                'jobstatus':jobstatus, 'jobtype':jobtype,
                'm_factor':multiplication_factor, 'people':people,
                'NONE_P':NONE_P, 'jobdesc':jobdesc, 'NONE_JN':NONE_JN}
            DT = utils.to_utc(DT)
            for dt in DT:
                dt = dt.strftime("%Y-%m-%d %H:%M")
                dt = datetime.strptime(dt, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
                pdtz = params['pdtz'] = dt
                edtz = params['edtz'] = dt + timedelta(minutes=mins)
                log.debug(
                    'pdtz:=%s edtz:=%s'%(pdtz, edtz)
                )
                jn = insert_into_jn_for_parent(job, params)
                isparent = crontype in (am.Job.Identifier.INTERNALTOUR, am.Job.Identifier.EXTERNALTOUR)
                insert_update_jobneeddetails(jn.id, job, parent=isparent)
                if isinstance(jn, am.Jobneed):
                    log.info("createJob() parent jobneed:= %s" % (jn.id))
                    if crontype in (am.Job.Identifier.INTERNALTOUR, am.Job.Identifier.EXTERNALTOUR):
                        edtz = create_child_tasks(
                            job, pdtz, people, jn.id, jobstatus, jobtype)
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
            resp = rp.JsonResponse({
                "errors":"Failed to schedule jobs"}, status=404)
            raise ex from ex
        else:
            status = "success"
            resp = rp.JsonResponse({'msg':'%s tasks scheduled successfully!'%(len(DT))}, status=200)
        log.info("insert_into_jn_and_jnd() [ End ]")
        return status, resp


def insert_into_jn_for_parent(job, params):
    try:
        jn = am.Jobneed.objects.create(
            job_id       = job.id,            parent             = params['NONE_JN'],
            jobdesc        = params['jobdesc'], plandatetime       = params['pdtz'],
            expirydatetime = params['edtz'],    gracetime          = job.gracetime,
            asset_id     = job.asset_id,    qset_id          = job.qset_id,
            ctzoffset      = job.ctzoffset,     people_id        = params['people'],
            pgroup_id     = job.pgroup_id,    frequency          = 'NONE',
            priority       = job.priority,      jobstatus          = params['jobstatus'],
            performedby   = params['NONE_P'],  jobtype            = params['jobtype'],
            scantype       = job.scantype,      identifier         = job.identifier,
            cuser_id       = job.cuser_id,      muser_id           = job.muser_id,
            bu_id        = job.bu_id,       ticketcategory_id = job.ticketcategory_id,
            gpslocation    = '0.0,0.0',         remarks            = '',
            seqno           = 0,                 multifactor        = params['m_factor'],
            client_id    = job.client_id,
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
        am.JobneedDetails.objects.get(jobneed_id=jnid).delete()
    except am.JobneedDetails.DoesNotExist:
        pass
    try:
        if not parent:
            qsb = am.QuestionSetBelonging.objects.select_related(
                'question').filter(
                    qset_id=job.qset_id).order_by(
                        'seqno').values_list(named=True)
        else:
            qsb = utils.get_or_create_none_qsetblng()
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
            seqno       = qsb.seqno,       question_id    = qsb.question_id,
            answertype = qsb.answertype, max          = qsb.max,
            min        = qsb.min,        alerton      = qsb.alerton,
            options    = qsb.options,    jobneed_id = jnid,
            cuser_id   = job.cuser_id,   muser_id     = job.muser_id,)
    except Exception:
        raise
    log.info("insert_into_jnd() [END]")
    

   
    
def create_child_tasks(job, _pdtz, _people, jnid, _jobstatus, _jobtype):
    try:
        prev_edtz = None
        NONE_P = utils.get_or_create_none_people()
        from django.utils.timezone import get_current_timezone
        tz = get_current_timezone()
        mins = pdtz = edtz = None
        R = am.Job.objects.filter(
            parent_id=job.id).order_by(
                'seqno').values_list(named=True)
        log.info("create_child_tasks() total child job:=%s" % (len(R)))
        prev_edtz = _pdtz
        params = {'_jobdesc':"", 'jnid':jnid, 'pdtz':None, 'edtz':None,
                  '_people':_people, '_jobstatus':_jobstatus, '_jobtype':_jobtype,
                  'm_factor':None, 'idx':None, 'NONE_P':NONE_P}
        for idx, r in enumerate(R):
            log.info("create_child_tasks() [%s] child job:= %s | job:= %s | cron:= %s" % (
                idx, r.jobname, r.id, r.cron))
            asset = am.Asset.objects.get(id=r.asset_id)
            params['m_factor'] = asset.asset_json['multifactor']
            _assetname = asset.assetname

            mins = job.planduration + r.expirytime + job.gracetime
            params['_people'] = r.aaatop_id
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
            job_id       = job.id,             parent_id          = params['jnid'],
            jobdesc        = params['_jobdesc'], plandatetime       = params['pdtz'],
            expirydatetime = params['edtz'],     gracetime          = job.gracetime,
            asset_id     = r.asset_id,       qset_id          = r.qset_id,
            aatop_id       = r.aatop_id,         people_id        = params['_people'],
            pgroup_id     = job.pgroup_id,     frequency          = 'NONE',
            priority       = r.priority,         jobstatus          = params['_jobstatus'],
            client_id    = r.client_id,      jobtype            = params['_jobtype'],
            scantype       = job.scantype,       identifier         = job.identifier,
            cuser_id       = r.cuser_id,         muser_id           = r.muser_id,
            bu_id        = r.bu_id,          ticketcategory_id = r.ticketcategory_id,
            gpslocation    = '0.0,0.0',          remarks            = '',
            seqno           = params['idx'],      multifactor        = params['m_factor'],
            performedby   = params['NONE_P'],   ctzoffset         =  r.ctzoffset
            )
    except Exception:
        raise
    else:
        return jn



def job_fields(job, checkpoint, external=False):
    data =  { 
        'jobname'     : job.jobname,                   'jobdesc'        : job.jobdesc,
        'cron'        : job.cron,                      'identifier'     : job.identifier,
        'expirytime'  : int(checkpoint['expirytime']), 'lastgeneratedon': job.lastgeneratedon,
        'priority'    : job.priority,                  'qset_id'      : checkpoint['qset'],
        'pgroup_id'  : job.pgroup_id,                'geofence'           : job.geofence_id,
        'endtime'     : job.endtime,                   'ticketcategory': job.ticketcategory,
        'fromdate'   : job.fromdate,                 'uptodate'      : job.uptodate,
        'planduration': job.planduration,              'gracetime'      : job.gracetime,
        'asset_id'  : checkpoint['asset'],         'frequency'      : job.frequency,
        'people_id' : job.people_id,               'starttime'      : job.starttime,
        'parent_id'   : job.id,                        'seqno'           : checkpoint['seqno'],
        'scantype'    : job.scantype,
    }
    if external:
        jsonData = {
            'distance'      : checkpoint['distance'],
            'breaktime'     : checkpoint['breaktime'],
            'is_randomized' : checkpoint['israndom'],
            'tour_frequency': checkpoint['routeFreq']}
        data['jobname']    = checkpoint['jobname']
        data['other_info'] = jsonData
    return data

def to_local(val):
    from django.utils.timezone import get_current_timezone
    return val.astimezone(get_current_timezone()).strftime('%d-%b-%Y %H:%M')

def delete_from_job(job, checkpointId, checklistId):
    try:
        am.Job.objects.get(
            parent     = int(job),
            asset_id = int(checkpointId),
            qset_id  = int(checklistId)).delete()
    except Exception:
        raise


def delete_from_jobneed(parentjob, checkpointId, checklistId):
    try:
        am.Jobneed.objects.get(
            parent     = int(parentjob),
            asset_id = int(checkpointId),
            qset_id  = int(checklistId)).delete()
    except Exception:
        raise


def update_lastgeneratedon(job, pdtz):
    try:
        log.info('update_lastgeneratedon [start]')
        if rec := am.Job.objects.filter(id=job.id).update(
            lastgeneratedon=pdtz
        ):
            log.info("after lastgenreatedon:=%s" % (pdtz))
        log.info('update_lastgeneratedon [end]')
    except Exception:
        raise


def send_email_notication(err):
    pass


def del_job(id):
    pass