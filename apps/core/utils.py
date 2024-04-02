'''
DEFINE FUNCTIONS AND CLASSES WERE CAN BE USED GLOBALLY.
'''
import ast
import json
import logging
import os.path
import threading
import random
from pprint import pformat
from datetime import datetime
from dateutil import parser

import django.shortcuts as scts
from django.contrib import messages as msg
from django.contrib.gis.measure import Distance
from django.db.models import Q
from django.http import JsonResponse
from django.http import response as rp
from django.template.loader import render_to_string
from PIL import ImageFile
from rest_framework.utils.encoders import JSONEncoder
from django.conf import settings

import apps.activity.models as am
import apps.onboarding.models as ob
import apps.peoples.utils as putils
from apps.peoples import models as pm
from apps.work_order_management.models  import Wom
from apps.tenants.models import Tenant
from apps.core import exceptions as excp

logger = logging.getLogger('__main__')
dbg = logging.getLogger('__main__').debug

def get_current_year():
    return datetime.now().year


def get_appropriate_client_url(client_code):
    return settings.CLIENT_DOMAINS.get(client_code)

class CustomJsonEncoderWithDistance(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Distance):
            print(obj)
            return obj.m
        return super(CustomJsonEncoderWithDistance, self).default(obj)


def cache_it(key, val, time=1*60):
    from django.core.cache import cache
    cache.set(key, val, time)
    logger.info(f'saved in cache {pformat(val)}')


def get_from_cache(key):
    from django.core.cache import cache
    if data := cache.get(key):
        logger.info(f'Got from cache {key}')
        return data
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
    data = {'errors': 'Something went wrong, Please try again!'}
    logger.critical(data['errors'], exc_info=True)
    msg.error(request, data['errors'], 'alert-danger')
    if force_return:
        return force_return
    return rp.JsonResponse(data, status=404)


def handle_RestrictedError(request):
    data = {'errors': "Unable to delete, due to dependencies"}
    logger.warning("%s", data['errors'], exc_info=True)
    msg.error(request, data['errors'], "alert-danger")
    return rp.JsonResponse(data, status=404)


def handle_EmptyResultSet(request, params, cxt):
    logger.warning('empty objects retrieved', exc_info=True)
    msg.error(request, 'List view not found',
              'alert-danger')
    return scts.render(request, params['template_list'], cxt)


def handle_intergrity_error(name):
    msg = f'The {name} record of with these values is already exisit!'
    logger.info(msg, exc_info=True)
    return rp.JsonResponse({'errors': msg}, status=404)


def render_form_for_update(request, params, formname, obj, extra_cxt=None, FORM=None):
    if extra_cxt is None:
        extra_cxt = {}
    logger.info("render form for update")
    try:
        logger.info(f"object retrieved '{obj}'")
        F = FORM or params['form_class'](
            instance=obj, request=request)
        C = {formname: F, 'edit': True} | extra_cxt

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


def clean_gpslocation( val):
    import re

    from django.contrib.gis.geos import GEOSGeometry
    from django.forms import ValidationError

    if gps := val:
        if gps == 'NONE': return None
        regex = '^([-+]?)([\d]{1,2})(((\.)(\d+)(,)))(\s*)(([-+]?)([\d]{1,3})((\.)(\d+))?)$'
        gps = gps.replace('(', '').replace(')', '')
        if not re.match(regex, gps):
            raise ValidationError("Invalid GPS location")
        gps.replace(' ', '')
        lat, lng = gps.split(',')
        gps = GEOSGeometry(f'SRID=4326;POINT({lng} {lat})')
    return gps

def render_grid(request, params, msg, objs, extra_cxt=None):
    if extra_cxt is None:
        extra_cxt = {}

    from django.core.exceptions import EmptyResultSet
    logger.info("render grid")
    try:
        logger.info("%s", msg)
        logger.info(
            f'objects {len(objs)} retrieved from db' if objs else "No Records!"
        )

        logger.info("Pagination Starts"if objs else "")
        cxt = paginate_results(request, objs, params)
        logger.info("Pagination Ends" if objs else "")
        if extra_cxt:
            cxt.update(extra_cxt)
        resp = scts.render(request, params['template_list'], context=cxt)
    except EmptyResultSet:
        resp = handle_EmptyResultSet(request, params, cxt)
    except Exception:
        resp = handle_Exception(request, scts.redirect('/dashboard'))
    return resp


def paginate_results(request, objs, params):
    from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

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


def get_instance_for_update(postdata, params, msg, pk, kwargs=None):
    if kwargs is None:
        kwargs = {}
    logger.info("%s", msg)
    obj = params['model'].objects.get(id=pk)
    logger.info(f"object retrieved '{obj}'")
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
        logger.info(f"object retrieved '{obj}'")
        return obj


def local_to_utc(data, offset, mobile_web):
    # sourcery skip: avoid-builtin-shadow
    from datetime import datetime, timedelta

    import pytz
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
            logger.critical("datetime parsing ERROR", exc_info=True)
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
            logger.critical("datetime parsing ERROR", exc_info=True)
            raise
        else:
            return newdata


def get_or_create_none_people(using=None):
    obj, _ = pm.People.objects.get_or_create(
        peoplecode='NONE', peoplename = 'NONE',
        defaults={
            'email': "none@youtility.in", 'dateofbirth': '1111-1-1',
            'dateofjoin': "1111-1-1",
        }
    )
    return obj

def get_none_typeassist():
    try:
        return ob.TypeAssist.objects.get(id=1)
    except ob.TypeAssist.DoesNotExist:
        o, _ = get_or_create_none_typeassist()
        return o


def get_or_create_none_pgroup():
    obj, _ = pm.Pgroup.objects.get_or_create(
        groupname="NONE",
        defaults={},
    )
    return obj


