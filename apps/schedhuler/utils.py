from sqlite3 import Row
from django.db.models import Q, F
from django.core.exceptions import EmptyResultSet
from django.db import transaction
from django.http import response as rp
import apps.activity.models as am
from logging import getLogger
from pprint import pformat
from random import shuffle
from apps.core import utils
from datetime import datetime, timezone, timedelta
log = getLogger('__main__')


def get_service_requirements(R):
    """
    returns startpoint, endpoint, waypoints
    required for directions api
    """
    if R:
        startp = {"lat":float(R[0]['cplocation'].coords[1]),
                  "lng":float(R[0]['cplocation'].coords[0])}

        endp = {"lat":float(R[len(R)-1]['cplocation'].coords[1]),
               "lng":float(R[len(R)-1]['cplocation'].coords[0])}
        waypoints=[]
        for i in range(1, len(R)-1):
            lat, lng = R[i]['cplocation'].coords[1], R[i]['cplocation'].coords[0]
            waypoints.append(
                {"lat":lat, "lng":lng}
            )
        return startp, endp, waypoints


def get_frequencied_data(DDE, data, f, breaktime):
    """
    Randomize data based on frequency
    """
    import copy

    R, dataCopy = [], copy.deepcopy(data)
    for _ in range(f-1):
        R=data
        R+=reversedFPoints(DDE, dataCopy, breaktime)


def convertto_namedtuple(A,records, freq, btime):
    """
    converts dict to namedtuple
    """
    rec, C = [], records[0].keys()
    from collections import namedtuple
    for i in range(len(records)):
        record = namedtuple("Record", C)
        records[i]["seqno"] = i+1
        records[i]["jobname"] = f"[{str(records[i]['seqno'])}]-{records[i]['jobname']}"
        tr = tuple(records[i].values())
        rec.append(record(**dict(list(zip(C, tr)))))
    
    if freq>1 or btime!=0:
        rec[0] = rec[0]._replace(distance=0) 
        rec[0] = rec[0]._replace(expirytime=0)
        rec[0] = rec[0]._replace(breaktime=0)
    return rec

    
def reversedFPoints(DDE, data, breaktime):
    
    R, j= [], 0
    DDE = DDE[::-1]
    for i in reversed(range(len(data))):
        if (i == len(data)-1):
            data[i]['distance'] = data[i]['duration'] = data[i]['expirytime'] = data[i]['breaktime'] = 0
        else:
            data[i]['distance'], data[i]['duration'], data[i]['expirytime'] = DDE[j]
            j+=1
        R.append(data[i])
    R[-1]['breaktime'] = breaktime
    return R


def calculate_route_details(R, job):
    data = [r._asdict() for r in R]
    ic(data)
    import googlemaps
    from django.conf import settings
    gmaps = googlemaps.Client(key=settings.GOOGLE_MAP_SECRET_KEY)
    startpoint, endpoint, waypoints = get_service_requirements(data)
    directions = gmaps.directions(mode='driving', waypoints = waypoints, origin=startpoint, destination= endpoint, optimize_waypoints = True)
    waypoint_order = directions[0]["waypoint_order"]
    freq, breaktime = job.other_info['tour_frequency'], job.other_info['breaktime']
    chekpoints = []
    
    #startpoint distance, duration, expirtime is 0.
    data[0]['seqno'] = 0+1
    chekpoints.append(data[0])
    chekpoints[0]['distance'] = 0
    chekpoints[0]["duration"] = 0
    chekpoints[0]["expirytime"] = 0
    
    #waypoint
    for i in range(len(waypoint_order)):
        data[i+1]['seqno'] = (i+1)+1
        chekpoints.append(data[waypoint_order[i]+1])
        
    #endpoint
    data[len(data)-1]['seqno'] = len(data)-1+1    
    chekpoints.append(data[len(data)-1])
    
    #calculate distance and duration
    legs = directions[0]["legs"]
    j=1
    
    
    DDE = []
    for i in range(len(legs)):
        l=[]
        chekpoints[j]['distance']=round(float(legs[i]['distance']["value"]/1000), 2)
        l.append(chekpoints[j]["distance"])
        chekpoints[j]['duration']=float(legs[i]["duration"]["value"])
        l.append(chekpoints[j].duration)
        chekpoints[j]['expirytime']=int(legs[i]["duration"]["value"]/60)
        l.append(chekpoints[j]['expirytime'])
        DDE.append(l)
        j+=1
    
    if freq > 1:
        chekpoints = get_frequencied_data(DDE, chekpoints, freq, breaktime)
    
    if freq>1 and breaktime!=0:
        #frequency points for freq>1.
        endp = int(len(chekpoints)/freq)
        chekpoints[endp]['breaktime'] = breaktime
    
    return convertto_namedtuple(chekpoints, freq, breaktime)

