import logging
from django.forms.utils import pretty_name

from django.http import request
logger = logging.getLogger('__main__')


def upload_peopleimg(instance, filename):
    try:
        logger.info('uploading peopleimg...')
        from os.path import join
        from django.conf import settings

        peoplecode = instance.peoplecode
        full_filename = peoplecode + "__" + filename
        foldertype = 'people'
        basedir = fyear = fmonth = None
        basedir = "master"
        filepath = join(basedir, foldertype, full_filename)
        filepath = str(filepath).lower()
        fullpath = filepath
    except Exception:
        logger.error(
            'upload_peopleimg(instance, filename)... FAILED', exc_info=True)
    else:
        logger.info('people image uploaded... DONE')
        return fullpath


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


def get_people_prefform(people, session):
    try:
        logger.info('people prefform (json form) retrieving...')
        from .forms import PeopleExtrasForm
        d = {}
        for k, v in people.people_extras.items():
            if k in ('blacklist', 'assignsitegroup', 'tempincludes',
                     'showalltemplates', 'showtemplatebasedonfilter', 'mobilecapability', 'portletcapability',
                     'reportcapability', 'webcapability'):
                d[k] = v
    except Exception:
        logger.error('get_people_prefform(people)... FAILED', exc_info=True)
        raise
    else:
        logger.info('people prefform (json form) retrieved... DONE')
        return PeopleExtrasForm(data=d, session=session)


def save_userinfo(instance, user, session):
    "saves user's related info from request and session"
    from django.shortcuts import redirect
    from apps.tenants.models import Tenant
    from apps.onboarding.models import Bt
    from django.core.exceptions import ObjectDoesNotExist
    if user.is_authenticated:
        try:
            logger.info('saving user info ...')
            logger.info("saving user's tenant & client info...")
            tenantid = session.get('tenantid')
            clientid = session.get('clientid')
            client = Bt.objects.get(btid=clientid)
            tenant = Tenant.objects.get(id=tenantid)
            instance.tenant = tenant
            instance.clientid = client
            logging.info('client and tenant info saved... DONE')
        except (KeyError, ObjectDoesNotExist):
            instance.tenant = None
            instance.clientid = None
        except AttributeError:
            pass
        try:
            if instance.mdtz and instance.cdtz:
                mdtz = instance.mdtz.replace(microsecond=0)
                cdtz = instance.cdtz.replace(microsecond=0)
                if mdtz > cdtz:
                    instance.muser = user
                elif mdtz == cdtz:
                    instance.cuser = instance.muser = user
                else:
                    return redirect('/')
            logging.info('user info saved... DONE')
        except:
            logger.error(
                'save_userinfo(instance, user)... FAILED', exc_info=True)
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


def save_user_session(request, people):
    '''save user info in session'''
    from apps.tenants.utils import get_client_from_hostname
    from django.core.exceptions import ObjectDoesNotExist
    from apps.onboarding.models import Bt
    from apps.tenants.models import Tenant
    try:
        if people.is_superuser == True:
            request.session['is_superadmin'] = True
            session = request.session
            session['people_webcaps'] = session['client_webcaps'] = session['people_mobcaps'] = \
            session['people_reportcaps'] = session['people_portletcaps'] = session['client_mobcaps'] = \
            session['client_reportcaps'] = session['client_portletcaps'] = False
            logger.info(request.session['is_superadmin'])
        else:
            logger.info('saving user session ...')
            clientcode = get_client_from_hostname(request)
            client = Bt.objects.get(bucode=clientcode.upper())
            tenant = Tenant.objects.get(subdomain_prefix=clientcode)
            request.session['tenantid'] = tenant.id
            request.session['clientid'] = client.btid
            request.session['is_superadmin'] = True if people.peoplecode == 'SUPERADMIN' else False
            # get cap choices and save in session data
            get_caps_choices(client=client, session=request.session, people=people)
    except ObjectDoesNotExist:
        logger.error('object not found...', exc_info=True)
        raise
    except Exception:
        logger.critical('something went wrong...', exc_info=True)
        raise
    else:
        logger.info("user and client info saved in session DONE")


def get_choice(li, queryset=False):
    '''return tuple for making choices
        according to django synatax
    '''
    if not queryset:
        label = li[0].capsname
        t = (label, [])
        for i in li[1:]:
            t[1].append((i.capscode, i.capsname))
        tuple(t[1])
        return t
    else:
        label = li[0].parent.capsname
        t = (label, [])
        for i in li:
            t[1].append((i.capscode, i.capsname))
        tuple(t[1])
        return t


def get_cap_choices_for_clientform(caps, cfor):
    choices, temp = [], []
    logger.debug('collecting caps choices for client form...')
    for i in range(1, len(caps)):
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
    choices, tmp = [], []
    logger.info('making choices started ...')
    for i in range(1, len(caps)):
        if caps[i].capscode in caps_assigned and caps[i].depth == 3:
            tmp.append(caps[i])
        if tmp and caps[i].depth == 2 and caps[i-1].depth == 3:
            choices.append(get_choice(tmp, queryset=True))
            tmp = []
        if i == (len(caps)-1) and choices:
            choices.append(get_choice(tmp, queryset=True))
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
        logger.debug(
            'saving capabilities info inside session for people and client...')
        session['people_webcaps'] = make_choices(
            people.people_extras['webcapability'], caps)
        session['people_mobcaps'] = make_choices(
            people.people_extras['mobilecapability'], caps)
        session['people_reportcaps'] = make_choices(
            people.people_extras['reportcapability'], caps)
        session['people_portletcaps'] = make_choices(
            people.people_extras['portletcapability'], caps)
        session['client_webcaps'] = make_choices(
            client.bu_preferences['webcapability'], caps)
        session['client_mobcaps'] = make_choices(
            client.bu_preferences['mobilecapability'], caps)
        session['client_reportcaps'] = make_choices(
            client.bu_preferences['reportcapability'], caps)
        session['client_portletcaps'] = make_choices(
            client.bu_preferences['portletcapability'], caps)
        logger.debug(
            'capabilities info saved in session for people and client... DONE')


def save_user_paswd(user):
    logger.info('Password is created by system... DONE')
    paswd = user.loginid + '@' + user.peoplecode
    user.set_password(paswd)
    



# def decrypt(txt):
#     from django.conf import settings
#     from cryptography.fernet import Fernet
#     import base64
#     txt = base64.urlsafe_b64decode(txt)
#     cipher_suite = Fernet(settings.ENCRYPT_KEY)
#     decoded_text = cipher_suite.decrypt(txt).decode("ascii")
#     return decoded_text


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
