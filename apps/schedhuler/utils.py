from django.db.models import Q, F, Subquery
from django.core.exceptions import EmptyResultSet
from django.db import transaction, DatabaseError
from django.http import response as rp
import apps.activity.models as am
from apps.y_helpdesk.models import Ticket, EscalationMatrix
from logging import getLogger
from pprint import pformat
from random import shuffle
from apps.core import utils
from datetime import datetime, timezone, timedelta
from django.utils import timezone as dtimezone
from django.db.models.query import QuerySet
from apps.reminder.models import Reminder
import random
import traceback as tb
from intelliwiz_config.celery import app
from celery import shared_task
from celery.utils.log import get_task_logger
log = get_task_logger('__main__')

def create_dynamic_job(jobids=None):
    try:
        jobs = am.Job.objects.filter(
            ~Q(jobname='NONE'),
            ~Q(asset__runningstatus = am.Asset.RunningStatus.SCRAPPED),
            parent_id = 1,
            enable = True,
            other_info__isdynamic=True
        ).select_related('asset').values(*utils.JobFields.fields)
        if jobids:
            jobs = jobs.filter(id__in = jobids)
        for job in jobs:
            asset = am.Asset.objects.get(id = job['asset_id'])
            jobstatus = 'ASSIGNED'
            jobtype = 'SCHEDULE'
            people = job['people_id']
            multiplication_factor = asset.asset_json['multifactor']
            NONE_JN  = utils.get_or_create_none_jobneed()
            NONE_P   = utils.get_or_create_none_people()
            params = {
                'm_factor':multiplication_factor,'jobtype':jobtype,
                'jobstatus':jobstatus, 'NONE_JN':NONE_JN, 'NONE_P':NONE_P,
                'jobdesc':job['jobname'], 'people':people,
                'sgroup_id':job['sgroup_id'], 'qset_id':job['qset_id'],
            }
            with transaction.atomic(using=utils.get_current_db_name()):
                jn = insert_into_jn_dynamic_for_parent(job, params)
                insert_update_jobneeddetails(jn.id, job, parent = True)
                resp = create_child_dynamic_tasks(job,people, jn.id, jobstatus, jobtype, jn.other_info)
                return resp
    except Exception as e:
        log.error("something went wrong in dynamic tour scheduling", exc_info=True)
        return {"errors":"Something Went Wrong!"}
    
    



@shared_task(name="create_job()")
def create_job(jobids = None):
    startdtz = enddtz = msg = resp = None
    result = {'story':[]}

    from django.utils.timezone import get_current_timezone
    with transaction.atomic(using = utils.get_current_db_name()):
        try:
            jobs = am.Job.objects.filter(
                ~Q(jobname='NONE'),
                ~Q(cron='* * * * *'),
                ~Q(asset__runningstatus = am.Asset.RunningStatus.SCRAPPED),
                parent_id = 1,
                enable = True,
                other_info__isdynamic=False,
            ).select_related(
                "asset", "pgroup",
                "cuser", "muser", "qset", "people",
            ).values(*utils.JobFields.fields)
            if jobids:
                jobs = jobs.filter(id__in = jobids)
            


            if not jobs:
                msg = "No jobs found schedhuling terminated"
                resp = {'msg':f"{msg}"}
                log.warning(f"{msg}", exc_info = True)
            total_jobs = len(jobs)

            if total_jobs > 0 or jobs is not None:
                log.info("\nprocessing jobs started found:= '%s' jobs", (len(jobs)))
                for idx, job in enumerate(jobs):
                    startdtz, enddtz = calculate_startdtz_enddtz(job)
                    log.debug(f"Jobs to be schedhuled from startdatetime {startdtz} to enddatetime {enddtz}")

                    DT, is_cron, resp = get_datetime_list(job['cron'], startdtz, enddtz, resp)
                    if not DT: 
                        resp =  {'msg':"Please check your Valid From and Valid To dates"}
                        continue
                    log.debug(
                        "Jobneed will going to create for all this datetimes\n %s", (pformat(get_readable_dates(DT))))
                    status, resp = insert_into_jn_and_jnd(job, DT, resp)
                    result['story'].append(resp)
        except Exception as e:
            log.critical("something went wrong!", exc_info=True)
    return resp, result