def get_or_create_none_location():
    obj, _ = am.Location.objects.get_or_create(
        loccode= "NONE", locname = 'NONE',
        defaults={
            'locstatus':'SCRAPPED'
            }
    )
    return obj


def get_or_create_none_cap():
    obj, _ = pm.Capability.objects.get_or_create(
        capscode = "NONE", capsname = 'NONE',
        defaults={}
    )
    return obj


def encrypt(data: bytes) -> bytes:
    import zlib
    from base64 import urlsafe_b64decode as b64d
    from base64 import urlsafe_b64encode as b64e
    data = bytes(data, 'utf-8')
    return b64e(zlib.compress(data, 9))


def decrypt(obscured: bytes) -> bytes:
    from zlib import decompress 
    from base64 import urlsafe_b64decode as b64d
    byte_val = decompress(b64d(obscured))
    return byte_val.decode('utf-8')

def save_capsinfo_inside_session(people, request):
    logger.info('save_capsinfo_inside_session... STARTED')
    from apps.core.raw_queries import get_query
    from apps.peoples.models import Capability
    web, mob, portlet, report = putils.create_caps_choices_for_peopleform(request.user.client)
    request.session['client_webcaps'] = list(web)
    request.session['client_mobcaps'] = list(mob)
    request.session['client_portletcaps'] = list(portlet)
    request.session['client_reportcaps'] = list(report)
    
    caps = Capability.objects.raw(get_query('get_web_caps_for_client'))
    request.session['people_webcaps'] = list(Capability.objects.filter(capscode__in = people.people_extras['webcapability'], cfor='WEB').values_list('capscode', 'capsname')) 
    request.session['people_mobcaps'] = list(Capability.objects.filter(capscode__in = people.people_extras['mobilecapability'], cfor='MOB').values_list('capscode', 'capsname')) 
    request.session['people_reportcaps'] = list(Capability.objects.filter(capscode__in = people.people_extras['reportcapability'], cfor='REPORT').values_list('capscode', 'capsname')) 
    request.session['people_portletcaps'] = list(Capability.objects.filter(capscode__in = people.people_extras['portletcapability'], cfor='PORTLET').values_list('capscode', 'capsname')) 
    logger.info('save_capsinfo_inside_session... DONE')
    
    



def save_user_session(request, people, ctzoffset=None):
    '''save user info in session'''
    from django.conf import settings
    from django.core.exceptions import ObjectDoesNotExist

    try:
        logger.info('saving user data into the session ... STARTED')
        if ctzoffset: request.session['ctzoffset'] = ctzoffset
        if people.is_superuser is True:
            request.session['is_superadmin'] = True
            session = request.session
            session['people_webcaps'] = session['client_webcaps'] = session['people_mobcaps'] = \
                session['people_reportcaps'] = session['people_portletcaps'] = session['client_mobcaps'] = \
                session['client_reportcaps'] = session['client_portletcaps'] = False
            logger.info(request.session['is_superadmin'])
            putils.save_tenant_client_info(request)
        else:
            putils.save_tenant_client_info(request)
            request.session['is_superadmin'] = people.peoplecode == 'SUPERADMIN'
            request.session['is_admin'] = people.isadmin
            save_capsinfo_inside_session(people, request)
            logger.info('saving user data into the session ... DONE')
        request.session['assignedsites'] = list(pm.Pgbelonging.objects.get_assigned_sites_to_people(people.id))
        request.session['assignedsitegroups'] = people.people_extras['assignsitegroup']
        request.session['clientcode'] = request.user.client.bucode
        request.session['clientname'] = request.user.client.buname
        request.session['sitename'] = request.user.bu.buname
        request.session['sitecode'] = request.user.bu.bucode
        request.session['google_maps_secret_key'] = settings.GOOGLE_MAP_SECRET_KEY
        request.session['is_workpermit_approver'] = request.user.people_extras['isworkpermit_approver']
    except ObjectDoesNotExist:
        logger.error('object not found...', exc_info=True)
        raise
    except Exception:
        logger.critical(
            'something went wrong please follow the traceback to fix it... ', exc_info=True)
        raise


def update_timeline_data(ids, request, update=False):
    # sourcery skip: hoist-statement-from-if, remove-pass-body
    steps = {'taids': ob.TypeAssist, 'buids': ob.Bt, 'shiftids': ob.Shift,
             'peopleids': pm.People, 'pgroupids': pm.Pgroup}
    fields = {'buids': ['id', 'bucode', 'buname'],
              'taids': ['tacode', 'taname', 'tatype'],
              'peopleids': ['id', 'peoplecode', 'loginid'],
              'shiftids': ['id', 'shiftname'],
              'pgroupids': ['id', 'name']}
    data = steps[ids].objects.filter(
        pk__in=request.session['wizard_data'][ids]).values(*fields[ids])
    if not update:
        request.session['wizard_data']['timeline_data'][ids] = list(data)
    else:
        request.session['wizard_data']['timeline_data'][ids].pop()
        request.session['wizard_data']['timeline_data'][ids] = list(data)


def process_wizard_form(request, wizard_data, update=False, instance=None):
    logger.info('processing wizard started...', )
    dbg('wizard_Data submitted by the view \n%s', wizard_data)
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
    dbg(f"response from update_wizard_form {resp}")
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
            print(f"idx going to be deleted {idx}")
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
        logger.warning('Unable to delete, duw to dependencies')
        msg.error(request, 'Unable to delete, duw to dependencies')
        cxt = {form_name: form, jsonformname: jsonform, 'edit': True}
        res = scts.render(request, temp, context=cxt)
    except Exception:
        logger.critical("something went wrong!", exc_info=True)
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
        except Exception:
            logger.critical('delete_unsaved_objects failed', exc_info=True)
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
        if visible.widget_type in ['text', 'textarea', 'datetime', 'time', 'number', 'date','email', 'decimal']:
            visible.field.widget.attrs['class'] = 'form-control form-control-solid'
        elif visible.widget_type in ['radio', 'checkbox']:
            visible.field.widget.attrs['class'] = 'form-check-input'
        elif visible.widget_type in ['select2', 'select', 'select2multiple', 'modelselect2', 'modelselect2multiple']:
            visible.field.widget.attrs['class'] = 'form-select form-select-solid'
            visible.field.widget.attrs['data-control'] = 'select2'
            visible.field.widget.attrs['data-placeholder'] = 'Select an option'
            visible.field.widget.attrs['data-allow-clear'] = 'true'