def create_job(jobs = None):
    startdtz = enddtz = msg = resp = None
    F, d = {}, []

    from django.utils.timezone import get_current_timezone
    with transaction.atomic(using = utils.get_current_db_name()):
        if not jobs:
            jobs = am.Job.objects.filter(
                ~Q(jobname='NONE'),
                ~Q(asset__runningstatus = am.Asset.RunningStatus.SCRAPPED),
                parent_id = 1,
            ).select_related(
                "asset", "pgroup",
                "cuser", "muser", "qset", "people",
            ).values_list(named = True)

        if not jobs:
            msg = "No jobs found schedhuling terminated"
            resp = rp.JsonResponse(f"{msg}", status = 404)
            log.warning(f"{msg}", exc_info = True)
            raise EmptyResultSet
        total_jobs = len(jobs)

        if total_jobs > 0 or jobs is not None:
            log.info("processing jobs started found:= '%s' jobs" % (len(jobs)))
            for idx, job in enumerate(jobs):
                startdtz, enddtz = calculate_startdtz_enddtz(job)
                log.debug(f"Jobs to be schedhuled from startdatetime {startdtz} to enddatetime {enddtz}")

                DT, is_cron, resp = get_datetime_list(job.cron, startdtz, enddtz, resp)
                log.debug(
                    "Jobneed will going to create for all this datetimes\n %s"%(pformat(get_readable_dates(DT)))
                )
                F[str(job.id)] = is_cron
                status, resp = insert_into_jn_and_jnd(job, DT, resp)
                d.append({
                    "job"   : job.id,
                    "jobname" : job.jobname,
                    "cron"    : job.cron,
                    "iscron"  : is_cron,
                    "count"   : len(DT),
                    "status"  : status
                })
            if F:
                log.info(f"create_job() Failed job schedule list:= {pformat(F)}")
            log.info(f"createJob()[end-] [{idx} of {total_jobs - 1}] parent job:= {job.jobname} | job:= {job.id} | cron:= {job.cron}")

        ic("resp in createjob()", resp)
    return resp

def display_jobs_date_info(cdtz, mdtz, fromdate, uptodate, ldtz):
    padd = "#"*8
    log.info(f"{padd} display_jobs_date_info [start] {padd}")
    log.info(f"created-on:= [{cdtz}] modified-on:=[{mdtz}]")
    log.info(f"valid-from:= [{fromdate}] valid-upto:=[{uptodate}]")
    log.info(f"before lastgeneratedon:= [{ldtz}]")
    log.info(f"{padd} display_jobs_date_info [end] {padd}")

def get_readable_dates(dt_list):
    if (isinstance(dt_list, list)):
        return [dt.strftime("%d-%b-%Y %H:%M") for dt in dt_list]