def calculate_startdtz_enddtz(job):
    """
    this function determines or calculates what is 
    the plandatetime & expirydatetime of a job for next 2 days or upto
    uptodate.
    """

    log.info(f"calculating startdtz, enddtz for job:= [{job['id']}]")
    tz = timezone(timedelta(minutes = int(job['ctzoffset'])))
    ctzoffset = job['ctzoffset']

    cdtz         = job['cdtz'].replace(microsecond = 0, tzinfo = tz) + timedelta(minutes = ctzoffset)
    mdtz         = job['mdtz'].replace(microsecond = 0, tzinfo = tz)  + timedelta(minutes = ctzoffset)
    vfrom        = job['fromdate'].replace(microsecond = 0, tzinfo = tz)  + timedelta(minutes = ctzoffset)
    vupto        = job['uptodate'].replace(microsecond = 0, tzinfo = tz) + timedelta(minutes = ctzoffset)
    ldtz         = job['lastgeneratedon'].replace(microsecond = 0, tzinfo = tz) + timedelta(minutes = ctzoffset)
    current_date= datetime.utcnow().replace(tzinfo=timezone.utc).replace(microsecond=0)
    current_date= current_date.replace(tzinfo = tz) + timedelta(minutes= ctzoffset)

    if mdtz > cdtz:
        ldtz = current_date
        # delete all old record
        delete_old_jobs(job['id'])
    startdtz = vfrom

    if ldtz > vfrom:
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
    log.info("getting datetime list for cron:=%s, starttime:= '%s' and endtime:= '%s'", cron_exp, startdtz, enddtz)
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
        isValidCron = False
        log.warning('Bad Cron error', exc_info = True)
        resp =  {"errors": "Bad Cron Error"}
    except Exception as ex:
        log.critical(
            'get_datetime_list(cron_exp, startdtz, enddtz) \
            Exc(eption: [cronexp:= %s]croniter bad cron error:= %s', cron_exp, str(ex), exc_info=True)
        resp ={"errors": "Bad Cron Error"}
        isValidCron = False
        log.error(
            'get_datetime_list(cron_exp, startdtz, enddtz) ERROR: ', exc_info = True)
        raise ex from ex
    if DT:
        log.info(f'Datetime list calculated are as follows:= {pformat(DT, compact = True)}')
    else: resp = {"errors": "Unable to schedule task, check your 'Valid From' and 'Valid To'"}

    log.info("get_datetime_list(cron_exp, startdtz, enddtz) [end]")
    return DT, isValidCron, resp


def insert_into_jn_and_jnd(job, DT, resp):
    """
        calculates expirydatetime for every dt in 'DT' list and
        inserts into jobneed and jobneed-details for all dates
        in 'DT' list.
    """
    log.info("insert_into_jn_and_jnd() [ start ]")
    status, resp, tracebackExp   = None, None, None
    if len(DT) > 0:
        try:
            # required variables
            NONE_JN  = utils.get_or_create_none_jobneed()
            NONE_P   = utils.get_or_create_none_people()
            crontype = job['identifier']
            jobstatus = 'ASSIGNED'
            jobtype = 'SCHEDULE'
            #assignee = job.pgroup.groupname if job['people_id'] == 1 else job.people.peoplename
            jobdesc = f'{job["jobname"]}'
            asset = am.Asset.objects.get(id = job['asset_id'])
            multiplication_factor = asset.asset_json['multifactor']
            mins = pdtz = edtz = people = jnid = None
            parent = people = -1

            mins = job['planduration'] + job['expirytime'] + job['gracetime']
            people = job['people_id']
            params   = {
                'jobstatus':jobstatus, 'jobtype':jobtype, 'route_name':job['sgroup__groupname'],
                'm_factor':multiplication_factor, 'people':people, 'qset_id':job['qset_id'],
                'NONE_P':NONE_P, 'jobdesc':jobdesc, 'NONE_JN':NONE_JN, 'sgroup_id':job['sgroup_id']}
            UTC_DT = utils.to_utc(DT)
            for dt in UTC_DT:
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
                            job, pdtz, people, jn.id, jobstatus, jobtype, jn.other_info)
                        if edtz is not None:
                            jn = am.Jobneed.objects.filter(id = jn.id).update(
                                expirydatetime = edtz
                            )
                            if jn <= 0:
                                raise ValueError
            update_lastgeneratedon(job, pdtz)
        except Exception as ex:
            status = 'failed'
            tracebackExp = tb.format_exc()
            log.critical('insert_into_jn_and_jnd() ERROR', exc_info = True)
            resp = {
                "errors": "Failed to schedule jobs"}
            raise ex from ex
        else:
            status = "success"
            resp = {'msg': f'{len(DT)} tasks scheduled successfully!', 'count':len(DT), 'job_id':job['id'], 'traceback':tracebackExp}

        log.info("insert_into_jn_and_jnd() [ End ]")
    return status, resp
    
