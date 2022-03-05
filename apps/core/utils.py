'''
DEFINE FUNCTIONS AND CLASSES WERE CAN BE USED GLOBALLY.
'''
import django.shortcuts as scts
from django.contrib import messages as msg
from django.template.loader import render_to_string
from django.http import response as rp
from flask import request
from pyrsistent import v
import apps.peoples.utils as putils
from pprint import pformat
from apps.peoples import models as pm
import logging
from apps.onboarding.models import  Bt, TypeAssist
import apps.activity.models as am
from django.db.models import Q
logger = logging.getLogger('__main__')
dbg = logging.getLogger('__main__').debug


def cache_it(key, val, time = 1*60):
    from django.core.cache import cache
    cache.set(key, val, time)
    logger.info('saved in cache %s'%(pformat(val)))


def get_from_cache(key):
    from django.core.cache import cache
    if data := cache.get(key):
        logger.info('Got from cache %s'%(key))
        return data
    else:
        logger.info('Not found in cache')
        return None


def render_form(request, params, cxt):
    logger.info("%s", cxt['msg'])
    html = render_to_string(params['template_form'], cxt, request)
    data = {"html_form": html}
    return rp.JsonResponse(data, status=200)


def handle_DoesNotExist(request):
    data = {'errors': 'Unable to edit object not found'}
    logger.error("%s", data['error'], exc_info=True)
    msg.error(request, data['error'], 'alert-danger')
    return rp.JsonResponse(data, status=404)


def handle_Exception(request, force_return=None):
    data = {'errors': 'Something went wrong'}
    logger.critical(data['errors'], exc_info=True)
    msg.error(request, data['errors'], 'alert-danger')
    if force_return:
        return force_return
    return rp.JsonResponse(data, status=404)


def handle_RestrictedError(request):
    data = {'errors': "Unable to delete, due to dependencies"}
    logger.warn("%s", data['error'], exc_info=True)
    msg.error(request, data['error'], "alert-danger")
    return rp.JsonResponse(data, status=404)


def handle_EmptyResultSet(request, params, cxt):
    logger.warn('empty objects retrieved', exc_info=True)
    msg.error(request, 'List view not found',
                   'alert-danger')
    return scts.render(request, params['template_list'], cxt)


def handle_intergrity_error(name):
    msg = 'The %s record of with these values is already exisit!' % (name)
    logger.info(msg, exc_info=True)
    return rp.JsonResponse({'errors': msg}, status=404)


def render_form_for_update(request, params, formname, obj, extra_cxt={}):
    logger.info("render form for update")
    try:
        logger.info("object retrieved '{}'".format(obj))
        F = params['form_class'](
            instance=obj, request=request, initial = params['form_initials'])
        ic(F.as_p().split('\n'))
        C = {formname: F, 'edit': True}
        C.update(extra_cxt)
        html = render_to_string(params['template_form'], C, request)
        data = {'html_form': html}
        return rp.JsonResponse(data, status=200)
    except params['model'].DoesNotExist:
        return handle_DoesNotExist(request)
    except Exception:
        return handle_Exception(request)


def render_form_for_delete(request, params, master=False):
    logger.info("render form for delete")
    from django.db.models import RestrictedError
    try:
        pk = request.GET.get('id')
        obj = params['model'].objects.get(id=pk)
        if master:
            obj.enable = False
            obj.save()
        else:
            obj.delete()
        return rp.JsonResponse({}, status=200)
    except params['model'].DoesNotExist:
        return handle_DoesNotExist(request)
    except RestrictedError:
        return handle_RestrictedError(request)
    except Exception:
        return handle_Exception(request, params)


def render_grid(request, params, msg, objs, extra_cxt = None):
    if extra_cxt is None:
        extra_cxt = {}
    
    from django.core.exceptions import EmptyResultSet
    logger.info("render grid")
    try:
        logger.info("%s", msg)
        logger.info('objects %s retrieved from db'%len(objs) if objs else "No Records!")
        logger.info("Pagination Starts"if objs else "")
        cxt = paginate_results(request, objs, params)
        logger.info("Pagination Ends" if objs else "")
        if extra_cxt: cxt.update(extra_cxt)
        resp = scts.render(request, params['template_list'], context=cxt)
    except EmptyResultSet:
        resp = handle_EmptyResultSet(request, params, cxt)
    except Exception:
        resp = handle_Exception(request, scts.redirect('/dashboard'))
    return resp


