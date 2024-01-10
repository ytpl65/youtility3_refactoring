import logging
from apps.peoples import models as pm
from apps.tenants.models import Tenant
from apps.peoples import utils as putils
from apps.core import utils
from django.core.cache import cache
logger = logging.getLogger('__main__')

dbg = logging.getLogger('__main__').debug


def save_jsonform(peoplepref_form, p):
    try:
        logger.info('saving jsonform ...')
        ic(peoplepref_form.cleaned_data)
        for k in [
            'blacklist', 'assignsitegroup', 'tempincludes', 'currentaddress', 'permanentaddress',
            'showalltemplates', 'showtemplatebasedonfilter', 'mobilecapability', 'isemergencycontact',
            'portletcapability', 'reportcapability', 'webcapability', 'isworkpermit_approver', 'alertmails']:
            p.people_extras[k] = peoplepref_form.cleaned_data.get(k)
    except Exception:
        logger.critical(
            'save_jsonform(peoplepref_form, p)... FAILED', exc_info=True)
        raise
    else:
        logger.info('jsonform saved DONE ... ')
        return True


def get_people_prefform(people,  request):
    try:
        logger.info('people prefform (json form) retrieving...')
        from .forms import PeopleExtrasForm
        d = {
            k: v
            for k, v in people.people_extras.items()
            if k
            in (
                'blacklist',
                'assignsitegroup',
                'tempincludes',
                'showalltemplates',
                'showtemplatebasedonfilter',
                'mobilecapability',
                'portletcapability',
                'reportcapability',
                'webcapability',
                'currentaddress',
                'permanentaddress',
                'isemergencycontact',
                'isworkpermit_approver',
                'alertmails'
            )
        }

    except Exception:
        logger.critical('get_people_prefform(people)... FAILED', exc_info=True)
        raise
    else:
        logger.info('people prefform (json form) retrieved... DONE')
        return PeopleExtrasForm(data=d, request=request)


def save_cuser_muser(instance, user, create=None):
    from django.utils import timezone
    #instance is already created
    logger.debug(f"while saving cuser and muser {instance.muser = } {instance.cuser = } {instance.mdtz = } {instance.cdtz = }")
    if instance.cuser is not None:
        logger.info("instance is already created")
        instance.muser = user
        instance.mdtz = timezone.now().replace(microsecond=0)
    #instance is being created
    else:
        logger.info("instance is being created")
        instance.cuser = instance.muser = user
        instance.cdtz = instance.mdtz = timezone.now().replace(microsecond=0)
    return instance


def save_client_tenantid(instance, user, session, client=None, bu=None):

    tenantid = session.get('tenantid')
    if bu is None:
        bu = session.get('bu_id')
    
    if hasattr(instance, 'client_id'):
        client = session.get('client_id') if instance.client_id  in [1, None] else instance.client_id
    if client is None: session.get('client_id')
    
    logger.info('client_id from session: %s', client)
    instance.tenant_id = tenantid
    instance.client_id = client
    instance.bu_id = bu
    logger.info("client info saved...DONE")
    return instance


def save_userinfo(instance, user, session, client=None, bu=None, create=True):
    """saves user's related info('cuser', 'muser', 'client', 'tenantid')
    from request and session"""
    from django.core.exceptions import ObjectDoesNotExist
    if user.is_authenticated:
        try:
            msg = "saving user and client info for the instance have been created"
            logger.info(f'{msg} STARTED')
            instance = save_client_tenantid(
                instance, user, session, client, bu)
            instance = save_cuser_muser(instance, user)
            instance.save()
            logger.info(f"while saving cdtz and mdtz id {instance.cdtz=} {instance.mdtz=}")
            logger.info(f'{msg} DONE')
        except (KeyError, ObjectDoesNotExist):
            instance.tenant = None
            instance.client = None
        except Exception:
            logger.critical("something went wrong !!!", exc_info=True)
            raise
        return instance


def validate_emailadd(val):
    try:
        from django import forms
        from .models import People
        user = People.objects.filter(email__exact=val)
        if not user.exists():
            raise forms.ValidationError("User with this email doesn't exist")
    except Exception:
        logger.critical('validate_emailadd(val)... FAILED', exc_info=True)
        raise


def validate_mobileno(val):
    try:
        from django import forms
        from .models import People
        user = People.objects.filter(mobno__exact=val)
        if not user.exists():
            raise forms.ValidationError(
                "User with this mobile no doesn't exist")
    except Exception:
        logger.error('validate_mobileno(val)... FAILED', exc_info=True)
        raise


def save_tenant_client_info(request):
    from apps.onboarding.models import Bt
    try:
        logger.info('saving tenant & client info into the session...STARTED')
        request.session['client_id'] = request.user.client.id
        request.session['bu_id'] = request.user.bu.id
        logger.info('saving tenant & client info into the session...DONE')
    except Exception:
        logger.critical('save_tenant_client_info failed', exc_info=True)
        raise