def apply_error_classes(form):
    # loop on *all* fields if key '__all__' found else only on errors:
    for x in (form.fields if '__all__' in form.errors else form.errors):
        attrs = form.fields[x].widget.attrs
        attrs.update({'class': attrs.get('class', '') + ' is-invalid'})


def to_utc(date, format=None):
    logger.info("to_utc() start [+]")
    import pytz
    if isinstance(date, list) and date:
        logger.info(f'found total {len(date)} datetimes')
        logger.info(f"before conversion datetimes {date}")
        dtlist = []
        for dt in date:
            dt = dt.astimezone(pytz.utc).replace(
                microsecond=0, tzinfo=pytz.utc)
            dtlist.append(dt)
        logger.info(f"after conversion datetime list returned {dtlist=}")
        return dtlist
    dt = date.astimezone(pytz.utc).replace(microsecond=0, tzinfo=pytz.utc)
    if format:
        dt.strftime(format)
    logger.info("to_utc() end [-]")
    return dt

# MAPPING OF HOSTNAME:DATABASE ALIAS NAME


def get_tenants_map():
    return {
        'intelliwiz.youtility.local': 'intelliwiz_django',
        'sps.youtility.local'       : 'sps',
        'capgemini.youtility.local' : 'capgemini',
        'dell.youtility.local'      : 'dell',
        'icicibank.youtility.local' : 'icicibank',
        'redmine.youtility.in' : 'sps',
        'django-local.youtility.in' : 'default',
        'barfi.youtility.in'        : 'icicibank',
        'intelliwiz.youtility.in'   : 'default',
        'testdb.youtility.local'    : 'testDB'
    }

# RETURN HOSTNAME FROM REQUEST


def hostname_from_request(request):
    return request.get_host().split(':')[0].lower()


def get_or_create_none_bv():
    obj, _ = ob.Bt.objects.get_or_create(
        bucode = "NONE", buname = "NONE",
        defaults={}
    )
    return obj


def get_or_create_none_typeassist():
    obj, iscreated = ob.TypeAssist.objects.get_or_create(
        tacode= "NONE", taname= "NONE",
        defaults={}
    )
    return obj, iscreated

# RETURNS DB ALIAS FROM REQUEST


def tenant_db_from_request(request):
    hostname = hostname_from_request(request)
    tenants_map = get_tenants_map()
    return tenants_map.get(hostname, 'default')


def get_client_from_hostname(request):
    hostname = hostname_from_request(request)
    print(hostname)
    return hostname.split('.')[0]


def get_or_create_none_tenant():
    return Tenant.objects.get_or_create(tenantname = 'Intelliwiz', subdomain_prefix = 'intelliwiz',defaults={})[0]


def get_or_create_none_job():
    from datetime import datetime, timezone
    date = datetime(1970, 1, 1, 00, 00, 00).replace(tzinfo=timezone.utc)
    obj, _ = am.Job.objects.get_or_create(
        jobname= 'NONE',    jobdesc= 'NONE',
        defaults={
            'fromdate': date,      'uptodate': date,
            'cron': "no_cron", 'lastgeneratedon': date,
            'planduration': 0,         'expirytime': 0,
            'gracetime': 0,         'priority': 'LOW',
            'seqno': -1,        'scantype': 'SKIP',
        }
    )
    return obj


def get_or_create_none_gf():
    obj, _ = ob.GeofenceMaster.objects.get_or_create(
        gfcode= 'NONE', gfname= 'NONE',
        defaults={
            'alerttext': 'NONE', 'enable': False
        }
    )
    return obj


def get_or_create_none_jobneed():
    from datetime import datetime, timezone
    date = datetime(1970, 1, 1, 00, 00, 00).replace(tzinfo=timezone.utc)
    obj, _ = am.Jobneed.objects.get_or_create(
        jobdesc= "NONE",  scantype= "NONE", seqno= -1,
        defaults={
            'plandatetime': date,
            'expirydatetime': date,   'gracetime': 0,
            'receivedonserver': date,  
        }
    )
    return obj

def get_or_create_none_wom():
    from datetime import datetime, timezone
    date = datetime(1970, 1, 1, 00, 00, 00).replace(tzinfo=timezone.utc)
    obj, _ = Wom.objects.get_or_create(
        description= "NONE", expirydatetime= date, plandatetime =  date,
        defaults={
            'worlpermit':Wom.WorkPermitStatus.NOTNEED,
            'attachmentcount':0, 'priority':Wom.Priority.LOW,
        }
    )
    return obj


def get_or_create_none_qset():
    obj, _ = am.QuestionSet.objects.get_or_create(
        qsetname = "NONE",
        defaults={}
    )
    return obj


def get_or_create_none_question():
    obj, _ = am.Question.objects.get_or_create(
        quesname = "NONE", 
        defaults={}
    )
    return obj


def get_or_create_none_qsetblng():
    'A None qsetblng with seqno -1'
    obj, _ = am.QuestionSetBelonging.objects.get_or_create(
       answertype = 'NONE', 
        ismandatory =  False, seqno = -1,
    defaults={
            'qset': get_or_create_none_qset(),
            'question': get_or_create_none_question(),
            }
    )
    return obj


def get_or_create_none_asset():
    obj, _ = am.Asset.objects.get_or_create(
        assetcode = "NONE", assetname = 'NONE',
        identifier = 'NONE',
        defaults={'iscritical': False}
    )
    return obj