def paginate_results(request, objs, params):
    from django.core.paginator import (Paginator,
     EmptyPage, PageNotAnInteger)

    logger.info('paginate results'if objs else "")
    if request.GET:
        objs = params['filter'](request.GET, queryset=objs).qs
    filterform = params['filter']().form
    page = request.GET.get('page', 1)
    paginator = Paginator(objs, 15)
    try:
        li = paginator.page(page)
    except PageNotAnInteger:
        li = paginator.page(1)
    except EmptyPage:
        li = paginator.page(paginator.num_pages)
    return {params['list']: li, params['filt_name']: filterform}


def get_instance_for_update(postdata, params, msg, pk, kwargs={}):
    logger.info("%s", msg)
    obj = params['model'].objects.get(id=pk)
    logger.info("object retrieved '{}'".format(obj))
    return params['form_class'](postdata, instance=obj, **kwargs)


def handle_invalid_form(request, params, cxt):
    logger.info("form is not valid")
    return rp.JsonResponse(cxt, status=404)


def get_model_obj(pk, request, params):
    try:
        obj = params['model'].objects.get(id=pk)
    except params['model'].DoesNotExist:
        return handle_DoesNotExist(request)
    else:
        logger.info("object retrieved '{}'".format(obj))
        return obj


def local_to_utc(data, offset, mobile_web):
    from datetime import datetime, timedelta
    import pytz
    from django.utils.timezone import utc
    dateFormatMobile = "%Y-%m-%d %H:%M:%S"
    dateFormatWeb = "%d-%b-%Y %H:%M"
    format = dateFormatWeb if mobile_web == "web" else dateFormatMobile
    if isinstance(data, dict):
        try:
            for k, v in data.items():
                local_dt = datetime.strptime(v, format)
                dt_utc = local_dt.astimezone(pytz.UTC).replace(microsecond=0)
                data[k] = dt_utc.strftime(format)
        except Exception:
            logger.error("datetime parsing ERROR", exc_info=True)
            raise
        else:
            return data
    elif isinstance(data, list):
        try:
            newdata = []
            for dt in data:
                local_dt = datetime.strptime(dt, format)
                dt_utc = local_dt.astimezone(pytz.UTC).replace(microsecond=0)
                dt = dt_utc.strftime(format)
                newdata.append(dt)
        except Exception:
            logger.error("datetime parsing ERROR", exc_info=True)
            raise
        else:
            return newdata


def get_or_create_none_people(using=None):
    obj, _ = pm.People.objects.filter(Q(peoplecode='NONE') | Q(peoplename='NONE')).get_or_create(
        id = -1,
        defaults={
            'peoplecode': 'NONE', 'peoplename': 'NONE',
            'email': "none@youtility.in", 'dateofbirth': '1111-1-1',
            'dateofjoin': "1111-1-1", 'id':-1
        }
    )
    return obj


def get_or_create_none_pgroup():
    obj, _ = pm.Pgroup.objects.get_or_create(
        id = -1,
        defaults={
            'groupname': "NONE", 'id':-1
        }
    )
    return obj


def get_or_create_none_cap():
    obj, _ = pm.Capability.objects.get_or_create(
        id = -1,
        defaults={
            'capscode': "NONE", 'capsname': 'NONE', 'id':-1
        }
    )
    return obj

def encrypt(data: bytes) -> bytes:
    import zlib
    from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d
    data = bytes(data, 'utf-8')
    return b64e(zlib.compress(data, 9))


def decrypt(obscured: bytes) -> bytes:
    import zlib
    from base64 import urlsafe_b64encode as b64e, urlsafe_b64decode as b64d
    byte_val = zlib.decompress(b64d(obscured))
    return byte_val.decode('utf-8')

def save_user_session(request, people):
    '''save user info in session'''
    from django.core.exceptions import ObjectDoesNotExist
    from django.conf import settings

    try:
        logger.info('saving user data into the session ... STARTED')
        if people.is_superuser == True:
            request.session['is_superadmin'] = True
            session = request.session
            session['people_webcaps'] = session['client_webcaps'] = session['people_mobcaps'] = \
                session['people_reportcaps'] = session['people_portletcaps'] = session['client_mobcaps'] = \
                session['client_reportcaps'] = session['client_portletcaps'] = False
            logger.info(request.session['is_superadmin'])
            putils.save_tenant_client_info(request)
        else:
            client = putils.save_tenant_client_info(request)
            request.session['is_superadmin'] = people.peoplecode == 'SUPERADMIN'
            request.session['is_admin'] = people.isadmin
            # get cap choices and save in session data
            putils.get_caps_choices(
                client=client, session=request.session, people=people)
            logger.info('saving user data into the session ... DONE')
        request.session['google_maps_secret_key'] = settings.GOOGLE_MAP_SECRET_KEY
    except ObjectDoesNotExist:
        logger.error('object not found...', exc_info=True)
        raise
    except Exception:
        logger.critical(
            'something went wrong please follow the traceback to fix it... ', exc_info=True)
        raise