def get_caps_from_db():
    from apps.peoples.models import Capability
    from apps.core.raw_queries import get_query
    web, mob, portlet, report = [], [], [], []
    cache_ttl = 20
    web     = cache.get('webcaps')
    mob     = cache.get('mobcaps')
    portlet = cache.get('portletcaps')
    report  = cache.get('reportcaps')
    
    
    if not web:
        web = Capability.objects.get_caps(cfor=Capability.Cfor.WEB)
        ic(web)
        cache.set('webcaps', web, cache_ttl)
    if not mob:
        mob = Capability.objects.get_caps(cfor=Capability.Cfor.MOB)
        cache.set('mobcaps', mob, cache_ttl)
    if not portlet:
        portlet = Capability.objects.get_caps(cfor=Capability.Cfor.PORTLET)
        cache.set('portletcaps', portlet, cache_ttl)
    if not report:
        report = Capability.objects.get_caps(cfor=Capability.Cfor.REPORT)
        cache.set('reportcaps', report, cache_ttl)
    return web, mob, portlet, report
    
    
def create_caps_choices_for_clientform():
    #get caps from db 
    return get_caps_from_db()


def create_caps_choices_for_peopleform(client):
    from apps.peoples.models import Capability
    from apps.core.raw_queries import get_query

    web, mob, portlet, report = [], [], [], []
    
    web     = cache.get('webcaps')
    mob     = cache.get('mobcaps')
    portlet = cache.get('portletcaps')
    report  = cache.get('reportcaps')
    
    if client:
        if not web:
            web = Capability.objects.filter(
                capscode__in = client.bupreferences['webcapability'], cfor=Capability.Cfor.WEB, enable=True).values_list('capscode', 'capsname')
            cache.set('webcaps', web, 30)
        if not mob:
            mob = Capability.objects.filter(
                capscode__in = client.bupreferences['mobilecapability'], cfor=Capability.Cfor.MOB, enable=True).values_list('capscode', 'capsname')
            cache.set('mobcaps', mob, 30)
        if not portlet:
            portlet = Capability.objects.filter(
                capscode__in = client.bupreferences['portletcapability'], cfor=Capability.Cfor.PORTLET, enable=True).values_list('capscode', 'capsname')
            cache.set('portletcaps', portlet, 30)
            ic(portlet)
        if not report:
            report = Capability.objects.filter(
                capscode__in = client.bupreferences['reportcapability'], cfor=Capability.Cfor.REPORT, enable=True).values_list('capscode', 'capsname')
            cache.set('reportcaps', report, 30)
    return web, mob, portlet, report



def save_caps_inside_session_for_people_client(people, caps, session, client):
    logger.debug(
        'saving capabilities info inside session for people and client...')
    #if client and people:
    #    session['people_mobcaps'] = make_choices(client.bu_preferences['mobilecapability'], fromclient=True) 
    session['people_webcaps'] = make_choices(
        people.people_extras['webcapability'], caps)
    session['people_mobcaps'] = make_choices(
        people.people_extras['mobilecapability'], caps)
    session['people_reportcaps'] = make_choices(
        people.people_extras['reportcapability'], caps)
    session['people_portletcaps'] = make_choices(
        people.people_extras['portletcapability'], caps)
    session['client_webcaps'] = make_choices(
        client.bupreferences['webcapability'], caps)
    session['client_mobcaps'] = make_choices(
        client.bupreferences['mobilecapability'], caps)
    session['client_reportcaps'] = make_choices(
        client.bupreferences['reportcapability'], caps)
    session['client_portletcaps'] = make_choices(
        client.bupreferences['portletcapability'], caps)
    logger.debug(
        'capabilities info saved in session for people and client... DONE')


def make_choices(caps_assigned, caps, fromclient=False):
    choices, parent_menus,  tmp = [], [], []
    logger.info('making choices started ...')
    for i in range(1, len(caps)):
        if i.cfor == 'WEB':
            if caps[i].capscode in caps_assigned and caps[i].depth == 3:
                tmp.append(caps[i])
            if tmp and caps[i].depth == 2 and caps[i-1].depth == 3:
                choice, menucode = get_choice(tmp, queryset=True)
                print(choice, menucode)
                parent_menus.append(menucode)
                choices.append(choice)
                tmp = []
            if i == (len(caps)-1) and choices:
                choice, menucode = get_choice(tmp, queryset=True)
                print(choice, menucode)
                parent_menus.append(menucode)
                choices.append(choice)
    if choices:
        ic(choices)
        logger.debug('choices are made and returned... DONE')
    return choices, parent_menus


