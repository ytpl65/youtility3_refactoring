import logging
from apps.peoples import models as pm
from apps.tenants.models import Tenant
from django.db import transaction
from apps.core import utils
logger = logging.getLogger('__main__')

dbg = logging.getLogger('__main__').debug





def save_jsonform(peoplepref_form, p):
    try:
        logger.info('saving jsonform ...')
        for k, v in p.people_extras.items():
            if k in ('blacklist', 'assignsitegroup', 'tempincludes',
                     'showalltemplates', 'showtemplatebasedonfilter', 'mobilecapability',
                     'portletcapability', 'reportcapability', 'webcapability'):
                p.people_extras[k] = peoplepref_form.cleaned_data[k]
    except Exception:
        logger.error(
            'save_jsonform(peoplepref_form, p)... FAILED', exc_info=True)
        raise
    else:
        logger.info('jsonform saved DONE ... ')
        return True


def get_people_prefform(people, session):
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
            )
        }

    except Exception:
        logger.error('get_people_prefform(people)... FAILED', exc_info=True)
        raise
    else:
        logger.info('people prefform (json form) retrieved... DONE')
        return PeopleExtrasForm(data=d, session=session)


def save_cuser_muser(instance, user):
    if instance.mdtz and instance.cdtz:
        mdtz = instance.mdtz.replace(microsecond=0)
        cdtz = instance.cdtz.replace(microsecond=0)
        if mdtz > cdtz:
            instance.muser = user
        elif mdtz == cdtz:
            instance.cuser = instance.muser = user
        logger.info("saving cuser muser info saved ...DONE")
    return instance


def save_clientid_tenantid(instance, user, session, clientid=None, buid=None):

    tenantid = session.get('tenantid')
    if buid is None:
        buid = session.get('buid')
    if clientid is None:
        clientid = session.get('clientid')
    instance.tenant_id   = tenantid
    instance.clientid_id = clientid
    instance.buid_id     = buid
    logger.info("client info saved...DONE")
    return instance



def save_userinfo(instance, user, session,clientid=None, buid=None):
    """saves user's related info('cuser', 'muser', 'clientid', 'tenantid')
    from request and session"""
    from django.core.exceptions import ObjectDoesNotExist
    if user.is_authenticated:
        try:
            msg = "saving user and client info for the instance have been created"
            logger.info(msg + " STARTED")
            instance = save_clientid_tenantid(instance, user, session, clientid, buid)
            instance = save_cuser_muser(instance, user)
            instance.save()
            logger.info(msg + " DONE")
        except (KeyError, ObjectDoesNotExist):
            instance.tenant = None
            instance.clientid = None
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
        logger.error('validate_emailadd(val)... FAILED', exc_info=True)
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
    from apps.core.utils import hostname_from_request, get_tenants_map
    from apps.onboarding.models import Bt
    from apps.tenants.models import Tenant
    try:
        logger.info('saving tenant & client info into the session...STARTED')
        hostname = hostname_from_request(request)
        clientcodeMap = get_tenants_map()
        clientcode = clientcodeMap.get(hostname)
        request.session['hostname'] = hostname
        client = Bt.objects.get(bucode=clientcode.upper())
        tenant = Tenant.objects.get(subdomain_prefix=clientcode)
        request.session['tenantid'] = tenant.id
        request.session['clientid'] = client.id
        request.session['buid'] = request.user.buid.id
        logger.info('saving tenant & client info into the session...DONE')
    except:
        raise
    else:
        return client




# def get_choice(li, queryset=False):
#     '''return tuple for making choices
#         according to django synatax
#     '''
#     code = None
#     if li:
#         if not queryset:
#             label = li[0].capsname
#             t = (label, [])
#             for i in li[1:]:
#                 t[1].append((i.capscode, i.capsname))
#         else:
#             label, code = li[0].parent.capsname, li[0].parent.capscode
#             t = (label, [])
#             for i in li:
#                 t[1].append((i.capscode, i.capsname))

#         tuple(t[1])
#         return t, code


# def get_cap_choices_for_clientform(caps, cfor):
#     # sourcery skip: merge-list-append
#     choices, temp = [], []
#     logger.debug('collecting caps choices for client form...')
#     for i in range(1, len(caps)):
#         if caps[i].depth in [3, 2]:
#             if caps[i-1].depth == 3 and caps[i].depth == 2 and caps[i-1].cfor == cfor:
#                 choice, _  = get_choice(temp)
#                 choices.append(choice)
#                 temp = []
#                 temp.append(caps[i])
#             else:
#                 if caps[i].cfor == cfor:
#                     temp.append(caps[i])
#                 if i == len(caps)-1 and choices:
#                     choice, _  = get_choice(temp)
#                     choices.append(choice)
#     if choices:
#         logger.debug('caps collected and returned... DONE')
#     return choices