def calculate_startdtz_enddtz(job):
    """
    this function determines or calculates what is 
    the plandatetime & expirydatetime of a job for next 2 days or upto
    uptodate.
    """

    log.info(f"calculating startdtz, enddtz for job:= [{job.id}]")
    tz = timezone(timedelta(minutes = int(job.ctzoffset)))
    ctzoffset = job.ctzoffset

    cdtz         = job.cdtz.replace(microsecond = 0, tzinfo = tz) + timedelta(minutes = ctzoffset)
    mdtz         = job.mdtz.replace(microsecond = 0, tzinfo = tz)  + timedelta(minutes = ctzoffset)
    vfrom        = job.fromdate.replace(microsecond = 0, tzinfo = tz)  + timedelta(minutes = ctzoffset)
    vupto        = job.uptodate.replace(microsecond = 0, tzinfo = tz) + timedelta(minutes = ctzoffset)
    ldtz         = job.lastgeneratedon.replace(microsecond = 0, tzinfo = tz) + timedelta(minutes = ctzoffset)
    # job.ctzoffset     = job.ctzoffset 
    # tzoffset     = job.ctzoffset 
    # cdtz         = job.cdtz.replace(microsecond = 0) 
    # mdtz         = job.mdtz.replace(microsecond = 0)  
    # vfrom        = job.fromdate.replace(microsecond = 0)  
    # vupto        = job.uptodate.replace(microsecond = 0) 
    # ldtz         = job.lastgeneratedon.replace(microsecond = 0) 
    # display_jobs_date_info(cdtz, mdtz, vfrom, vupto, ldtz)
    current_date= datetime.utcnow().replace(tzinfo=timezone.utc).replace(microsecond=0)
    current_date= current_date.replace(tzinfo = tz) + timedelta(minutes= ctzoffset)

    if mdtz > cdtz:
        ldtz = current_date
        # delete all old record
        del_job(job.id)
    startdtz = vfrom

    if ldtz > startdtz:
        startdtz = ldtz
    if startdtz < current_date:
        startdtz = current_date
        ldtz     = current_date
    enddtz = ((current_date + timedelta(days = 2)) - ldtz) + ldtz
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
    from croniter import croniter, CroniterBadCronError
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
    except CroniterBadCronError as ex:
        log.warning('Bad Cron error', exc_info = True)
        resp =  rp.JsonResponse({"errors": "Bad Cron Error"}, status = 404)
    except Exception as ex:
        log.error(
            'get_datetime_list(cron_exp, startdtz, enddtz) \
            Exception: [cronexp:= %s]croniter bad cron error:= %s'
            % (cron_exp, str(ex))
        )
        resp = rp.JsonResponse({"errors": "Bad Cron Error"}, status = 404)
        isValidCron = False
        log.error(
            'get_datetime_list(cron_exp, startdtz, enddtz) ERROR: ', exc_info = True)
        raise ex from ex
    if DT:
        log.info(f'Datetime list calculated are as follows:= {pformat(DT, compact = True)}')

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
            log.info(f"dt_local_to_utc got all date: {dtlist}")
            try:
                tzoffset= int(tzoffset)
                for item_ in dtlist:
                    udt= cdt= None
                    try:
                        udt = (
                            datetime.strptime(
                                str(item_), dateFormate
                            )
                            .replace(tzinfo = timezone.utc)
                            .replace(microsecond = 0)
                        )
                        cdt= udt - timedelta(minutes= tzoffset)
                        data[key] = str(data[key]).replace(str(item_), str(cdt))
                    except Exception as ex:
                        log.error("datetime parsing error", exc_info = True)
                        raise
            except ValueError:
                log.error("tzoffset parsing error", exc_info = True)
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
        log.info(f"got all date {dtlist}")
        try:
            tzoffset= int(tzoffset)
            for item in dtlist:
                udt= cdt= None
                try:
                    udt = (
                        datetime.strptime(str(item), dateFormate)
                        .replace(tzinfo = timezone.utc)
                        .replace(microsecond = 0)
                    )

                    cdt= udt - timedelta(minutes= tzoffset)
                    data = str(data).replace(str(item), str(cdt))
                except Exception as ex:
                    log.error("datetime parsing error", exc_info = True)
                    raise
        except ValueError:
            log.error("tzoffset parsing error", exc_info = True)
            raise