def insert_into_jn_dynamic_for_parent(job, params):
    defaults={
            'ctzoffset'        : job['ctzoffset'],
            'priority'         : job['priority'],
            'identifier'       : job['identifier'],
            'gpslocation'      : 'POINT(0.0 0.0)',
            'remarks'          : '',
            'multifactor'      : params['m_factor'],
            'client_id'        : job['client_id'],
            'other_info'       : job['other_info'],
            'cuser_id'         : job['cuser_id'],
            'muser_id'         : job['muser_id'],
            'ticketcategory_id': job['ticketcategory_id'],
            'frequency'        : 'NONE',
            'bu_id'            : job['bu_id'],
            'seqno'            : 0,
            'scantype'         : job['scantype'],
            'gracetime'    : job['gracetime'],
            'performedby'    : params['NONE_P'],
            'jobstatus'      : params['jobstatus'],
            'jobdesc' : params['jobdesc'],
            'qset_id' : params['qset_id'],
            'sgroup_id' : params['sgroup_id'],
            'asset_id' : job['asset_id'],
            'people_id' : job['people_id'],
            'pgroup_id' : job['pgroup_id'],
            'parent' : params['NONE_JN'],
        }
    obj = am.Jobneed.objects.create(
        job_id         = job['id'],
        jobtype        = params['jobtype'],
        **defaults
    )
    return obj


    
def insert_into_jn_for_parent(job, params):
    defaults={
            'ctzoffset'        : job['ctzoffset'],
            'priority'         : job['priority'],
            'identifier'       : job['identifier'],
            'gpslocation'      : 'POINT(0.0 0.0)',
            'remarks'          : '',
            'multifactor'      : params['m_factor'],
            'client_id'        : job['client_id'],
            'other_info'       : job['other_info'],
            'cuser_id'         : job['cuser_id'],
            'muser_id'         : job['muser_id'],
            'ticketcategory_id': job['ticketcategory_id'],
            'frequency'        : 'NONE',
            'bu_id'            : job['bu_id'],
            'seqno'            : 0,
            'scantype'         : job['scantype'],
            'gracetime'    : job['gracetime'],
            'performedby'    : params['NONE_P'],
            'jobstatus'      : params['jobstatus'],
            'jobdesc' : params['jobdesc'],
            'qset_id' : params['qset_id'],
            'sgroup_id' : params['sgroup_id'],
            'asset_id' : job['asset_id'],
            'people_id' : job['people_id'],
            'pgroup_id' : job['pgroup_id'],
            'parent' : params['NONE_JN'],
        }
    obj, iscreated = am.Jobneed.objects.get_or_create(
        defaults=defaults,
        job_id         = job['id'],
        jobtype        = params['jobtype'],
        plandatetime = params['pdtz'],
        expirydatetime = params['edtz'],
        parent = params['NONE_JN'],
    )
    log.info("{}".format("record is created" if iscreated else "record is not created"))
    return obj


    
def insert_update_jobneeddetails(jnid, job, parent=False):
    # sourcery skip: use-contextlib-suppress
    log.info("insert_update_jobneeddetails() [START]")
    from django.utils.timezone import get_current_timezone
    tz = get_current_timezone()
    try:
        am.JobneedDetails.objects.filter(jobneed_id=jnid).delete()
    except am.JobneedDetails.DoesNotExist:
        pass
    try:
        qsb = utils.get_or_create_none_qsetblng() if parent else am.QuestionSetBelonging.objects.select_related('question').filter(qset_id=job['qset_id']).order_by('seqno').values_list(named=True)
        if qsb:
            log.info(f'Checklist found with {len(qsb) if isinstance(qsb, QuerySet) else 1} questions in it.')
            insert_into_jnd(qsb, job, jnid, parent)
    except Exception:
        raise
    log.info("insert_update_jobneeddetails() [END]")
    

