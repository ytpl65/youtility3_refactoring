# save json datafield of Bt table
from icecream import ic
from django.db.models import Q


import logging

from apps.onboarding.models import Bt, TypeAssist
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


def get_tatype_choices(superadmin=False):
    from .models import TypeAssist
    from django.db.models.query_utils import Q

    if superadmin:
        return TypeAssist.objects.all()
    return TypeAssist.objects.filter(
        Q(tatype__tacode='NONE') & ~Q(tacode='NONE') & ~Q(tacode='BU_IDENTIFIER'))


def update_children_tree(instance, newcode, newtype, whole=False):
    """Updates tree of child bu tree's"""
    from apps.core.raw_queries import query
    try:
        if not whole:
            childs = Bt.objects.raw(query['get_childrens_of_bt']%(instance.id))
            ic(childs)
        else: childs = Bt.objects.exclude(id=-1)
        if len(childs) > 1:
            prev_code = instance.bucode
            prev_type = instance.identifier.tacode
            for bt in childs:
                tree = bt.butree
                treepart = prev_type + ' :: ' + prev_code
                newtreepart = newtype + ' :: ' + newcode
                ic(treepart)
                ic(newtreepart)
                ic("before", tree)
                if tree and treepart in tree:
                    newtree = tree.replace(treepart, newtreepart)
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
    from ..core.raw_queries import query
    parent_menus = Capability.objects.raw(query['get_web_caps_for_client'])
    for i in parent_menus:
        print(f'depth: {i.depth} tacode {i.tacode} path {i.path}')
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
        logger.info('Creating BT tree for %s STARTED' % (instance.bucode))
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
        logger.error('Something went wrong while creating Bt tree for instance %s' % (instance.bucode),
                     exc_info=True)
        raise
    else:
        logger.info('BU Tree created for instance %s... DONE' %
                    (instance.bucode))


def create_bv_reportting_heirarchy(instance, newcode, newtype, parent):
    if instance.id != None:
        dbg("Updating the reporting heirarchy!")
        #update bu tree
        if instance.bucode != "NONE" and instance.parent.bucode == 'NONE':
            dbg("Updating heirarchy of the Root Node")
            update_children_tree(instance, newcode, newtype.tacode)
        else:
            dbg("Updating heirarchy of branch Node")
            update_children_tree(instance, newcode, newtype.tacode, whole=True)
        pass
    else:
        dbg("Creating the reporting heirarchy!")
        #create bu tree
        if instance.bucode != "NONE" and parent.bucode == 'NONE':
            #Root Node
            dbg("Creating heirarchy of the Root Node")
            instance.butree = f'{newtype.tacode} :: {newcode}'
        elif instance.butree != (parent.butree + ' > ' + newcode):
            #Non Root Node
            dbg("Creating heirarchy of branch Node")
            instance.butree += f"{parent.butree} > {newtype.tacode} :: {newcode}"
        

def create_tenant(buname, bucode):
    # create_tenant for every client
    from apps.tenants.models import Tenant
    try:
        logger.info(
            'Creating corresponding tenant for client %s ...STARTED' % (bucode))
        _, _ = Tenant.objects.update_or_create(
            defaults={'tenantname':buname}, subdomain_prefix=bucode.lower())
    except Exception:
        logger.error('Something went wrong while creating tenant for the client %s' % (bucode),
                     exc_info=True)
        raise
    else:
        logger.info(
            'Corresponding tenant created for client %s ...DONE' % (bucode))


def create_default_admin_for_client(client):
    from apps.peoples.models import People
    from datetime import date
    peoplecode = client.bucode + '_DEFAULT_ADMIN'
    peoplename = client.bucode + ' Default Admin'
    dob = doj = date.today()
    mobno = '+913851286222'
    email = client.bucode + '@youtility.in'
    try:
        logger.info(
            'Creating default user for the client: %s ...STARTED' % (client.bucode))

        People.objects.create(peoplecode=peoplecode,
                              peoplename=peoplename, dateofbirth=dob,
                              dateofjoin=doj, mobno=mobno, email=email,
                              isadmin=True)
        logger.info('Default user-admin created for the client... DONE')
    except Exception:
        logger.error("Something went wrong while creating default user-admin for client... FAILED",
                     exc_info=True)
        raise