def insert_into_jn_and_jnd(job, DT, resp):
    """
        calculates expirydatetime for every dt in 'DT' list and
        inserts into jobneed and jobneed-details for all dates
        in 'DT' list.
    """
    log.info("insert_into_jn_and_jnd() [ start ]")
    status   = None
    if len(DT) > 0:
        try:
            # required variables
            NONE_JN  = utils.get_or_create_none_jobneed()
            NONE_P   = utils.get_or_create_none_people()
            crontype = job.identifier
            jobstatus = 'ASSIGNED'
            jobtype = 'SCHEDULE'
            assignee = job.pgroup.groupname if job.people_id == 1 else job.people.peoplename
            jobdesc = f'{job.jobname} :: {assignee}'
            asset = am.Asset.objects.get(id = job.asset_id)
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
                dt = datetime.strptime(dt, '%Y-%m-%d %H:%M').replace(tzinfo = timezone.utc)
                pdtz = params['pdtz'] = dt
                edtz = params['edtz'] = dt + timedelta(minutes = mins)
                log.debug(f'pdtz:={pdtz} edtz:={edtz}')
                jn = insert_into_jn_for_parent(job, params)
                isparent = crontype in (am.Job.Identifier.INTERNALTOUR.value, am.Job.Identifier.EXTERNALTOUR.value)
                insert_update_jobneeddetails(jn.id, job, parent = isparent)
                if isinstance(jn, am.Jobneed):
                    log.info(f"createJob() parent jobneed:= {jn.id}")
                    if crontype in (am.Job.Identifier.INTERNALTOUR.value, am.Job.Identifier.EXTERNALTOUR.value):
                        edtz = create_child_tasks(
                            job, pdtz, people, jn.id, jobstatus, jobtype)
                        if edtz is not None:
                            jn = am.Jobneed.objects.filter(id = jn.id).update(
                                expirydatetime = edtz
                            )
                            if jn <= 0:
                                raise ValueError
            update_lastgeneratedon(job, pdtz)
        except Exception as ex:
            status = 'failed'
            log.error('insert_into_jn_and_jnd() ERROR', exc_info = True)
            resp = rp.JsonResponse({
                "errors": "Failed to schedule jobs"}, status = 404)
            raise ex from ex
        else:
            status = "success"
            resp = rp.JsonResponse({'msg': f'{len(DT)} tasks scheduled successfully!', 'count':len(DT)}, status = 200)

        log.info("insert_into_jn_and_jnd() [ End ]")
        return status, resp

def insert_into_jn_for_parent(job, params):
    try:
        jn = am.Jobneed.objects.create(
            job_id         = job.id,                     parent            = params['NONE_JN'],
            jobdesc        = params['jobdesc'],          plandatetime      = params['pdtz'],
            expirydatetime = params['edtz'],             gracetime         = job.gracetime,
            asset_id       = job.asset_id,               qset_id           = job.qset_id,
            ctzoffset      = job.ctzoffset,              people_id         = params['people'],
            pgroup_id      = job.pgroup_id,              frequency         = 'NONE',
            priority       = job.priority,               jobstatus         = params['jobstatus'],
            performedby    = params['NONE_P'],           jobtype           = params['jobtype'],
            scantype       = job.scantype,               identifier        = job.identifier,
            cuser_id       = job.cuser_id,               muser_id          = job.muser_id,
            bu_id          = job.bu_id,                  ticketcategory_id = job.ticketcategory_id,
            gpslocation    = 'POINT(0.0 0.0)',             remarks           = '',
            seqno          = 0,                          multifactor       = params['m_factor'],
            client_id      = job.client_id,
        )
    except Exception:
        raise
    else:
        return jn



def insert_update_jobneeddetails(jnid, job, parent = False):
    log.info("insert_update_jobneeddetails() [START]")
    from django.utils.timezone import get_current_timezone
    tz = get_current_timezone()
    try:
        am.JobneedDetails.objects.get(jobneed_id = jnid).delete()
    except am.JobneedDetails.DoesNotExist:
        pass
    try:
        if not parent:
            qsb = am.QuestionSetBelonging.objects.select_related(
                'question').filter(
                    qset_id = job.qset_id).order_by(
                        'seqno').values_list(named = True)
        else:
            qsb = utils.get_or_create_none_qsetblng()
        if not qsb:
            log.error("No Checklist Found failed to schedhule job",
                      exc_info = True)
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
            seqno      = qsb.seqno,      question_id = qsb.question_id,
            answertype = qsb.answertype, max         = qsb.max,
            min        = qsb.min,        alerton     = qsb.alerton,
            options    = qsb.options,    jobneed_id  = jnid,
            cuser_id   = job.cuser_id,   muser_id    = job.muser_id,
            ctzoffset  = job.ctzoffset)
    except Exception:
        raise
    log.info("insert_into_jnd() [END]")