# this will return choices for heirarchical choices for select2 dropdowns


# def make_choices(caps_assigned, caps):
#     choices, parent_menus,  tmp = [], [], []
#     logger.info('making choices started ...')
#     for i in range(1, len(caps)):
#         if caps[i].capscode in caps_assigned and caps[i].depth == 3:
#             tmp.append(caps[i])
#         if tmp and caps[i].depth == 2 and caps[i-1].depth == 3:
#             choice, menucode = get_choice(tmp, queryset=True)
#             print(choice, menucode)
#             parent_menus.append(menucode)
#             choices.append(choice)
#             tmp = []
#         if i == (len(caps)-1) and choices:
#             choice, menucode = get_choice(tmp, queryset=True)
#             print(choice, menucode)
#             parent_menus.append(menucode)
#             choices.append(choice)
#     if choices:
#         logger.debug('choices are made and returned... DONE')
#     return choices, parent_menus

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
            #print(f'tmp {tmp} choice {choice}')
            choices.append(choice)
            tmp = []
        if i == (len(caps)-1) and choices and tmp:
            choice = get_choice(tmp, queryset=True)
            #print(f'tmp {tmp} choice {choice}')
            choices.append(choice)
    if choices:
        logger.debug('choices are made and returned... DONE')
    return choices


# call this method in session to save data inside session
def get_caps_choices(client=None, cfor=None,  session=None, people=None):
    '''get choices for capability clientform 
        or save choices in session'''
    from apps.peoples.models import Capability
    from apps.onboarding.raw_queries import query
    from django.core.cache import cache
    from icecream import ic
    caps = Capability.objects.raw(query['get_web_caps_for_client'])
    # for cap in caps:
    #print(f'Code {cap.capscode} Depth {cap.depth}')
    try:
        caps = cache.get('caps')
        if caps:
            logger.debug('got caps from cache...')
        if not caps:
            logger.debug('got caps from db...')
            caps = Capability.objects.raw(query['get_web_caps_for_client'])
            cache.set('caps', caps, 1*60)
            logger.debug('results are stored in cache... DONE')
    except Exception:
        raise

    if cfor:
        # return choices for client form
        return get_cap_choices_for_clientform(caps, cfor)

    elif session and people and client:
        utils.save_caps_inside_session_for_people_client(
            people, caps, session, client)

# TODO Rename this here and in `get_caps_choices`




def save_user_paswd(user):
    logger.info('Password is created by system... DONE')
    paswd = user.loginid + '@' + 'youtility'
    user.set_password(paswd)
    user.save()


def display_user_session_info(session):
    from pprint import pp
    from icecream import ic
    pp('Following user data saved in sesion\n')
    for key, value in session.items():
        pp('session info:{} => {}'.format(key, value))


def get_choices_for_peoplevsgrp(request):
    site = request.user.buid
    return pm.People.objects.filter(
        buid__btid=site.btid).values_list(
            'peopleid', 'peoplename')


def save_pgroupbelonging(pg, request):
    dbg("saving pgbelonging for pgroup %s" % (pg))
    from apps.onboarding.models import Bt
    peoples = request.POST.getlist('peoples')
    client = Bt.objects.get(id=int(request.session['clientid']))
    site = Bt.objects.get(id=int(request.session['buid']))
    tenant = Tenant.objects.get(id=int(request.session['tenantid']))
    if peoples:
        try:
            with transaction.atomic():
                print('request>POST', dict(request.POST), peoples)
                for i in range(len(peoples)):
                    people = pm.People.objects.get(id=int(peoples[i]))
                    pgb = pm.Pgbelonging.objects.create(
                        groupid=pg,
                        peopleid=people,
                        clientid=client,
                        tenant=tenant,
                        buid=site
                    )
                    if request.session.get('wizard_data'):
                        request.session['wizard_data']['pgbids'].append(pgb.id)
                    save_cuser_muser(pgb, request.user)
        except Exception:
            dbg("saving pgbelonging for pgroup %s FAILED" % (pg))
            raise
        else:
            dbg("saving pgbelonging for pgroup %s DONE" % (pg))

# def encrypt(txt):
#     from django.conf import settings
#     from cryptography.fernet import Fernet
#     import base64
#     # convert integer etc to string first
#     txt = str(txt)
#     # get the key from settings
#     cipher_suite = Fernet(settings.ENCRYPT_KEY) # key should be byte
#     # #input should be byte, so convert the text to byte
#     encrypted_text = cipher_suite.encrypt(txt.encode('ascii'))
#     # encode to urlsafe base64 format
#     encrypted_text = base64.urlsafe_b64encode(encrypted_text).decode("ascii")
#     return encrypted_text