def get_choice(li, queryset=False):
    '''return tuple for making choices
        according to django synatax
    '''
    if not queryset:
        label = li[0].capscode
        t = (label, [])
        for i in li[1:]:
            t[1].append((i.capscode, i.capsname))
    else:
        label = li[0].parent.capscode
        t = (label, [])
        for i in li:
            t[1].append((i.capscode, i.capsname))

    tuple(t[1])
    return t


def get_cap_choices_for_clientform(caps, cfor):
    # sourcery skip: merge-list-append
    choices, temp = [], []
    logger.debug('collecting caps choices for client form...')
    for i in range(1, len(caps)):
        if caps[i].cfor == 'WEB':
            ic(caps[i].capscode, caps[i].depth, caps[i].path, caps[i].parent_id)
            if caps[i].depth in [3, 2]:
                # print(caps[i].depth)
                if caps[i-1].depth == 3 and caps[i].depth == 2 and caps[i-1].cfor == cfor:
                    choices.append(get_choice(temp))
                    temp = []
                    temp.append(caps[i])
                else:
                    if caps[i].cfor == cfor:
                        temp.append(caps[i])
                    if i == len(caps)-1 and choices:
                        choices.append(get_choice(temp))
    if choices:
        logger.debug('caps collected and returned... DONE')
    return choices


def make_choices(caps_assigned, caps):
    print(caps_assigned)
    choices, tmp = [], []
    logger.info('making choices started ...')
    for i in range(1, len(caps)):
        if caps[i].capscode in caps_assigned and caps[i].depth == 3:
            tmp.append(caps[i])
        if tmp and caps[i].depth == 2 and caps[i-1].depth == 3:
            choice = get_choice(tmp, queryset=True)
            # print(f'tmp {tmp} choice {choice}')
            choices.append(choice)
            tmp = []
        if i == (len(caps)-1) and choices and tmp:
            choice = get_choice(tmp, queryset=True)
            # print(f'tmp {tmp} choice {choice}')
            choices.append(choice)
    if choices:
        logger.debug('choices are made and returned... DONE')
    return choices

# call this method in session to save data inside session


def get_caps_choices(client=None, cfor=None,  session=None, people=None):
    '''get choices for capability clientform 
        or save choices in session'''
    from apps.peoples.models import Capability
    from apps.core.raw_queries import get_query
    from icecream import ic
    caps = Capability.objects.raw(get_query('get_web_caps_for_client'))
    # for cap in caps:
    # print(f'Code {cap.capscode} Depth {cap.depth}')
    if cfor == Capability.Cfor.MOB:
        return Capability.objects.select_related(
            'parent').filter(cfor=cfor, enable=True).values_list('capscode', 'capsname')
    caps = cache.get('caps')
    if caps:
        logger.debug('got caps from cache...')
    if not caps:
        logger.debug('got caps from db...')
        caps = Capability.objects.raw(get_query('get_web_caps_for_client'))
        cache.set('caps', caps, 1*60)
        logger.debug('results are stored in cache... DONE')

    if cfor:
        # return choices for client form
        return get_cap_choices_for_clientform(caps, cfor)




def save_user_paswd(user):
    logger.info('Password is created by system... DONE')
    paswd = f'{user.loginid}@youtility'
    user.set_password(paswd)
    user.save()


def display_user_session_info(session):
    from pprint import pp
    from icecream import ic
    pp('Following user data saved in sesion\n')
    for key, value in session.items():
        pp(f'session info:{key} => {value}')


def get_choices_for_peoplevsgrp(request):
    site = request.user.bu
    return pm.People.objects.filter(
        bu__btid=site.btid).values_list(
            'people', 'peoplename')


def save_pgroupbelonging(pg, request):
    dbg("saving pgbelonging for pgroup %s", (pg))
    from apps.onboarding.models import Bt
    peoples = request.POST.getlist('peoples[]')
    S = request.session
    #delete old grouop info
    ic(pm.Pgbelonging.objects.filter(pgroup = pg).delete())
    if peoples:
        try:
            for i, item in enumerate(peoples):
                people = pm.People.objects.get(id=int(item))
                pgb = pm.Pgbelonging.objects.create(
                    pgroup=pg,
                    people=people,
                    client_id=S['client_id'],
                    bu_id=S['bu_id'],
                    assignsites_id = 1
                )
                if request.session.get('wizard_data'):
                    request.session['wizard_data']['pgbids'].append(pgb.id)
                save_cuser_muser(pgb, request.user)
        except Exception:
            dbg("saving pgbelonging for pgroup %s FAILED", (pg))
            logger.critical("somthing went wrong", exc_info=True)
            raise
        else:
            dbg("saving pgbelonging for pgroup %s DONE", (pg))