def get_or_create_none_ticket():
    from apps.y_helpdesk.models import Ticket
    obj, _ = Ticket.objects.get_or_create(
        ticketdesc = 'NONE',
        defaults = {}
    )
    return obj



def create_none_entries():
    '''
    Creates None entries in self relationship models.
    '''
    try:
        db = get_current_db_name()
        _, iscreated = get_or_create_none_typeassist()
        if not iscreated:
            return
        get_or_create_none_people()
        get_or_create_none_ticket()
        get_or_create_none_bv()
        get_or_create_none_cap()
        get_or_create_none_pgroup()
        get_or_create_none_job()
        get_or_create_none_jobneed()
        get_or_create_none_qset()
        get_or_create_none_asset()
        get_or_create_none_tenant()
        get_or_create_none_question()
        get_or_create_none_qsetblng()
        get_or_create_none_gf()
        logger.debug("NONE entries are successfully inserted...")
    except Exception as e:
        logger.error('create none entries', exc_info=True)
        raise


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
                loginid=inputs[0],
                password=inputs[1],
                peoplecode=inputs[2],
                peoplename=inputs[3],
                dateofbirth=inputs[4],
                dateofjoin=inputs[5],
                email=inputs[6],
            )
            print(
                f"Operation Successfull!\n Superuser with this loginid {user.loginid} is created")
        else:
            raise ValueError("Please provide all fields!")


THREAD_LOCAL = threading.local()


def get_current_db_name():
    return getattr(THREAD_LOCAL, 'DB', "default")


def set_db_for_router(db):
    from django.conf import settings
    dbs = settings.DATABASES
    if db not in dbs:
        print('raised')
        raise excp.NoDbError("Database with this alias not exist!")
    setattr(THREAD_LOCAL, "DB", db)


def display_post_data(post_data):
    logger.info("\n%s", (pformat(post_data, compact = True)))

def format_data(objects):
    columns, rows, data = objects[0].keys(), {}, {}
    for i, d in enumerate(objects):
        for c in columns:
            rows[i][c] = "" if rows[i][c] is None else str(rows[i][c])
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


def searchValue2(fields,  ST):
    q_objs = Q()
    for field in fields:
        q_objs |= get_filter(field, 'contains', ST)
    return q_objs


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
        return {'data': []}
    if requestData['search[value]'] != "":
        objects = searchValue(
            objects, fields, related, model, requestData["search[value]"])
        filtered = objects.count()
    else:
        filtered = count
    length, start = int(requestData['length']), int(requestData['start'])
    return objects[start:start+length], filtered


def get_paginated_results2(objs, count, params, R):
    filtered = 0
    if count:
        logger.info('Pagination Start'if count else "")
        if R['serch[value]'] != "":
            objects = searchValue2(
                objs, params['fields'], params['related'], R['search[value]'])
            filtered = objects.count()
        else:
            filtered = count
        length, start = int(R['length']), int(R['start'])
        objects = objects[start:start+length]
    return JsonResponse(data={
        'draw': R['draw'],
        'data': list(objects),
        'recordsFiltered': filtered,
        'recordsTotal': count
    })


def PD(data=None, post=None, get=None, instance=None, cleaned=None):
    """
    Prints Data (DD)
    """
    if post:
        logger.debug(
            f"POST data recived from client: {pformat(post, compact = True)}\n")
    elif get:
        logger.debug(
            f"GET data recived from client: {pformat(get, compact = True)}\n")
    elif cleaned:
        logger.debug(
            f"CLEANED data after processing {pformat(cleaned, compact = True)}\n")
    elif instance:
        logger.debug(
            f"INSTANCE data recived from DB {pformat(instance, compact = True)}\n")
    else:
        logger.debug(f"{pformat(data, compact = True)}\n")


def register_newuser_token(user, clientUrl):
    if not user.email or not user.loginid:
        return False, None
    import requests
    from django.conf import settings
    domain = 'local'if settings.DEBUG else 'in'
    endpoint = f"http://{clientUrl}.youtility.{domain}"
    query = """
        mutation { 
            register(
                email:%s,
                loginid:%s,
                password1:%s,
                password2:%s,
            ){
                success,
                errors,
                token,
                refreshToken
            }
        }
    """ % (user.email, user.loginid, user.password, user.password)

    res = requests.post(endpoint, json={"query": query})
    if res.status_code == 200:
        return True, res
    return False, None


def clean_record(record):

    from django.contrib.gis.geos import GEOSGeometry

    for k, v in record.items():
        if k in ['gpslocation', 'startlocation', 'endlocation']:
            ic(v, type(v))
            v = v.split(',')
            ic(v)
            p = f'POINT({v[1]} {v[0]})'
            ic(p)
            record[k] = GEOSGeometry(p, srid=4326)
    return record


def save_common_stuff(request, instance, is_superuser=False, ctzoffset=-1):
    from django.utils import timezone
    userid = 1 if is_superuser else request.user.id
    if instance.cuser is not None:
        instance.muser_id = userid
        instance.mdtz = timezone.now().replace(microsecond=0)
        instance.ctzoffset = ctzoffset
    else:
        instance.cuser_id = instance.muser_id = userid
    #instance.ctzoffset = int(request.session['ctzoffset'])
    return instance


def create_tenant_with_alias(db):
    Tenant.objects.create(
        tenantname=db.upper(),
        subdomain_prefix=db
    )


def get_record_from_input(input):

    ic(input.values)
    values = ast.literal_eval(json.dumps(input.values))
    ic(values)
    return dict(zip(input.columns, values))

# import face_recognition



def alert_observation(pk, event):

    raise NotImplementedError()


def alert_email(pk, event):
    if event == 'OBSERVATION':
        alert_observation(pk, event)