def create_child_tasks(job, _pdtz, _people, jnid, _jobstatus, _jobtype, parent_other_info):
    try:
        prev_edtz, tour_freq = None, 1
        NONE_P  = utils.get_or_create_none_people()
        from django.utils.timezone import get_current_timezone
        tz = get_current_timezone()
        mins = pdtz = edtz = None
        R = am.Job.objects.annotate(
            cplocation = F('bu__gpslocation')
            ).filter(
            parent_id = job['id']).order_by(
                'seqno').values(*utils.JobFields.fields, 'cplocation', 'sgroup__groupname', 'bu__solid', 'bu__buname')

        log.info(f"create_child_tasks() total child job:={len(R)}")
        
        params = {'_jobdesc': "", 'jnid':jnid, 'pdtz':None, 'edtz':None,
                  '_people':_people, '_jobstatus':_jobstatus, '_jobtype':_jobtype,
                  'm_factor':None, 'idx':None, 'NONE_P':NONE_P, 'parent_other_info':parent_other_info}
        L = list(R)
        if job['other_info']['is_randomized'] in ['True', True] and len(R) > 1:
            #randomize data if it is random tour job
            random.shuffle(L)
            R = calculate_route_details(L, job)
            tour_freq = int(job['other_info']['tour_frequency'])
        elif job['other_info']['tour_frequency'] and int(job['other_info']['tour_frequency']) > 1:
            tour_freq = int(job['other_info']['tour_frequency'])
            R = calculate_route_details(L, job)
            
        prev_edtz = _pdtz
        brektime_idx = len(R)//tour_freq
        for idx, r in enumerate(R):
            log.info(f"create_child_tasks() [{idx}] child job:= {r['jobname']} | job:= {r['id']} | cron:= {r['cron']}")

            asset = am.Asset.objects.get(id = r['asset_id'])
            params['m_factor'] = asset.asset_json['multifactor']
            jobdescription = f"{r['asset__assetname']} - {r['jobname']}" 
            
            if r['identifier'] == 'EXTERNALTOUR':
                jobdescription = f"{job['sgroup__groupname']} - {r['bu__solid']} - {r['bu__buname']}" 

            mins = job['planduration'] + r['expirytime'] + job['gracetime']
            params['_people'] = r['people_id']
            params['_jobdesc'] = jobdescription
            
            
            if job['other_info']['tour_frequency'] and int(job['other_info']['tour_frequency']) > 1 and job['other_info']['breaktime'] and brektime_idx == idx:
                pdtz = params['pdtz'] = prev_edtz + timedelta(minutes=int(job['other_info']['breaktime']) + r['expirytime'])
            else:
                pdtz = params['pdtz'] = prev_edtz + timedelta(minutes=r['expirytime'])
            edtz = params['edtz'] = pdtz + timedelta(minutes=job['planduration'] + job['gracetime'])
            prev_edtz = edtz

            
            params['idx'] = idx
            jn = insert_into_jn_for_child(job, params, r)
            insert_update_jobneeddetails(jn.id, r)
    except Exception:
        log.critical(
            "create_child_tasks() ERROR failed to create task's", exc_info = True)
        raise
    else:
        log.info("create_child_tasks() successfully created [ END ]")
        return edtz


def create_child_dynamic_tasks(job,  _people, jnid, _jobstatus, _jobtype, parent_other_info):
    try:
        prev_edtz, tour_freq = None, 1
        NONE_P  = utils.get_or_create_none_people()
        from django.utils.timezone import get_current_timezone
        tz = get_current_timezone()
        mins = pdtz = edtz = None
        R = am.Job.objects.annotate(
            cplocation = F('bu__gpslocation')
            ).filter(
            parent_id = job['id']).order_by(
                'seqno').values(*utils.JobFields.fields, 'cplocation', 'sgroup__groupname', 'bu__solid', 'bu__buname')

        log.info(f"create_child_tasks() total child job:={len(R)}")
        
        params = {'_jobdesc': "", 'jnid':jnid, 'pdtz':None, 'edtz':None,
                  '_people':_people, '_jobstatus':_jobstatus, '_jobtype':_jobtype,
                  'm_factor':None, 'idx':None, 'NONE_P':NONE_P, 'parent_other_info':parent_other_info}
            
        for idx, r in enumerate(R):
            log.info(f"create_child_tasks() [{idx}] child job:= {r['jobname']} | job:= {r['id']} | cron:= {r['cron']}")

            asset = am.Asset.objects.get(id = r['asset_id'])
            params['m_factor'] = asset.asset_json['multifactor']
            jobdescription = f"{r['asset__assetname']} - {r['jobname']}"
            

            mins = job['planduration'] + r['expirytime'] + job['gracetime']
            params['_people'] = r['people_id']
            params['_jobdesc'] = jobdescription

            params['idx'] = idx
            jn = insert_into_jn_for_child(job, params, r)
            insert_update_jobneeddetails(jn.id, r)
    except Exception:
        log.critical(
            "create_child_tasks() ERROR failed to create task's", exc_info = True)
        return {'errors':"Failed to schedule Tour"}
    else:
        log.info("create_child_tasks() successfully created [ END ]")
        return {'msg':"Dynamic Tour Scheduled!"}



