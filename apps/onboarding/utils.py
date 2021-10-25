# save json datafield of Bt table
import django
from django.db.models.deletion import RestrictedError
from icecream import ic
import django.shortcuts as scts
import django.contrib.messages as msg


import logging
logger = logging.getLogger('django')
dbg = logging.getLogger('__main__').debug


def save_json_from_bu_prefsform(bt, buprefsform):
    try:
        for k, _ in bt.bu_preferences.items():
            if k in ('validimei', 'validip', 'reliveronpeoplecount',
                    'pvideolength', 'usereliver', 'webcapability', 'mobilecapability',
                    'reportcapability', 'portletcapability'):
                bt.bu_preferences[k] = buprefsform.cleaned_data.get(k)
    except Exception:
        logger.error("save json from buprefsform... FAILED", exc_info=True)
        return False
    else:
        logger.info('save_json_from_bu_prefsform(bt, buprefsform) success')
        return True


# returns Bt json form
def get_bu_prefform(bt):
    from .forms import BuPrefForm
    try:
        d = {
            k: v
            for k, v in bt.bu_preferences.items()
            if k
            in (
                'validimei',
                'validip',
                'reliveronpeoplecount',
                'pvideolength',
                'userreliver',
            )
        }

    except Exception:
        logger.error("get_bu_prefform... FAILED", exc_info=True)
    else:
        logger.info("get_bu_prefform success")
        return BuPrefForm(data=d)


def get_tatype_choices():
    from .models import TypeAssist
    try:
        ta = TypeAssist.objects.select_related().get(tacode='NONE')
    except:
        ta = TypeAssist.objects.create(tacode='NONE',
                taname='NONE',tatype='NONE')
    parents = ta.get_all_children()
    choices = [("", "")]
    for idx, ele in enumerate(parents):
        choices.append((ele.tacode, str(ele.taname)))
    return choices


def update_children_tree(instance, newcode, newtype):
    """Updates tree of child bu tree's"""
    try:
        childs = instance.get_all_children()
        ic(childs)
        if len(childs) > 1:
            prev_code = instance.bucode
            prev_type = instance.butype.tacode
            for bt in childs:
                tree = bt.butree
                ic("before", tree)
                if (prev_type + ' :: ' + prev_code) in tree:
                    newtree = tree.replace(prev_code, newcode)
                    newtree = newtree.replace(prev_type, newtype)
                    bt.butree = newtree
                    bt.save()
                    ic('after', bt.butree)
    except Exception:
        logger.error(
            "update_children_tree(instance, newcode, newtype)... FAILED", exc_info=True)
    else:
        logger.info('update_children_tree(instance, newcode, newtype) success')


# Dynamic rendering for capability data
def get_choice(li):
    label = li[0].capsname
    t = (label, [])
    for i in li[1:]:
        t[1].append((i.capscode, i.capsname))
    tuple(t[1])
    return t


def get_webcaps_choices():  # sourcery skip: merge-list-append
    '''Populates parent data in parent-multi-select field'''
    from apps.peoples.models import Capability
    from django.db.models import Q
    from .raw_queries import query
    parent_menus = Capability.objects.raw(query['get_web_caps_for_client'])
    choices, temp = [], []
    for i in range(1, len(parent_menus)):
        if parent_menus[i-1].depth == 3 and parent_menus[i].depth == 2:
            choices.append(get_choice(temp))
            temp = []
            temp.append(parent_menus[i])
        else:
            temp.append(parent_menus[i])
            if i == len(parent_menus)-1:
                choices.append(get_choice(temp))
    return choices


def get_bt_prefform(bt):
    try:
        from .forms import ClentForm
        d = {
            k: v
            for k, v in bt.bu_preferences.items()
            if k
            in [
                'validimei',
                'validip',
                'reliveronpeoplecount',
                'usereliver',
                'pvideolength',
                'webcapability',
                'mobilecapability',
                'portletcapability',
                'reportcapability',
            ]
        }

        return ClentForm(data=d)
    except Exception:
        logger.error('get_bt_prefform(bt)... FAILED', exc_info=True)
    else:
        logger.info('get_bt_prefform success')