def extract_seq(R):
    return [r.seqno for r in R]


def check_sequence_of_prevjobneed(job, current_seq):
    R = am.Jobneed.objects.filter(parent_id=1, job_id=job.id).values_list('seqno', flat=True).order_by('-id')
    if len(R) > 1:
        ic(R[1], current_seq)
        return list(R[1]) == current_seq
    
    



def create_child_tasks(job, _pdtz, _people, jnid, _jobstatus, _jobtype):
    try:
        prev_edtz = None
        NONE_P = utils.get_or_create_none_people()
        from django.utils.timezone import get_current_timezone
        tz = get_current_timezone()
        mins = pdtz = edtz = None
        R = am.Job.objects.annotate(
            cplocation = F('bu__gpslocation')
            ).filter(
            parent_id = job.id).order_by(
                'seqno').values_list(named = True)
        log.info(f"create_child_tasks() total child job:={len(R)}")
        prev_edtz = _pdtz
        params = {'_jobdesc': "", 'jnid':jnid, 'pdtz':None, 'edtz':None,
                  '_people':_people, '_jobstatus':_jobstatus, '_jobtype':_jobtype,
                  'm_factor':None, 'idx':None, 'NONE_P':NONE_P}
        
        if job.other_info['is_randomized'] in ['True', True] and len(R) > 1:
            #randomize data if it is random tour job
            L = list(R)
            while True:
                shuffle(L)
                seq = extract_seq(L)
                if not check_sequence_of_prevjobneed(job, seq):
                    break
            R = calculate_route_details(L, job)  
            
            
        for idx, r in enumerate(R):
            log.info(f"create_child_tasks() [{idx}] child job:= {r.jobname} | job:= {r.id} | cron:= {r.cron}")

            asset = am.Asset.objects.get(id = r.asset_id)
            params['m_factor'] = asset.asset_json['multifactor']
            _assetname = asset.assetname if r.identifier == 'INTERNALTOUR' else r.qset.qsetname

            mins = job.planduration + r.expirytime + job.gracetime
            params['_people'] = r.people_id
            params['_jobdesc'] = f"{_assetname} :: {r.jobname}"
            if idx == 0:
                pdtz = params['pdtz'] = prev_edtz
            else:
                pdtz = params['pdtz'] = prev_edtz - \
                    timedelta(minutes = r.expirytime + job.gracetime)
            edtz = params['edtz'] = pdtz + timedelta(minutes = mins)
            prev_edtz = edtz
            params['idx'] = idx
            jn = insert_into_jn_for_child(job, params, r)
            insert_update_jobneeddetails(jn.id, r)
    except Exception:
        log.error(
            "create_child_tasks() ERROR failed to create task's", exc_info = True)
        raise
    else:
        log.info("create_child_tasks() successfully created [ END ]")
        return edtz


def insert_into_jn_for_child(job, params, r):
    try:
        jn = am.Jobneed.objects.create(
                job_id         = job.id,                     parent_id         = params['jnid'],
                jobdesc        = params['_jobdesc'],         plandatetime      = params['pdtz'],
                expirydatetime = params['edtz'],             gracetime         = job.gracetime,
                asset_id       = r.asset_id,                 qset_id           = r.qset_id,
                pgroup_id      = job.pgroup_id,              frequency         = 'NONE',
                priority       = r.priority,                 jobstatus         = params['_jobstatus'],
                client_id      = r.client_id,                jobtype           = params['_jobtype'],
                scantype       = job.scantype,               identifier        = job.identifier,
                cuser_id       = r.cuser_id,                 muser_id          = r.muser_id,
                bu_id          = r.bu_id,                    ticketcategory_id = r.ticketcategory_id,
                gpslocation    = 'SRID=4326;POINT(0.0 0.0)', remarks           = '',
                seqno          = params['idx'],              multifactor       = params['m_factor'],
                performedby    = params['NONE_P'],           ctzoffset         = r.ctzoffset,
                people_id      = params['_people'],
            )
    except Exception:
        raise
    else:
        return jn