def calculate_route_details(R, job):
    data = R
    import googlemaps
    gmaps = googlemaps.Client(key='AIzaSyDVbA53nxHKUOHdyIqnVPD01aOlTitfVO0')
    startpoint, endpoint, waypoints = get_service_requirements(data)
    directions = gmaps.directions(mode='driving', waypoints=waypoints, origin=startpoint, destination=endpoint, optimize_waypoints=True)

    directions = gmaps.directions(mode='driving', waypoints=waypoints, origin=startpoint, destination=endpoint, optimize_waypoints=True)

    waypoint_order = directions[0]["waypoint_order"]
    freq, breaktime = job['other_info']['tour_frequency'], job['other_info']['breaktime']

    data[0]['seqno'] = 0 + 1
    #startpoint
    chekpoints = [data[0]]
    chekpoints[0]['distance'] = 0
    chekpoints[0]["duration"] = 0
    chekpoints[0]["expirytime"] = 0
    
    #waypoints
    for i, item in enumerate(waypoint_order):
        data[i + 1]['seqno'] = i + 1 + 1
        chekpoints.append(data[item + 1])
    
    #endpoint
    data[len(data)-1]["seqno"] = len(data)-1+1    
    chekpoints.append(data[len(data)-1])
    
    legs = directions[0]["legs"]
    j = 1
    DDE = []
    for i, item in enumerate(legs):
        l=[]
        chekpoints[j]['distance']=round(float(item['distance']["value"]/1000), 2)
        l.append(chekpoints[j]["distance"])
        chekpoints[j]['duration']=float(legs[i]["duration"]["value"])
        l.append(chekpoints[j]['duration'])
        chekpoints[j]['expirytime']=int(legs[i]["duration"]["value"]/60)
        l.append(chekpoints[j]['expirytime'])
        DDE.append(l)
        j += 1
    if freq and freq > 1:
        checkpoints = get_frequencied_data(DDE, chekpoints, freq, breaktime)
    if freq and freq > 1 and breaktime != 0:
        endp = int(len(chekpoints) / freq)
        chekpoints[endp]['breaktime'] = breaktime
    return chekpoints
    
    
    
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
    
    
def get_frequencied_data(DDE, data, f, breaktime):
    """
    Randomize data based on frequency
    """
    import copy

    R, dataCopy = [], copy.deepcopy(data)
    for _ in range(f-1):
        R=data
        R+=reversedFPoints(DDE, dataCopy, breaktime)
        
        
        

def get_service_requirements(R):
    """
    returns startpoint, endpoint, waypoints
    required for directions api
    """
    if R:
        startp = {"lat":float(R[0]['cplocation'].coords[1]),
                  "lng":float(R[0]['cplocation'].coords[0])}

        endp = {"lat":float(R[-1]['cplocation'].coords[1]),
               "lng":float(R[-1]['cplocation'].coords[0])}
        waypoints=[]
        for i in range(1, len(R)-1):
            lat, lng = R[i]['cplocation'].coords[1], R[i]['cplocation'].coords[0]
            waypoints.append(
                {"lat":lat, "lng":lng}
            )
        return startp, endp, waypoints



def delete_old_jobs(job_id, ppm=False):
    """
    Delete old jobs and related data based on the given job ID.
    """
    # Get a list of related job IDs and include the given ID if ppm is True.
    job_ids = am.Job.objects.filter(parent_id=job_id).values_list('id', flat=True)
    job_ids = [job_id] + list(job_ids)

    # Set the old date to 1970-01-01 00:00:00 UTC.
    old_date = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Update jobneeddetails
    jobneed_ids = am.Jobneed.objects.filter(plandatetime__gt=dtimezone.now(), job_id__in=job_ids).values_list('id', flat=True)
    jnd_count = am.JobneedDetails.objects.filter(jobneed_id__in=jobneed_ids).update(cdtz=old_date, mdtz=old_date)

    # Update jobneeds
    jn_count = am.Jobneed.objects.filter(
        job_id__in=job_ids, plandatetime__gt=dtimezone.now()).update(
            cdtz=old_date, mdtz=old_date, plandatetime=old_date, expirydatetime=old_date)

    # Update job
    am.Job.objects.filter(id=job_id).update(cdtz=F('mdtz'))

    # Log the results
    log.info('Deleted %s jobneedetails and %s jobneeds for job ID %s', jnd_count, jn_count, job_id)