def create_bt_tree(bucode, indentifier, instance, parent=None):
    # sourcery skip: remove-redundant-if
    # None Entry
    try:
        logger.info('Creating BT tree for %s STARTED'%(instance.bucode))
        if bucode == 'NONE':
            return
        # Root Node
        if parent:
            if bucode != 'NONE' and parent.bucode == 'NONE':
                update_children_tree(instance, bucode, indentifier.tacode)
                instance.butree = f'{indentifier.tacode} :: {bucode}'
        # Branch Nodes
            elif instance.butree != (parent.butree + ' > ' + bucode):
                update_children_tree(instance, bucode, indentifier.tacode)
                instance.butree = ""
                instance.butree += f"{parent.butree} > {indentifier.tacode} :: {bucode}"
    except Exception:
        logger.error('Something went wrong while creating Bt tree for instance %s'%(instance.bucode),
        exc_info=True)
        raise
    else:
        logger.info('BU Tree created for instance %s... DONE'%(instance.bucode))


def create_tenant(buname, bucode):
    #create_tenant for every client
    from apps.tenants.models import Tenant
    try:
        logger.info('Creating corresponding tenant for client %s ...STARTED'%(bucode))
        _,_ = Tenant.objects.update_or_create(tenantname = buname, subdomain_prefix = bucode.lower())
    except Exception:
        logger.error('Something went wrong while creating tenant for the client %s'%(bucode), 
        exc_info=True)
        raise
    else:
        logger.info('Corresponding tenant created for client %s ...DONE'%(bucode))


def create_default_admin_for_client(client):
    from apps.peoples.models import People
    from datetime import date
    peoplecode = client.bucode + '_DEFAULT_ADMIN'
    peoplename = client.bucode + ' Default Admin'
    dob = doj = date.today()
    mobno = '+913851286222'
    email = client.bucode + '@youtility.in'
    try:
        logger.info('Creating default user for the client: %s ...STARTED'%(client.bucode))
        
        People.object.create(peoplecode = peoplecode,
        peoplename = peoplename, dateofbirth = dob, 
        dateofjoin = doj, mobno = mobno, email = email, 
        isadmin = True)
        logger.info('Default user-admin created for the client... DONE')
    except Exception:
        logger.error("Something went wrong while creating default user-admin for client... FAILED",
        exc_info=True) 
        raise


def process_wizard_form(request, wizard_data, update=False):
    logger.info('processing wizard started...', )
    print('wizard_Data....', wizard_data)
    resp = None
    wiz_session = request.session['wizard_data']
    if not wizard_data['last_form']:
        logger.info('wizard its NOT last form')    
        if not update:
            logger.info('processing wizard not an update form')
            wiz_session[wizard_data['current_ids']].append(wizard_data['instance_id'])
            request.session['wizard_data'].update(wiz_session)
            resp = scts.redirect(wizard_data['current_url'])
        else:
            resp = update_wizard_form(wizard_data, wiz_session, request)
    else:
        resp = scts.redirect('onboarding:wizard_view')
    return resp 



def update_wizard_form(wizard_data, wiz_session, request):
    # sourcery skip: lift-return-into-if, remove-unnecessary-else
    resp = None
    logger.info('processing wizard is an update form')
    if wizard_data['instance_id'] not in wiz_session[wizard_data['current_ids']]:
        wiz_session[wizard_data['current_ids']].append(wizard_data['instance_id'])
    if wiz_session[wizard_data['next_ids']]:
        resp = scts.redirect(wizard_data['next_update_url'], pk = wiz_session[wizard_data['next_ids']][-1])
    else:
        request.session['wizard_data'].update(wiz_session)
        resp = scts.redirect(wizard_data['current_url'])
    return resp


def handle_other_exception(request, form, form_name, template, jsonform="", jsonform_name=""):
    logger.critical("something went wrong...", exc_info=True)
    msg.error(request, "[ERROR] Something went wrong",
    "alert-danger")
    cxt = {form_name:form, 'edit':True, jsonform_name:jsonform}
    return scts.render(request, template, context=cxt)


def handle_does_not_exist(request, url):
    logger.error('Object does not exist', exc_info= True)
    msg.error(request, "Object does not exist",
    "alert alert-danger")
    return scts.redirect(url)