def printsql(objs):
    from django.core.exceptions import EmptyResultSet
    try:
        print('SQL QUERY:\n', objs.query.__str__())
    except EmptyResultSet:
        print("NO SQL")


def get_select_output(objs):
    if not objs:
        return None, 0, "No records"
    records = json.dumps(list(objs), default=str)
    count = objs.count()
    msg = f'Total {count} records fetched successfully!'
    return records, count, msg


def get_qobjs_dir_fields_start_length(R):
    qobjs = None
    if R.get('search[value]'):
        qobjs = searchValue2(R.getlist('fields[]'), R['search[value]'])

    orderby, fields = R.getlist('order[0][column]'), R.getlist('fields[]')
    orderby = [orderby] if not isinstance(orderby, list) else orderby
    length, start = int(R['length']), int(R['start'])

    for order in orderby:
        if order:
            ic(f'columns[{order}][data]')
            key = R[f'columns[{order}][data]']
            dir = f"-{key}" if R['order[0][dir]'] == 'desc' else f"{key}"
        else:
            dir = "-mdtz"
    if not orderby:
        dir = "-mdtz"
    return qobjs, dir,  fields, length, start


def runrawsql(sql, args=None, db='default', named=False, count=False, named_params=False):
    "Runs raw sql return namedtuple or dict type results"
    from django.db import connections
    cursor = connections[db].cursor()
    if named_params:
        sql = sql.format(**args)
        cursor.execute(sql)
    else:
        cursor.execute(sql, args)
    querystring = str(cursor.query, encoding='utf-8')
    logger.debug(f"\n\nSQL QUERY: {querystring}\n")
    if count:
        return cursor.rowcount
    else:
        return namedtuplefetchall(cursor) if named else dictfetchall(cursor)