def job_fields(job, checkpoint, external = False):
    data =  {
        'jobname'     : f"{checkpoint.get('assetname', '')} :: {job.jobname}",     'jobdesc'        : f"{checkpoint.get('assetname', '')} :: {job.jobname} :: {checkpoint['qsetname']}",
        'cron'        : job.cron,                      'identifier'     : job.identifier,
        'expirytime'  : int(checkpoint['expirytime']), 'lastgeneratedon': job.lastgeneratedon,
        'priority'    : job.priority,                  'qset_id'        : checkpoint['qsetid'],
        'pgroup_id'   : job.pgroup_id,                 'geofence'       : job.geofence_id,
        'endtime'     : datetime.strptime(checkpoint.get('endtime', "00:00"), "%H:%M"),                   'ticketcategory' : job.ticketcategory,
        'fromdate'    : job.fromdate,                  'uptodate'       : job.uptodate,
        'planduration': job.planduration,              'gracetime'      : job.gracetime,
        'asset_id'    : checkpoint['assetid'],           'frequency'      : job.frequency,
        'people_id'   : job.people_id,                 'starttime'      : datetime.strptime(checkpoint.get('starttime', "00:00"), "%H:%M"),
        'parent_id'   : job.id,                        'seqno'          : checkpoint['seqno'],
        'scantype'    : job.scantype,                  'ctzoffset'      : job.ctzoffset
    }
    if external:
        jsonData = {
            'distance'      : checkpoint['distance'],
            'breaktime'     : checkpoint['breaktime'],
            'is_randomized' : job.other_info['is_randomized'],
            'tour_frequency': job.other_info['tour_frequency']}
        data['jobname']    = f"{checkpoint['buname']} :: {job.jobname}"
        data['jobdesc']    = f"{checkpoint.get('buname', '')} :: {job.jobname} :: {checkpoint['qsetname']}"
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
        log.error('delete_from_job() raised  error', exc_info=True)
        raise

def delete_from_jobneed(parentjob, checkpointId, checklistId):
    try:
        am.Jobneed.objects.get(
            parent     = int(parentjob),
            asset_id = int(checkpointId),
            qset_id  = int(checklistId)).delete()
    except Exception:
        log.error("delete_from_jobneed() raised error", exc_info=True)
        raise

def update_lastgeneratedon(job, pdtz):
    try:
        log.info('update_lastgeneratedon [start]')
        if rec := am.Job.objects.filter(id = job.id).update(
            lastgeneratedon = pdtz
        ):
            log.info(f"after lastgenreatedon:={pdtz}")
        log.info('update_lastgeneratedon [end]')
    except Exception:
        log.error("update_lastgeneratedon() raised error", exc_info=True)
        raise

def send_email_notication(err):
    raise NotImplementedError()

def del_job(id):
    log.info("deleting old jobs start[+]")
    jobs = am.Job.objects.filter(parent_id__in = [id]).exclude(id=1).values_list(named=True)
    jobids = [job.id for job in jobs]
    #update jobneedetails and jobneed
    olddate = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    oldjobneeds = am.Jobneed.objects.filter(plandatetime__gt = datetime.now(timezone.utc), job_id__in = jobids).values_list("id", flat=True)
    am.JobneedDetails.objects.filter(jobneed_id__in = oldjobneeds).update(cdtz = olddate, mdtz=olddate)
    am.Jobneed.objects.filter(job_id__in=jobids, plandatetime__gt=datetime.now(timezone.utc)).update(cdtz=olddate, mdtz=olddate, plandatetime=olddate, expirydatetime=olddate)

    am.Job.objects.filter(id=id).exclude(id=1).update(cdtz = F('mdtz'))
    log.info("deleting old jobs end[-]")

