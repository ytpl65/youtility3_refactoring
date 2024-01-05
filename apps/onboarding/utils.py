# save json datafield of Bt table
from icecream import ic
from django.db.models import Q

import logging

from apps.onboarding.models import Bt, TypeAssist
logger = logging.getLogger('django')
dbg = logging.getLogger('__main__').debug

def save_json_from_bu_prefsform(bt, buprefsform):
    ic(buprefsform.cleaned_data)
    try:
        for k, _ in bt.bupreferences.items():
            if k in ('validimei', 'validip', 'reliveronpeoplecount',
                     'pvideolength', 'usereliver', 'webcapability', 'mobilecapability',
                     'reportcapability', 'portletcapability', 'ispermitneeded'):
                bt.bupreferences[k] = buprefsform.cleaned_data.get(k)
    except Exception:
        logger.critical("save json from buprefsform... FAILED", exc_info = True)
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
            for k, v in bt.bupreferences.items()
            if k
            in (
                'validimei',
                'validip',
                'reliveronpeoplecount',
                'pvideolength',
                'userreliver',
                'ispermitneeded'
            )
        }

    except Exception:
        logger.critical("get_bu_prefform... FAILED", exc_info = True)
    else:
        logger.info("get_bu_prefform success")
        return BuPrefForm(data = d)

def get_tatype_choices(superadmin = False):

    if superadmin:
        return TypeAssist.objects.all()
    return TypeAssist.objects.filter(
        Q(tatype__tacode='NONE') & ~Q(tacode='NONE') & ~Q(tacode='BU_IDENTIFIER'))

def update_children_tree(instance, newcode, newtype, whole = False):
    """Updates tree of child bu tree's"""
    try:
        childs = Bt.objects.get_all_bu_of_client(instance.id)
        ic(instance.id, childs)
        ic(instance.bucode, newcode)
        if len(childs) > 1:
            childs = Bt.objects.filter(id__in = childs).order_by('id')
            print(childs)
            for bt in childs:
                oldtree = instance.butree
                oldtreepart = f'{instance.identifier.tacode} :: {instance.bucode}'
                newtreepart = f'{newtype} :: {newcode}'

                if oldtree == oldtreepart:
                    ic('saved')
                    instance.butree = newtreepart
                    instance.save()
                elif oldtree and oldtreepart != newtreepart:
                    newtree = bt.butree.replace(oldtreepart, newtreepart)
                    bt.butree = newtree
                    bt.save()
                    ic(bt.bucode)
    except Exception:
        logger.critical(
            "update_children_tree(instance, newcode, newtype)... FAILED", exc_info = True)
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
    from ..core.raw_queries import get_query
    parent_menus = Capability.objects.raw(get_query('get_web_caps_for_client'))
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
            for k, v in bt.bupreferences.items()
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

        return ClentForm(data = d)
    except Exception:
        logger.critical('get_bt_prefform(bt)... FAILED', exc_info = True)
    else:
        logger.info('get_bt_prefform success')

def create_bt_tree(bucode, indentifier, instance, parent = None):
    # sourcery skip: remove-redundant-if
    # None Entry
    try:
        logger.info(f'Creating BT tree for {instance.bucode} STARTED')
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
        logger.critical(f'Something went wrong while creating Bt tree for instance {instance.bucode}', exc_info = True)

        raise
    else:
        logger.info('BU Tree created for instance %s... DONE', (instance.bucode))

def create_bv_reportting_heirarchy(instance, newcode, newtype, parent):
    if instance.id is None:
        dbg("Creating the reporting heirarchy!")
        # create bu tree
        ic(instance.bucode, parent, newcode, newtype)
        if hasattr(instance, 'bucode')  and hasattr(parent, 'bucode'):
            if instance.bucode != "NONE" and parent.bucode == 'NONE':
                # Root Node
                dbg("Creating heirarchy of the Root Node")
                instance.butree = f'{newtype.tacode} :: {newcode}'
            elif instance.butree != f'{parent.butree} > {newtype.tacode} :: {newcode}':
                # Non Root Node
                dbg("Creating heirarchy of branch Node")
                instance.butree += f"{parent.butree} > {newtype.tacode} :: {newcode}"

    else:
        dbg("Updating the reporting heirarchy!")
        # update bu tree
        if instance.bucode not in(None, 'NONE') and hasattr(instance.parent, 'bucode') and instance.parent.bucode in (None, 'NONE'):
            dbg("Updating heirarchy of the Root Node")
            update_children_tree(instance, newcode, newtype.tacode)
        else:
            dbg("Updating heirarchy of branch Node")
            update_children_tree(instance, newcode, newtype.tacode)

def create_tenant(buname, bucode):
    # create_tenant for every client
    from apps.tenants.models import Tenant
    try:
        logger.info(
            'Creating corresponding tenant for client %s ...STARTED', (bucode))
        _, _ = Tenant.objects.update_or_create(
            defaults={'tenantname':buname}, subdomain_prefix = bucode.lower())
    except Exception:
        logger.critical('Something went wrong while creating tenant for the client %s', (bucode), exc_info = True)
        raise
    else:
        logger.info(
            'Corresponding tenant created for client %s ...DONE', (bucode))

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
            'Creating default user for the client: %s ...STARTED', (client.bucode))

        People.objects.create(peoplecode = peoplecode,
                              peoplename = peoplename, dateofbirth = dob,
                              dateofjoin = doj, mobno = mobno, email = email,
                              isadmin = True)
        logger.info('Default user-admin created for the client... DONE')
    except Exception:
        logger.critical("Something went wrong while creating default user-admin for client... FAILED",
                     exc_info = True)
        raise