def namedtuplefetchall(cursor):
    from collections import namedtuple
    "Return all rows from a cursor as a namedtuple"
    desc = cursor.description
    nt_result = namedtuple('Result', [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def getformatedjson(geofence=None, jsondata=None, rettype=dict):
    data = jsondata or geofence.geojson
    geodict = json.loads(data)
    result = [{'lat': lat, 'lng': lng}
              for lng, lat in geodict['coordinates'][0]]
    return result if rettype == dict else json.dumps(result)




def getawaredatetime(dt, offset):
    from datetime import datetime, timedelta, timezone
    tz = timezone(timedelta(minutes=int(offset)))
    if isinstance(dt, datetime):
        val = dt
    else:
        val = dt.replace("+00:00", "")
        val = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
    return val.replace(tzinfo=tz, microsecond=0)


def ok(self):
    self.stdout.write(self.style.SUCCESS("DONE"))


def failed(self):
    self.stdout.write(self.style.ERROR("FAILED"))


class JobFields:
    fields = [
        'id', 'jobname', 'jobdesc', 'geofence_id', 'cron',
        'expirytime', 'identifier', 'cuser_id', 'muser_id','bu_id',
        'client_id', 'sgroup__groupname',
        'pgroup_id', 'sgroup_id','ticketcategory_id', 'frequency',
        'starttime', 'endtime', 'seqno', 'ctzoffset', 'people_id',
        'asset_id', 'parent_id', 'scantype', 'planduration', 'fromdate',
        'uptodate', 'priority', 'lastgeneratedon', 'qset_id', 'qset__qsetname',
        'asset__assetname', 'other_info', 'gracetime', 'cdtz', 'mdtz']

def sumDig( n ):
    a = 0
    while n > 0:
        a = a + n % 10
        n = int(n / 10)
 
    return a


# Returns True if n is valid EMEI
def isValidEMEI(n):
 
    # Converting the number into
    # String for finding length
    s = str(n)
    l = len(s)

    if l != 15:
        return False
    return True

    
def verify_mobno(mobno):
    import phonenumbers as pn
    from phonenumbers.phonenumberutil import NumberParseException
    try:
        no = pn.parse(f'+{mobno}') if '+' not in mobno else pn.parse(mobno)
        if not pn.is_valid_number(no):
            return False
    except NumberParseException as e:
        return False
    else: return True
    
    
def verify_emailaddr(email):
    from email_validator import EmailNotValidError, validate_email
    try:
        validate_email(email)
        return True
    except EmailNotValidError as e:
        logger.warning('email is not valid')
        return False
        
def verify_loginid(loginid):
    import re
    return bool(re.match(r"^[a-zA-Z0-9@#_\-\_]+$", loginid))
    
def verify_peoplename(peoplename):
    import re
    return bool(re.match(r"^[a-zA-Z0-9\-_@#\(\|\) ]*$", peoplename))


def get_home_dir():
    from django.conf import settings
    ic(settings.MEDIA_ROOT)
    return settings.MEDIA_ROOT


def orderedRandom(arr, k):
    if not len(arr) > 25: return arr
    indices = random.sample(range(len(arr)), k)
    return [arr[i] for i in sorted(indices)]    



def upload(request, vendor=False):
    logger.info(f"{request.POST = }")
    S = request.session
    if 'img' not in request.FILES:
        return
    foldertype = request.POST["foldertype"]
    if foldertype in ["task", "internaltour", "externaltour", "ticket", "incidentreport", 'visitorlog', 'conveyance', 'workorder', 'workpermit']:
        tabletype, activity_name = "transaction", foldertype.upper()
    if foldertype in ['people', 'client']:
        tabletype, activity_name = "master", foldertype.upper()
    logger.info(f"Floder type: {foldertype} and activity Name: {activity_name}")

    home_dir = settings.MEDIA_ROOT
    fextension = os.path.splitext(request.FILES['img'].name)[1]
    filename = parser.parse(str(datetime.now())).strftime('%d_%b_%Y_%H%M%S') + fextension
    logger.info(f'{filename = } {fextension = }')
    
    if tabletype == 'transaction':
        fmonth = str(datetime.now().strftime("%b"))
        fyear = str(datetime.now().year)
        peopleid = request.POST["peopleid"]
        fullpath = f'{home_dir}/transaction/{S["clientcode"]}_{S["client_id"]}/{peopleid}/{activity_name}/{fyear}/{fmonth}/'
        
    else:
        fullpath = f'{home_dir}/master/{S["clientcode"]}_{S["client_id"]}/{foldertype}/'
    
    logger.info(f'{fullpath = }')


    if not os.path.exists(fullpath):    
        os.makedirs(fullpath)
    fileurl = f'{fullpath}{filename}'
    logger.info(f"{fileurl = }")
    try:
        if not os.path.exists(fileurl):
            ic(fileurl)
            with open(fileurl, 'wb') as temp_file:
                temp_file.write(request.FILES['img'].read())
                temp_file.close()
    except Exception as e:
        logger.critical(e, exc_info=True)
        return False, None, None

    logger.info(f"{filename = } {fullpath = }")
    return True, filename, fullpath 
    
def upload_vendor_file(file, womid):
    home_dir = settings.MEDIA_ROOT
    fmonth = str(datetime.now().strftime("%b"))
    fyear = str(datetime.now().year)
    fullpath = f'{home_dir}/transaction/workorder_management/details/{fyear}/{fmonth}/'
    fextension = os.path.splitext(file.name)[1]
    filename = parser.parse(str(datetime.now())).strftime('%d_%b_%Y_%H%M%S') + f'womid_{womid}' + fextension
    if not os.path.exists(fullpath):    
        os.makedirs(fullpath)
    fileurl = f'{fullpath}{filename}'
    try:
        if not os.path.exists(fileurl):
            with open(fileurl, 'wb') as temp_file:
                temp_file.write(file.read())
                temp_file.close()
    except Exception as e:
        logger.critical(e, exc_info=True)
        return False, None, None

    return True, filename, fullpath.replace(home_dir, '')
        
                

def check_nones(none_fields, tablename, cleaned_data, json=False):
    none_instance_map = {
        'question':get_or_create_none_question,
        'asset':get_or_create_none_asset,
        'people': get_or_create_none_people,
        'pgroup': get_or_create_none_pgroup,
        'typeassist':get_or_create_none_typeassist
    }

    for field in none_fields:
        cleaned_data[field] = 1 if json else none_instance_map[tablename]()
    return cleaned_data


def get_action_on_ticket_states(prev_tkt, current_state):
    actions = []
    if prev_tkt and prev_tkt[-1]['previous_state'] and current_state:
        prev_state = prev_tkt[-1]['previous_state']
        if prev_state['status'] != current_state['status']:
            actions.append(f'''Status Changed From "{prev_state['status']}" To "{current_state['status']}"''')
        
        if prev_state['priority'] != current_state['priority']:
            actions.append(f'''Priority Changed from "{prev_state['priority']}" To "{current_state['priority']}"''')
        
        if prev_state['location'] != current_state['location']:
            actions.append(f'''Location Changed from "{prev_state['location']}" To "{current_state['location']}"''')
        
        if prev_state['ticketdesc'] != current_state['ticketdesc']:
            actions.append(f'''Ticket Description Changed From "{prev_state['ticketdesc']}" To "{current_state['ticketdesc']}"''')
        
        if prev_state['assignedtopeople'] != current_state['assignedtopeople']:
            actions.append(f'''Ticket Is Reassigned From "{prev_state['assignedtopeople']}" To "{current_state['assignedtopeople']}"''')
        
        if prev_state['assignedtogroup'] != current_state['assignedtogroup']:
            actions.append(f'''Ticket Is Reassigned From "{prev_state['assignedtogroup']}" To "{current_state['assignedtogroup']}"''')
        
        if prev_state['comments'] != current_state['comments'] and current_state['comments'] not in ['None', None]:
            actions.append(f'''New Comments "{current_state['comments']}" are added after "{prev_state['comments']}"''')
        if prev_state['level'] != current_state['level']:
            actions.append(f'''Ticket level is changed from {prev_state['level']} to {current_state["level"]}''')
        return actions
    return ["Ticket Created"]
        
    


from django.utils import timezone

def store_ticket_history(instance, request=None, user = None):
    from background_tasks.tasks import send_ticket_email
       
    
    # Get the current time
    now = timezone.now().replace(microsecond=0, second=0)
    peopleid = request.user.id if request else user.id
    peoplename = request.user.peoplename if request else user.peoplename
    
    # Get the current state of the ticket
    current_state = {
        "ticketdesc": instance.ticketdesc,
        "assignedtopeople": instance.assignedtopeople.peoplename,
        "assignedtogroup": instance.assignedtogroup.groupname,
        "comments":instance.comments,
        "status":instance.status,
        "priority":instance.priority,
        "location":instance.location.locname,
        'level':instance.level,
        'isescalated':instance.isescalated
    }

    # Get the previous state of the ticket, if it exists
    ticketstate = instance.ticketlog['ticket_history']
    
    details = get_action_on_ticket_states(ticketstate, current_state)
    
    # Create a dictionary to represent the changes made to the ticket
    history_item = {
        "people_id"     : peopleid,
        "when"          : str(now),
        "who"           : peoplename,
        "assignto"      : instance.assignedtogroup.groupname if instance.assignedtopeople_id in [1, None] else instance.assignedtopeople.peoplename,
        "action"        : "created",
        "details"       : details,
        "previous_state": current_state,
    }

    logger.debug(
        f"{instance.mdtz=} {instance.cdtz=} {ticketstate=} {details=}"
    )
    
    
    # Check if there have been any changes to the ticket
    if instance.mdtz > instance.cdtz and  ticketstate and  ticketstate[-1]['previous_state'] != current_state:
        history_item['action'] = "updated"

        # Append the history item to the ticket_history list within the ticketlog JSONField
        ticket_history = instance.ticketlog["ticket_history"]
        ticket_history.append(history_item)
        instance.ticketlog = {"ticket_history": ticket_history}
        logger.info("changes have been made to ticket")
    elif instance.mdtz > instance.cdtz:
        history_item['details'] = 'No changes detected'
        history_item['action'] = 'updated'
        instance.ticketlog['ticket_history'].append(history_item)
        logger.info("no changed detected")
    else:
        instance.ticketlog['ticket_history'] = [history_item]
        send_ticket_email.delay(id=instance.id)
        logger.info("new ticket is created..")
    instance.save()
    logger.info("saving ticket history ended...")
    

def get_email_addresses(people_ids, group_ids=None, buids=None):
    from apps.peoples.models import People, Pgbelonging
    
    p_emails, g_emails = [],[]
    if people_ids:
        p_emails = list(People.objects.filter(
            ~Q(peoplecode='NONE'), id__in = people_ids
        ).values_list('email', flat=True))
    if group_ids:
        g_emails = list(Pgbelonging.objects.select_related('pgroup').filter(
            ~Q(people_id=1), pgroup_id__in = group_ids, assignsites_id = 1
        ).values_list('people__email', flat=True))
    return list(set(p_emails + g_emails)) or []
    
    
    

def send_email(subject, body, to, from_email=None, atts=None, cc=None):
    if atts is None: atts = []
    from django.core.mail import EmailMessage
    from django.conf import settings

    logger.info('email sending process started')
    msg = EmailMessage()
    msg.subject = subject
    logger.info(f'subject of email is {subject}')
    msg.body = body
    msg.from_email = from_email or settings.EMAIL_HOST_USER
    msg.to = to
    if cc: msg.cc = cc
    logger.info(f'recipents of email are  {to}')
    msg.content_subtype= 'html'
    for attachment in atts:
        msg.attach_file(attachment)
    if atts: logger.info(f'Total {len(atts)} found and added to the message')
    msg.send()
    logger.info('email successfully sent')
    
    
    
def get_timezone(offset):  # sourcery skip: aware-datetime-for-utc
    import pytz
    from datetime import datetime, timedelta
    # Convert the offset string to a timedelta object
    offset = f'+{offset}' if int(offset) > 0 else str(offset)
    sign = offset[0] # The sign of the offset (+ or -)
    mins = int(offset[1:])
    delta = timedelta(minutes=mins) # The timedelta object
    if sign == "-": # If the sign is negative, invert the delta
        delta = -delta

    # Loop through all the timezones and find the ones that match the offset
    matching_zones = [] # A list to store the matching zones
    for zone in pytz.all_timezones: # For each timezone
        tz = pytz.timezone(zone) # Get the timezone object
        utc_offset = tz.utcoffset(datetime.utcnow()) # Get the current UTC offset
        if utc_offset == delta: # If the offset matches the input
            matching_zones.append(zone) # Add the zone to the list

    # Return the list of matching zones or None if no match found
    return matching_zones[0] if matching_zones else None


def format_timedelta(td):
    if not td: return None
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 60*60*24)
    hours, remainder = divmod(remainder, 60*60)
    minutes, seconds = divmod(remainder, 60)

    result = ""
    if days > 0:
        result += f"{days} day{'s' if days != 1 else ''}, "
    if hours > 0:
        result += f"{hours} hour{'s' if hours != 1 else ''}, "
    if minutes > 0:
        result += f"{minutes} minute{'s' if minutes != 1 else ''}, "
    if seconds > 0 or len(result) == 0:
        result += f"{seconds} second{'s' if seconds != 1 else ''}"
    return result.rstrip(', ')


def convert_seconds_to_human_readable(seconds):
    # Calculate the time units
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    # Create a human readable string
    result = []
    if days:
        result.append(f"{int(days)} day{'s' if days > 1 else ''}")
    if hours:
        result.append(f"{int(hours)} hour{'s' if hours > 1 else ''}")
    if minutes:
        result.append(f"{int(minutes)} minute{'s' if minutes > 1 else ''}")
    if sec:
        result.append(f"{sec:.2f} second{'s' if sec > 1 else ''}") # limit decimal places to 2
    
    return ", ".join(result)


def create_client_site():
    from apps.onboarding.models import Bt, TypeAssist
    client_type, _ = TypeAssist.objects.get_or_create(
        tacode='CLIENT', taname = 'Client'
    )
    site_type, _ = TypeAssist.objects.get_or_create(
        tacode='SITE', taname = 'Site', 
    )
    client, _ = Bt.objects.get_or_create(
        bucode='TESTCLIENT', buname='Test Client',
        identifier=client_type, id=4
    )
    site, _ = Bt.objects.get_or_create(
        bucode = 'TESTBT', buname = 'Test Bt',
        identifier = site_type, parent = client,
        id=5
    )
    return client, site



def create_user():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user, _ = User.objects.get_or_create(
            loginid='testuser', id=4,
            dateofbirth='2022-05-22', peoplecode='TESTUSER',
            peoplename='Test User', email="testuser@gmail.com",
            isverified = True)
    user.set_password('testpassword')
    user.save()
    return user
    


def basic_user_setup():
    '''
    sets up the basic user setup
    and returns the client
    '''
    from django.urls import reverse
    from django.test import Client
    
    # create user, client and site and assign (client, site) it to user
    user = create_user()
    _client, _site, = create_client_site()
    user.client = _client
    user.bu = _site
    user.save()
    
    # initialize the test client
    client = Client()
    
    # request the login page, this sets up test_cookies like browser
    client.get(reverse('login'))
    
    # post request to login, this saves the session data for the user
    response = client.post(
    reverse('login'), 
    data = {'username':'testuser', 'password':'testpassword', 'timezone':330})

    # get request from the response
    request = response.wsgi_request
    
    # simulate the login of the client
    client.login(**{'username':'testuser', 'password':'testpassword', 'timezone':330})
    
    # update the default session data with user session data got from post request
    session = client.session
    session.update(dict(request.session))
    session.save()
    return client

def get_changed_keys(dict1, dict2):
    """
    This function takes two dictionaries as input and returns a list of keys 
    where the corresponding values have changed from the first dictionary to the second.
    """

    # Handle edge cases where either of the inputs is not a dictionary
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        raise TypeError("Both arguments should be of dict type")

    # Create a list to hold keys with changed values
    changed_keys = []

    # Compare values of common keys in the dictionaries
    for key in dict1.keys() & dict2.keys():
        if dict1[key] != dict2[key]:
            changed_keys.append(key)

    return changed_keys

class Instructions(object): 
    def __init__(self, tablename):
        from apps.onboarding.views import MODEL_RESOURCE_MAP, HEADER_MAPPING
        
        if tablename is None: raise ValueError("The tablename argument is required")
        self.tablename = tablename
        self.model_source_map = MODEL_RESOURCE_MAP
        self.header_mapping = HEADER_MAPPING
        
    def field_choices_map(self, choice_field):
        from django.apps import apps
        Question             = apps.get_model("activity", 'Question')
        Asset                = apps.get_model("activity", 'Asset')
        Location             = apps.get_model("activity", 'Location')
        QuestionSet          = apps.get_model("activity", 'QuestionSet')
        return {
            "Answer Type*": [choice[0] for choice in Question.AnswerType.choices],
            'AVPT Type' : [choice[0] for choice in Question.AvptType.choices],
            'Identifier*' : [choice[0] for choice in Asset.Identifier.choices],
            'Running Status*' : [choice[0] for choice in Asset.RunningStatus.choices],
            'Status*' : [choice[0] for choice in Location.LocationStatus.choices],
            'Type*' : ['SITEGROUP', 'PEOPLEGROUP'],
            'QuestionSet Type*' : [choice[0] for choice in QuestionSet.Type.choices],
        }.get(choice_field)
    
    def get_insructions(self):
        general_instructions = self.get_general_instructions()
        custom_instructions = self.get_custom_instructions()
        column_names = self.get_column_names()
        valid_choices = self.get_valid_choices_if_any()
        format_info = self.get_valid_format_info()
        
        return  {
            'general_instructions': general_instructions + custom_instructions if custom_instructions else general_instructions,
            'column_names':"Columns: ${}&".format(', '.join(column_names)) ,
            'valid_choices':valid_choices,
            'format_info':format_info
        }
    
    def get_general_instructions(self):
        return [
            "Make sure you correctly selected the type of data that you wanna import in bulk. before clicking 'download'",
            "Make sure while filling data in file, your column header does not contain value other than columns mentioned below.",
            "The column names marker asterisk (*) are mandatory to fill"
        ]
    
    def get_custom_instructions(self):
        ic(self.tablename)
        return {
            'SCHEDULEDTOURS':[
                'Make sure you insert the tour details first then you insert its checkpoints.',
                'The Primary data of a checkpoint consist of Seq No, Asset, Question Set/Checklist, Expiry Time',
                'Once you entered the primary data of a checkpoint, for other columns you can copy it from tour details you have just entered',
                'This way repeat the above 3 steps for other tour details and its checkpoints'
            ]
        }.get(self.tablename)
    
    
    def get_column_names(self):
        return self.header_mapping.get(self.tablename)
        
    
    def get_valid_choices_if_any(self):
        table_choice_field_map = {
            "QUESTION": ['Answer Type*', 'AVPT Type'],
            "QUESTIONSET":['QuestionSet Type*'],
            'ASSET':['Identifier*', 'Running Status*'],
            'GROUP':['Type*'],
            'LOCATION': ['Status*']
            }
        if self.tablename in table_choice_field_map:
            valid_choices = []
            for choice_field in table_choice_field_map.get(self.tablename):
                instruction_str = f'Valid values for column: {choice_field} ${", ".join(self.field_choices_map(choice_field))}&'
                valid_choices.append(instruction_str)
            return valid_choices
        return []
    
    def get_valid_format_info(self):
        return [
            'Valid Date Format: $YYYY-MM-DD For example: 1998-06-22&',
            'Valid Mobile No Format: $[ country code ][ rest of number ] For example: 910123456789&' ,
            'Valid Time Format: $HH:MM:SS For example: 23:55:00&',
            'Valid Date Time Format: $YYYY-MM-DD HH:MM:SS For example: 1998-06-22 23:55:00&'
            ]

def generate_timezone_choices():
    from pytz import common_timezones
    from pytz import timezone as pytimezone
    from datetime import datetime
    
    utc = pytimezone('UTC')
    now = datetime.now(utc)
    choices = [('', "")]
    
    for tz_name in common_timezones:
        tz = pytimezone(tz_name)
        offset = now.astimezone(tz).strftime('%z')
        offset_sign = '+' if offset[0] == '+' else '-'
        offset_digits = int(offset.lstrip('+').lstrip('-')) # Remove the sign before converting to int
        offset_hours = abs(int(offset_digits // 100)) # Integer division to get the hours
        offset_minutes = offset_digits % 100 # Modulus to get the minutes
        formatted_offset = f"UTC {offset_sign}{offset_hours:02d}:{offset_minutes:02d}"
        choices.append((f"{tz_name} ({formatted_offset})", f"{tz_name} ({formatted_offset})"))
    
    return choices

def download_qrcode(code, name, report_name, session, request):
    from apps.reports import utils as rutils
    report_essentials = rutils.ReportEssentials(report_name=report_name)
    ReportFormat = report_essentials.get_report_export_object()
    report = ReportFormat(filename=report_name, client_id=session['client_id'],
                              formdata={'print_single_qr':code, 'qrsize':200, 'name':name}, request=request, returnfile=False)
    return report.execute()