def update_timeline_data(ids, request, update=False):
    # sourcery skip: hoist-statement-from-if, remove-pass-body
    import apps.onboarding.models as ob
    import apps.peoples.models as pm
    steps = {'taids': ob.TypeAssist, 'buids': ob.Bt, 'shiftids': ob.Shift,
             'peopleids': pm.People, 'pgroupids': pm.Pgroup}
    fields = {'buids': ['id', 'bucode', 'buname'],
              'taids': ['tacode', 'taname', 'tatype'],
              'peopleids': ['id', 'peoplecode', 'loginid'],
              'shiftids': ['id', 'shiftname'],
              'pgroupids': ['id', 'groupname']}
    data = steps[ids].objects.filter(
        pk__in=request.session['wizard_data'][ids]).values(*fields[ids])
    if not update:
        request.session['wizard_data']['timeline_data'][ids] = list(data)
    else:
        request.session['wizard_data']['timeline_data'][ids].pop()
        request.session['wizard_data']['timeline_data'][ids] = list(data)


def process_wizard_form(request, wizard_data, update=False, instance=None):
    logger.info('processing wizard started...', )
    dbg('wizard_Data submitted by the view \n%s' % wizard_data)
    wiz_session, resp = request.session['wizard_data'], None
    if not wizard_data['last_form']:
        logger.info('wizard its NOT last form')
        if not update:
            logger.info('processing wizard not an update form')
            wiz_session[wizard_data['current_ids']].append(
                wizard_data['instance_id'])
            request.session['wizard_data'].update(wiz_session)
            update_timeline_data(wizard_data['current_ids'], request, False)
            resp = scts.redirect(wizard_data['current_url'])
        else:
            resp = update_wizard_form(wizard_data, wiz_session, request)
            update_timeline_data(wizard_data['current_ids'], request, True)
    else:
        resp = scts.redirect('onboarding:wizard_view')
    return resp


def update_wizard_form(wizard_data, wiz_session, request):
    # sourcery skip: lift-return-into-if, remove-unnecessary-else
    resp = None
    logger.info('processing wizard is an update form')
    if wizard_data['instance_id'] not in wiz_session[wizard_data['current_ids']]:
        wiz_session[wizard_data['current_ids']].append(
            wizard_data['instance_id'])
    if wiz_session.get(wizard_data['next_ids']):
        resp = scts.redirect(
            wizard_data['next_update_url'], pk=wiz_session[wizard_data['next_ids']][-1])
    else:
        request.session['wizard_data'].update(wiz_session)
        resp = scts.redirect(wizard_data['current_url'])
    dbg("response from update_wizard_form %s" % (resp))
    return resp




def handle_other_exception(request, form, form_name, template, jsonform="", jsonform_name=""):
    logger.critical(
        "something went wrong please follow the traceback to fix it... ", exc_info=True)
    msg.error(request, "[ERROR] Something went wrong",
              "alert-danger")
    cxt = {form_name: form, 'edit': True, jsonform_name: jsonform}
    return scts.render(request, template, context=cxt)


def handle_does_not_exist(request, url):
    logger.error('Object does not exist', exc_info=True)
    msg.error(request, "Object does not exist",
              "alert-danger")
    return scts.redirect(url)


def get_index_for_deletion(lookup, request, ids):
    id = lookup['id']
    data = request.session['wizard_data']['timeline_data'][ids]
    for idx, item in enumerate(data):
        if item['id'] == int(id):
            print("idx going to be deleted %s" % (idx))
            return idx