def del_ppm_reminder(jobid):
    log.info('del_ppm_reminder start +')
    Reminder.objects.filter(reminderdate__gt = datetime.now(timezone.utc), job_id = jobid).delete()
    log.info('del_ppm_reminder end -')


def calculate_startdtz_enddtz_for_ppm(job): 
    log.info(f"calculating startdtz, enddtz for job:= [{job['id']}]")
    tz = timezone(timedelta(minutes = int(job['ctzoffset'])))
    ctzoffset = job['ctzoffset']

    current_date = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    cdtz         = job['cdtz'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    mdtz         = job['mdtz'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    vfrom        = job['fromdate'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    vupto        = job['uptodate'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)
    ldtz         = job['lastgeneratedon'].replace(microsecond=0, tzinfo=tz) + timedelta(minutes=ctzoffset)

    if mdtz > cdtz:
        ldtz = current_date
        delete_old_jobs(job['id'], True)
        del_ppm_reminder(job['id'])

    startdtz = max(current_date, vfrom)
    enddtz = vupto
    startdtz = max(startdtz, ldtz)

    if startdtz < current_date:
        ldtz = current_date
    return startdtz, enddtz
    
    
def create_ppm_reminder(jobs):
    try:
        #FOR EVERY JOB
        for job in jobs:
            if job['count'] <= 0:
                continue
            #EXTRACT REMINDER CONFIG (FROM ESCMATRIX)
            esm = EscalationMatrix.objects.select_related('job', 'assignedgroup', 'assignedperson', 'bu').filter(job_id=job['job'])
            #RETRIVE JOBNEEDS
            jobneeds = am.Jobneed.objects.select_related('job', 'asset', 'qset', 'bu', 'client', 'people', 'pgroup').filter(
                plandatetime__gt=datetime.now(), job_id=job['job'])
            
            if not esm or not jobneeds:
                continue
            
            #FOR EVERY JOBNEED
            for jn in jobneeds:
                log.info(f'create_ppm_reminder() jobneed:{jn.id} plandatetime {jn.plandatetime} jobdesc {jn.jobdesc} buid {jn.bu_id} asset_id {jn.asset_id} qsetid {jn.qset_id}')
                assignto = "GROUP" if jn.pgroup_id != 1 else "PEOPLE"
                #FOR EVERY REMINDER IN REMINDER CONFIG
                for r in esm:
                    log.debug(f"reminder : {pformat(r)}")
                    reminderdate = jn.plandatetime.replace(microsecond=0)

                    if r.frequency == "WEEK":
                        reminderbefore = int(r.frequencyvalue) * 7 * 24 * 60
                    elif r.frequency == "DAY":
                        reminderbefore = int(r.frequencyvalue) * 24 * 60
                    elif r.frequency == "HOUR":
                        reminderbefore = int(r.frequencyvalue) * 60
                    elif r.frequency == "MINUTE":
                        reminderbefore = int(r.frequencyvalue)
                    
                    reminderdate = reminderdate - timedelta(minutes=reminderbefore)
                    #CREATE REMINDER
                    Reminder.objects.create(
                        description    = jn.jobdesc,
                        bu_id          = jn.bu_id,
                        asset_id       = jn.asset_id,
                        qset_id        = jn.qset_id,
                        people_id      = jn.people_id,
                        group_id       = jn.pgroup_id,
                        priority       = jn.priority,
                        reminderin     = r.frequency,
                        reminderbefore = r.frequencyvalue,
                        reminderdate = reminderdate,
                        job_id         = jn.job_id,
                        jobneed_id     = jn.id,
                        plandatetime   = jn.plandatetime,
                        cuser_id       = jn.cuser_id,
                        muser_id       = jn.muser_id,
                        ctzoffset      = jn.ctzoffset,
                        mailids        = r.notify
                    )
    except Exception as e:
        log.critical("something went wrong inside create_ppm_reminder", exc_info=True)


#@shared_task(name="create_ppm_job")
def create_ppm_job(jobid=None):
    F, d = {}, []
    startdtz = enddtz = msg = resp = None
    try:
        with transaction.atomic(using=utils.get_current_db_name()):
            jobs = am.Job.objects.filter(
                ~Q(jobname='NONE'),
                ~Q(asset__runningstatus = am.Asset.RunningStatus.SCRAPPED),
                identifier = am.Job.Identifier.PPM.value,
                parent_id = 1
            ).select_related('asset', 'pgroup', 'cuser', 'muser', 'people', 'qset').values(
                *utils.JobFields.fields
            )
            if jobid:
                jobs = jobs.filter(id = jobid).values(*utils.JobFields.fields)


            if not jobs:
                msg = "No jobs found schedhuling terminated"
                resp = rp.JsonResponse(f"{msg}", status = 404)
                log.warning(f"{msg}", exc_info = True)
            total_jobs = len(jobs)

            if total_jobs > 0 and jobs is not None:
                log.info("processing jobs started found:= '%s' jobs", (len(jobs)))
                for job in jobs:
                    startdtz, enddtz = calculate_startdtz_enddtz_for_ppm(job)
                    log.debug(f"Jobs to be schedhuled from startdatetime {startdtz} to enddatetime {enddtz}")
                    DT, is_cron, resp = get_datetime_list(job['cron'], startdtz, enddtz, resp)
                    log.debug(
                        "Jobneed will going to create for all this datetimes\n %s", (pformat(get_readable_dates(DT))))
                    if not is_cron: F[str(job['id'])] = job['cron']
                    status, resp = insert_into_jn_and_jnd(job, DT, resp)
                    if status:
                        d.append({
                            "job"   : job['id'],
                            "jobname" : job['jobname'],
                            "cron"    : job['cron'],
                            "iscron"  : is_cron,
                            "count"   : len(DT),
                            "status"  : status
                        })
                create_ppm_reminder(d)
                if F:
                    log.info(f"create_ppm_job Failed job schedule list:={pformat(F)}")
                    for key, value in list(F.items()):
                        log.info(f"create_ppm_job job_id: {key} | cron: {value}")
    except Exception as e:
        log.critical("something went wrong create_ppm_job", exc_info=True)
        
                

def send_reminder_email():
    #get all reminders which are not sent
    from django.template.loader import render_to_string
    from django.conf import settings
    from django.core.mail import  EmailMessage

    reminders = Reminder.objects.get_all_due_reminders()
    try:
        for rem in reminders:
            emails = utils.get_email_addresses([rem['people_id'], rem['cuser_id'], rem['muser_id']], [rem['group_id']])
            recipents = list(set(emails + rem['mailids'].split(',')))
            subject = f"Reminder For {rem['job__jobname']}"
            context = {'job':rem['job__jobname'], 'plandatetime':rem['pdate'], 'jobdesc':rem['job__jobdesc'],
                    'creator':rem['cuser__peoplename'],'modifier':rem['muser__peoplename']}
            html_message = render_to_string('reminder_mail.html', context=context)
            log.info(f"Sending reminder mail with subject {subject}")
            msg = EmailMessage()
            msg.subject = subject
            msg.body  = html_message
            msg.from_email = settings.EMAIL_HOST_USER
            msg.to = recipents
            msg.content_subtype = 'html'
            msg.send()
            log.info(f"Reminder mail sent to {recipents} with subject {subject}")
    except Exception as e:
        log.critical("Error while sending reminder email", exc_info=True)
        
        
def send_email_notication(err):
    raise NotImplementedError()


def job_fields(job, checkpoint, external = False):
    data =  {
        'jobname'     : f"{checkpoint.get('bu__buname', '')} :: {job['jobname']}",       'jobdesc'          : f"{checkpoint.get('bu__buname', '')} :: {job['jobname']} :: {checkpoint['qsetname']}",
        'cron'        : job['cron'],                                                    'identifier'       : job['identifier'],
            'expirytime'  : int(checkpoint['expirytime']),                                  'lastgeneratedon'  : job['lastgeneratedon'],
        'priority'    : job['priority'],                                                'qset_id'          : checkpoint['qsetid'],
        'pgroup_id'   : job['pgroup_id'],                                               'geofence'         : job['geofence_id'],
        'endtime'     : datetime.strptime(checkpoint.get('endtime', "00:00"), "%H:%M"), 'ticketcategory_id': job['ticketcategory_id'],
        'fromdate'    : job['fromdate'],                                                'uptodate'         : job['uptodate'],
        'planduration': job['planduration'],                                            'gracetime'        : job['gracetime'],
        'asset_id'    : checkpoint['assetid'],                                          'frequency'        : job['frequency'],
        'people_id'   : job['people_id'],                                               'starttime'        : datetime.strptime(checkpoint.get('starttime', "00:00"), "%H:%M"),
        'parent_id'   : job['id'],                                                      'seqno'            : checkpoint['seqno'],
        'scantype'    : job['scantype'],                                                'ctzoffset'        : job['ctzoffset'],
        'bu_id': job['bu_id'], 'client_id':job['client_id']
    }
    if external:
        jsonData = {
            'distance'      : checkpoint['distance'],
            'breaktime'     : checkpoint['breaktime'],
            'istimebound'   : job['other_info']['istimebound'],
            'is_randomized' : job['other_info']['is_randomized'],
            'tour_frequency': job['other_info']['tour_frequency']}
        data['jobname']    = f"{checkpoint['bu__buname']} :: {job['jobname']}"
        data['jobdesc']    = f"{checkpoint.get('bu__buname', '')} :: {job['jobname']} :: {checkpoint['qsetname']}"
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
        log.critical('delete_from_job() raised  error', exc_info=True)
        raise

def delete_from_jobneed(parentjob, checkpointId, checklistId):
    try:
        am.Jobneed.objects.get(
            parent     = int(parentjob),
            asset_id = int(checkpointId),
            qset_id  = int(checklistId)).delete()
    except Exception:
        log.critical("delete_from_jobneed() raised error", exc_info=True)
        raise

def update_lastgeneratedon(job, pdtz):
    try:
        log.info('update_lastgeneratedon [start]')
        if rec := am.Job.objects.filter(id = job['id']).update(
            lastgeneratedon = pdtz
        ):
            log.info(f"after lastgenreatedon:={pdtz}")
        log.info('update_lastgeneratedon [end]')
    except Exception:
        log.critical("update_lastgeneratedon() raised error", exc_info=True)
        raise
    
def get_readable_dates(dt_list):
    if (isinstance(dt_list, list)):
        return [dt.strftime("%d-%b-%Y %H:%M") for dt in dt_list]
    
    

def insert_into_jnd(qsb, job, jnid, parent=False):
    log.info("insert_into_jnd() [START]")
    qset = qsb if isinstance(qsb, QuerySet) else [qsb]
    for obj in qset:
        answer = 'NONE' if parent else None
        am.JobneedDetails.objects.create(
            seqno      = obj.seqno,      question_id = obj.question_id,
            answertype = obj.answertype, max         = obj.max,
            min        = obj.min,        alerton     = obj.alerton,
            options    = obj.options,    jobneed_id  = jnid,
            cuser_id   = job['cuser_id'],   muser_id    = job['muser_id'],
            ctzoffset  = job['ctzoffset'], answer = answer,
            isavpt = obj.isavpt, avpttype = obj.avpttype)
    log.info("insert_into_jnd() [END]")
    


def  insert_into_jn_for_child(job, params, r):
    try:
        jn = am.Jobneed.objects.create(
                job_id         = job['id'],                     parent_id         = params['jnid'],
                jobdesc        = params['_jobdesc'],         plandatetime      = params['pdtz'],
                expirydatetime = params['edtz'],             gracetime         = job['gracetime'],
                asset_id       = r['asset_id'],                 qset_id           = r['qset_id'],
                pgroup_id      = job['pgroup_id'],              frequency         = 'NONE',
                priority       = r['priority'],                 jobstatus         = params['_jobstatus'],
                client_id      = r['client_id'],                jobtype           = params['_jobtype'],
                scantype       = job['scantype'],               identifier        = job['identifier'],
                cuser_id       = r['cuser_id'],                 muser_id          = r['muser_id'],
                bu_id          = r['bu_id'],                    ticketcategory_id = r['ticketcategory_id'],
                gpslocation    = r['cplocation'], remarks           = '',
                seqno          = params['idx'],              multifactor       = params['m_factor'],
                performedby    = params['NONE_P'],           ctzoffset         = r['ctzoffset'],
                people_id      = params['_people'],          other_info = params['parent_other_info']
            )
    except Exception:
        log.error("insert_into_jn_for_child[]", exc_info=True)
        raise
    else:
        return jn