def delete_object(request, model,lookup, ids, temp, 
form, url, form_name, jsonformname=None, jsonform=None):
    
    try:
        logger.info('Request for object delete...')
        res, obj = None, model.objects.get(**lookup)
        form = form(instance = obj)
        obj.delete()
        msg.success(request, "Entry has been deleted successfully", 'alert-success')
        request.session['wizard_data'][ids].pop()
        logger.info('Object deleted')
        res = scts.redirect(url)
    except model.DoesNotExist:
        logger.error('Unable to delete, object does not exist')
        msg.error(request, 'Client does not exist', "alert alert-danger")
        res = scts.redirect(url)
    except RestrictedError:
        logger.warn('Unable to delete, duw to dependencies')
        msg.error(request, 'Unable to delete, duw to dependencies')
        cxt = {form_name:form, jsonformname:jsonform, 'edit':True}
        res = scts.render(request, temp, context=cxt)
    except Exception:
        msg.error(request, '[ERROR] Something went wrong', "alert alert-danger")
        cxt = {form_name:form, jsonformname:jsonform, 'edit':True}
        res = scts.render(request, temp, context=cxt)
    return res


def delete_unsaved_objects(model, ids):
    if ids:
        try:
            logger.info('Found unsaved objects in session going to be deleted...')
            model.objects.filter(pk__in = ids).delete()
        except:
            raise
        else:
            logger.info('Unsaved objects are deleted...DONE')


def update_prev_step(step_url, request):
    url, ids = step_url
    session = request.session['wizard_data']
    instance = session.get(ids)[-1] if session.get(ids) else None
    new_url = url.replace('form', 'update') if instance and ('update' not in url) else url
    request.session['wizard_data'].update(
        {'prev_inst':instance,
        'prev_url':new_url})


def update_next_step(step_url, request):
    url, ids = step_url
    session = request.session['wizard_data']
    instance = session.get(ids)[-1] if session.get(ids) else None
    new_url = url.replace('form', 'update') if instance and ('update' not in url) else url
    request.session['wizard_data'].update(
        {'next_inst':instance,
        'next_url':new_url})


def update_other_info(step, request, current, formid):
    url, ids = step[current]
    session = request.session['wizard_data']
    session['current_step'] = session['steps'][current] 
    session['current_url'] = url
    session['final_url'] = step['final_step'][0]
    session['formid'] = formid
    session['del_url'] =  url.replace('form', 'delete')
    instance = session.get(ids)[-1] if session.get(ids) else None
    session['current_inst'] = instance
    


def update_wizard_steps(request, current, prev, next, formid):
    '''Updates wizard next, current, prev, final urls'''
    step_urls = {
        'buform':('onboarding:wiz_bu_form','buids'),
        'shiftform':('onboarding:wiz_shift_form','shiftids'),
        'peopleform':('peoples:wiz_people_form','peopleids'),
        'pgroupform':('peoples:wiz_pgroup_form','pgroupids'),
        'final_step':('onboarding:wizard_preview', '')}
    #update prev step
    update_prev_step(step_urls.get(prev, ("", "")), request)
    #update next step
    update_next_step(step_urls.get(next, ("", "")), request)
    #update other info
    update_other_info(step_urls, request, current, formid)
    


def save_msg(request):
    '''Displays a success message'''
    return msg.success(request, 'Entry has been saved successfully!', 'alert-success')


def initailize_form_fields(form):
    for visible in form.visible_fields():
        if visible.widget_type not in ['file', 'checkbox', 'clearablefile', 'select', 'selectmultiple']:
            visible.field.widget.attrs['class'] = 'form-control'
        if visible.widget_type == 'checkbox':
            visible.field.widget.attrs['class'] = 'form-check-input h-20px w-30px'
            dbg("...........clasess applied to checkboxes fields ...........")
        if visible.widget_type in ['select2', 'modelselect2', 'select2multiple']:
            dbg("...........clasess applied to select fields ...........")
            visible.field.widget.attrs['class']            = 'form-select'
            visible.field.widget.attrs['data-placeholder'] = 'Select an option'
            visible.field.widget.attrs['data-allow-clear'] = 'true'

    
    
def apply_error_classes(form):
    # loop on *all* fields if key '__all__' found else only on errors:
    for x in (form.fields if '__all__' in form.errors else form.errors):
        attrs = form.fields[x].widget.attrs
        attrs.update({'class': attrs.get('class', '') + ' is-invalid'})