def delete_object(request, model, lookup, ids, temp,
                  form, url, form_name, jsonformname=None, jsonform=None):
    """called when individual form request for deletion"""
    from django.db.models import RestrictedError
    try:
        logger.info('Request for object delete...')
        res, obj = None, model.objects.get(**lookup)
        form = form(instance=obj)
        obj.delete()
        msg.success(request, "Entry has been deleted successfully",
                    'alert-success')
        request.session['wizard_data'][ids].remove(int(lookup['id']))
        request.session['wizard_data']['timeline_data'][ids].pop(
            get_index_for_deletion(lookup, request, ids))
        logger.info('Object deleted')
        res = scts.redirect(url)
    except model.DoesNotExist:
        logger.error('Unable to delete, object does not exist')
        msg.error(request, 'Client does not exist', "alert alert-danger")
        res = scts.redirect(url)
    except RestrictedError:
        logger.warn('Unable to delete, duw to dependencies')
        msg.error(request, 'Unable to delete, duw to dependencies')
        cxt = {form_name: form, jsonformname: jsonform, 'edit': True}
        res = scts.render(request, temp, context=cxt)
    except Exception:
        msg.error(request, '[ERROR] Something went wrong',
                  "alert alert-danger")
        cxt = {form_name: form, jsonformname: jsonform, 'edit': True}
        res = scts.render(request, temp, context=cxt)
    return res


def delete_unsaved_objects(model, ids):
    if ids:
        try:
            logger.info(
                'Found unsaved objects in session going to be deleted...')
            model.objects.filter(pk__in=ids).delete()
        except:
            raise
        else:
            logger.info('Unsaved objects are deleted...DONE')


def update_prev_step(step_url, request):
    url, ids = step_url
    session = request.session['wizard_data']
    instance = session.get(ids)[-1] if session.get(ids) else None
    new_url = url.replace('form', 'update') if instance and (
        'update' not in url) else url
    request.session['wizard_data'].update(
        {'prev_inst': instance,
         'prev_url': new_url})


def update_next_step(step_url, request):
    url, ids = step_url
    session = request.session['wizard_data']
    instance = session.get(ids)[-1] if session.get(ids) else None
    new_url = url.replace('form', 'update') if instance and (
        'update' not in url) else url
    request.session['wizard_data'].update(
        {'next_inst': instance,
         'next_url': new_url})


def update_other_info(step, request, current, formid, pk):
    url, ids = step[current]
    session = request.session['wizard_data']
    session['current_step'] = session['steps'][current]
    session['current_url'] = url
    session['final_url'] = step['final_step'][0]
    session['formid'] = formid
    session['del_url'] = url.replace('form', 'delete')
    session['current_inst'] = pk


def update_wizard_steps(request, current, prev, next, formid, pk):
    '''Updates wizard next, current, prev, final urls'''
    step_urls = {
        'buform': ('onboarding:wiz_bu_form', 'buids'),
        'shiftform': ('onboarding:wiz_shift_form', 'shiftids'),
        'peopleform': ('peoples:wiz_people_form', 'peopleids'),
        'pgroupform': ('peoples:wiz_pgroup_form', 'pgroupids'),
        'final_step': ('onboarding:wizard_preview', '')}
    # update prev step
    update_prev_step(step_urls.get(prev, ("", "")), request)
    # update next step
    update_next_step(step_urls.get(next, ("", "")), request)
    # update other info
    update_other_info(step_urls, request, current, formid, pk)


def save_msg(request):
    '''Displays a success message'''
    return msg.success(request, 'Entry has been saved successfully!', 'alert-success')


def initailize_form_fields(form):
    for visible in form.visible_fields():
        if visible.widget_type in ['text','textarea','datetime','time', 'number', 'email', 'decimal']:
            visible.field.widget.attrs['class'] = 'form-control form-control-solid'
        elif visible.widget_type in ['radio', 'checkbox']:
            visible.field.widget.attrs['class'] = 'form-check-input'
        elif visible.widget_type in ['select2', 'select', 'select2multiple', 'modelselect2', 'modelselect2multiple']:
            visible.field.widget.attrs['class'] = 'form-select form-select-solid'
        


def apply_error_classes(form):
    # loop on *all* fields if key '__all__' found else only on errors:
    for x in (form.fields if '__all__' in form.errors else form.errors):
        attrs = form.fields[x].widget.attrs
        attrs.update({'class': attrs.get('class', '') + ' is-invalid'})

def to_utc( date, format=None):
    import pytz
    if isinstance(date, list) and date:
        dtlist = []
        for dt in date:
            dt = dt.astimezone(pytz.utc).replace(microsecond=0, tzinfo=pytz.utc)
            dtlist.append(dt)
        return dtlist
    else:
        dt = date.astimezone(pytz.utc).replace(microsecond=0, tzinfo=pytz.utc)
        if format:
            dt.strftime(format)
        return dt

