# save json datafield of Bt table
from icecream import ic
import logging
logger = logging.getLogger('django')


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
        d = {}
        for k, v in bt.bu_preferences.items():
            if k in ('validimei', 'validip', 'reliveronpeoplecount',
                     'pvideolength', 'userreliver'):
                d[k] = v
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
                                       taname='NONE',
                                       tatype='NONE')
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


def get_webcaps_choices():
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
        d = {}
        for k, v in bt.bu_preferences.items():
            if k in ['validimei', 'validip', 'reliveronpeoplecount',
                     'usereliver', 'pvideolength', 'webcapability', 'mobilecapability',
                     'portletcapability', 'reportcapability']:
                d[k] = v
        return ClentForm(data=d)
    except Exception:
        logger.error('get_bt_prefform(bt)... FAILED', exc_info=True)
    else:
        logger.info('get_bt_prefform success')


def create_bt_tree(bucode, butype, instance, parent=None):
    # None Entry
    if bucode == 'NONE':
        return
    # Root Node
    if parent:
        if bucode != 'NONE' and parent.bucode == 'NONE':
            update_children_tree(instance, bucode, butype.tacode)
            instance.butree = f'{butype.tacode} :: {bucode}'
    # Branch Nodes
        if instance.butree != (parent.butree + ' > ' + bucode):
            update_children_tree(instance, bucode, butype.tacode)
            instance.butree = ""
            instance.butree += f"{parent.butree} > {butype.tacode} :: {bucode}"

def create_tenant(buname, bucode):
    #create_tenant for every client
    from apps.tenants.models import Tenant
    _,_ = Tenant.objects.update_or_create(tenantname = buname, subdomain_prefix = bucode.lower())
    