# MAPPING OF HOSTNAME:DATABASE ALIAS NAME 
def get_tenants_map():
    return {
        'sps.youtility.local'       :'sps',
        'capgemini.youtility.local' :'capgemini',
        'dell.youtility.local'      :'dell',
        'icicibank.youtility.local' :'icicibank',
        'barfi.youtility.in'        :'icicibank'
    }

# RETURN HOSTNAME FROM REQUEST 
def hostname_from_request(request):
    return request.get_host().split(':')[0].lower()


def get_or_create_none_bv():
    obj, _ = Bt.objects.get_or_create(
        id = -1,
        defaults={
            'bucode':"NONE", 'buname':"NONE",'id':-1
        }
    )
    return obj


def get_or_create_none_typeassist():
    obj, _ = TypeAssist.objects.get_or_create(
        id = -1,
        defaults={
            'tacode':"NONE", 'taname':"NONE",'id':-1
        }
    )
    return obj

# RETURNS DB ALIAS FROM REQUEST
def tenant_db_from_request(request):
    hostname = hostname_from_request(request)
    print(f"Hostname from Request:{hostname}")
    tenants_map = get_tenants_map()
    return tenants_map.get(hostname, 'default')


def get_client_from_hostname(request):
    hostname = hostname_from_request(request)
    print(hostname)
    return hostname.split('.')[0]

   
def get_or_create_none_job():
    from datetime import datetime, timezone
    date = datetime(1970,1,1,00,00,00).replace(tzinfo=timezone.utc)
    obj, _ = am.Job.objects.get_or_create(
        id = -1,
        defaults={
            'jobname'     : 'NONE',    'jobdesc'        : 'NONE',
            'from_date'   : date,      'upto_date'      : date,
            'cron'        : "no_cron", 'lastgeneratedon': date,
            'planduration': 0,         'expirytime'     : 0,
            'gracetime'   : 0,         'priority'       : 'LOW',
            'slno'        : -1,        'scantype'       : 'SKIP',
            'id':-1
        }
    )
    return obj


def get_or_create_none_jobneed():
    from datetime import datetime, timezone
    date = datetime(1970,1,1,00,00,00).replace(tzinfo=timezone.utc)
    obj, _ = am.Jobneed.objects.get_or_create(
        id = -1,
        defaults={
            'jobdesc'          : "NONE", 'plandatetime': date,
            'expirydatetime'   : date,   'gracetime'   : 0,
            'recievedon_server': date,   'slno'        : -1,
            'scantype'         : "NONE", 'id':-1
        }
    )
    return obj


def get_or_create_none_qset():
    obj, _ = am.QuestionSet.objects.get_or_create(
        id = -1,
        defaults={
            'qset_name':"NONE", 'id':-1}
    )
    return obj

def get_or_create_none_question():
    obj, _ = am.Question.objects.get_or_create(
        id = -1,
        defaults = {
            'ques_name':"NONE", 'id':-1}
    )
    return obj


def get_or_create_none_qsetblng():
    obj, _ = am.QuestionSetBelonging.objects.get_or_create(
        id = -1,
        defaults = {
            'qset'     : get_or_create_none_qset(),
            'question'     : get_or_create_none_question(),
            'answertype' : 'NUMERIC', 'id':-1, 
            'ismandatory': False, 'slno':-1}
    )
    return obj

def get_or_create_none_asset():
    obj, _ = am.Asset.objects.get_or_create(
        id = '-1',
        defaults={
            'assetcode'    : "NONE", 'assetname' : 'NONE',
            'iscritical'   : False,  'identifier': 'NONE',
            'runningstatus': 'SCRAPPED', 'id':-1
        }
    )
    return obj


def create_none_entries(db):
    '''
    Creates None entries in self relationship models.
    '''
    try:
        set_db_for_router(db)
    except ValueError:
        print("Database with this alias not exist operation can't be performed")
    else:
        print(f"Creating None entries for {db}")
        get_or_create_none_typeassist()
        get_or_create_none_people()
        get_or_create_none_bv()
        get_or_create_none_cap()
        get_or_create_none_pgroup()
        get_or_create_none_job()
        get_or_create_none_jobneed()
        get_or_create_none_qset()
        print("Successfully created none entries for 'TypeAssist', 'People', 'Bv',\
         \'Capability', 'Pgroup', 'Job', 'Jobneed', 'QuestionSet")
    
def create_super_admin(db):
    try:
        set_db_for_router(db)
    except ValueError:
        print("Database with this alias not exist operation can't be performed")
    else:
        print(f"Creating SuperUser for {db}")
        from apps.peoples.models import People
        print("please provide required fields in this order single space separated\n")
        print("loginid  password  peoplecode  peoplename  dateofbirth  dateofjoin  email")
        inputs = input().split(" ")
        if len(inputs) == 7:
            user = People.objects.create_superuser(
                loginid     = inputs[0],
                password    = inputs[1],
                peoplecode  = inputs[2],
                peoplename  = inputs[3],
                dateofbirth = inputs[4],
                dateofjoin  = inputs[5],
                email       = inputs[6],
            )
            print(f"Operation Successfull!\n Superuser with this loginid {user.loginid} is created")
        else:
            raise ValueError("Please provide all fields!")

import threading
THREAD_LOCAL = threading.local()

def get_current_db_name():
    return getattr(THREAD_LOCAL, 'DB', "default")


def set_db_for_router(db):
    from django.conf import settings
    dbs = settings.DATABASES
    if db not in dbs:
        print('raised')
        raise ValueError("Database with this alias not exist!")
    setattr(THREAD_LOCAL, "DB", db)
    
def display_post_data(post_data):
    logger.info(
        "\n%s"%(pformat(post_data, compact=True))
    )
    
def format_data(objects):
    columns, rows, data = objects[0].keys(), {}, {}
    for i, d in enumerate(objects):
        for c in columns:
            rows[i][c] = "" if rows[i][c] is None else str(rows[i][c])
            del c
        del i, d
    data['rows'] = rows
    return data
    
def getFilters():
    return {
        "eq": "__iexact", "lt": "__lt",        "le": "__lte",
        "gt": "__gt",     "ge": "__gte",       "bw": "__istartswith",
        "in": "__in",     "ew": "__iendswith", "cn": "__icontains",
        "bt": "__range"}
    
def searchValue(objects, fields, related, model,  ST):
    q_objs = Q()
    for field in fields:
        q_objs |= get_filter(field, 'contains', ST)
    return model.objects.filter(
        q_objs).select_related(
            *related).values(*fields)
    
    
def get_filter(field_name, filter_condition, filter_value):
    # thanks to the below post
    # https://stackoverflow.com/questions/310732/in-django-how-does-one-filter-a-queryset-with-dynamic-field-lookups
    # the idea to this below logic is very similar to that in the above mentioned post
    if filter_condition.strip() == "contains":
        kwargs = {
            '{0}__icontains'.format(field_name): filter_value
        }
        return Q(**kwargs)

    if filter_condition.strip() == "not_equal":
        kwargs = {
            '{0}__iexact'.format(field_name): filter_value
        }
        return ~Q(**kwargs)

    if filter_condition.strip() == "starts_with":
        kwargs = {
            '{0}__istartswith'.format(field_name): filter_value
        }
        return Q(**kwargs)
    if filter_condition.strip() == "equal":
        kwargs = {
            '{0}__iexact'.format(field_name): filter_value
        }
        return Q(**kwargs)

    if filter_condition.strip() == "not_equal":
        kwargs = {
            '{0}__iexact'.format(field_name): filter_value
        }
        return ~Q(**kwargs)


def get_paginated_results(requestData, objects, count,
fields, related, model):
        '''paginate the results'''
        logger.info('Pagination Start'if count else "")
        if not requestData.get('draw'):
            return {'data':[]}
        if requestData['search[value]']!= "":
            objects =  searchValue(
                objects, fields, related, model, requestData["search[value]"])
            filtered = objects.count()
        else:
            filtered = count
        length, start = int(requestData['length']), int(requestData['start'])
        return objects[start:start+length], filtered
    

def PD(data=None, post=None, get=None, instance=None, cleaned=None):
    """
    Prints Data (DD)
    """
    if post: logger.debug(f"POST data recived from client: {pformat(post, compact=True)}\n")
    elif get: logger.debug(f"GET data recived from client: {pformat(get, compact=True)}\n")
    elif cleaned: logger.debug(f"CLEANED data after processing {pformat(cleaned, compact=True)}\n")
    elif instance: logger.debug(f"INSTANCE data recived from DB {pformat(instance, compact=True)}\n")
    else: logger.debug(f"{pformat(data, compact=True)}\n")

        
        
        