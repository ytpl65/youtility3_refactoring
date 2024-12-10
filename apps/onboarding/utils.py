# save json datafield of Bt table
from icecream import ic
from django.db.models import Q
import re
import os
import requests
import pandas as pd
from tablib import Dataset
import logging
from intelliwiz_config.settings import BULK_IMPORT_GOOGLE_DRIVE_API_KEY as api_key,MEDIA_ROOT
from apps.onboarding.models import Bt, TypeAssist
from apps.peoples.models import People
from apps.core import utils
import json 
from django.http import response as rp


logger = logging.getLogger('django')
dbg = logging.getLogger('__main__').debug

def save_json_from_bu_prefsform(bt, buprefsform):
    ic(buprefsform.cleaned_data)
    try:
        for k, _ in bt.bupreferences.items():
            if k in (
                "validimei",
                "validip",
                "reliveronpeoplecount",
                "pvideolength",
                "usereliver",
                "webcapability",
                "mobilecapability",
                "reportcapability",
                "portletcapability",
                "ispermitneeded",
                "startdate",
                "enddate",
                "onstop",
                "onstopmessage",
                "clienttimezone",
                "billingtype",
                "no_of_device_allowed",
                "devices_currently_added",
                "no_of_users_allowed_web",
                "no_of_users_allowed_both",
                "no_of_users_allowed_mob",
            ):
                bt.bupreferences[k] = buprefsform.cleaned_data.get(k)
    except Exception:
        logger.critical("save json from buprefsform... FAILED", exc_info = True)
        return False
    else:
        logger.info('save_json_from_bu_prefsform(bt, buprefsform) success')
        return True



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
                'no_of_devices_allowed',
                'no_of_users_allowed_mob',
                'no_of_users_allowed_web',
                'no_of_users_allowed_both',
                'devices_currently_added',
                'startdate',
                'enddate',
                'onstop',
                'onstopmessage',
                'clienttimezone',
                'billingtype'
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

        People.objects.create(
            peoplecode=peoplecode,
            peoplename=peoplename,
            dateofbirth=dob,
            dateofjoin=doj,
            mobno=mobno,
            email=email,
            isadmin=True,
        )
        logger.info("Default user-admin created for the client... DONE")
    except Exception:
        logger.critical("Something went wrong while creating default user-admin for client... FAILED",
                     exc_info = True)
        raise



api_key = 'AIzaSyCeionNj4VHSf5RFzvu2VYNYB7Zh1H7MX4'

def extract_file_id(drive_link):
    """Extract the file ID from the Google Drive link."""
    match = re.search(r'/folders/([a-zA-Z0-9-_]+)',drive_link)
    print(match)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Google Drive file link.")

def get_file_metadata(file_id):
    print(file_id)
    """Get metadata for a specific Google Drive file."""
    url = f"https://www.googleapis.com/drive/v3/files?q='{file_id}'+in+parents&key={api_key}&fields=files(id,name,mimeType,size)"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get file metadata: {response.content}")
    
def check_if_name_is_correct(image_name):
    image_name = image_name.split('.')[0]
    regex = re.compile('^[a-zA-Z0-9_#\-\(\)]*$')
    val = re.match(regex,image_name)
    if val:
        return [True," "] 
    return [False, "Image Name is not Correct"]

def check_if_size_of_image_is_correct(image_size):
    if image_size >= 300:
        return [False," Image size is greater than 300KB"] 
    return [True, " "]

def check_if_image_format_is_correct(image_format):
    if image_format not in ['image/png','image/jpeg','image/jpg']:
        return [False,"Image Extension is not correct. Correct Extension should be (.png,.jpeg,.jpg)"]
    return [True," "]

def convert_image_size_to_kb(image_size):
    return int(image_size)//1024


def check_if_the_people_code_with_the_image_name_exists(image_name):
    from apps.peoples.models import People
    peoplecode = image_name.split('.')[0]
    is_exists = People.objects.filter(peoplecode=peoplecode).exists()
    if is_exists:
        return [True, '']
    return [False, f"People with the People Code: {peoplecode} does not exists"]


def is_bulk_image_data_correct(data):
    incorrect_image_data = []
    correct_image_data = []
    for image_data in data:
        print("Image Data: ",image_data)
        image_name = image_data.get('name','')
        image_size = convert_image_size_to_kb(image_data.get('size',0))
        image_data['size'] = image_size
        image_format = image_data.get('mimeType','')
        is_image_name_correct = check_if_name_is_correct(image_name=image_name)
        is_image_size_correct = check_if_size_of_image_is_correct(image_size=image_size)
        is_image_format_correct = check_if_image_format_is_correct(image_format=image_format)
        is_peoplecode_of_image_exists = check_if_the_people_code_with_the_image_name_exists(image_name=image_name)
        errors_message = []
        is_data_correct = True
        if not is_image_name_correct[0]:
            errors_message.append(is_image_name_correct[1])
            is_data_correct = False
        if not is_image_format_correct[0]:
            errors_message.append(is_image_format_correct[1])
            is_data_correct = False
        if not is_image_size_correct[0]:
            errors_message.append(is_image_size_correct[1])
            is_data_correct = False
        if not is_peoplecode_of_image_exists[0]:
            errors_message.append(is_peoplecode_of_image_exists[1])
            is_data_correct = False
        image_data['error'] = errors_message
        if is_data_correct:
            correct_image_data.append(image_data)
        else:
            incorrect_image_data.append(image_data)    
    if len(incorrect_image_data) > 0:
        return False, correct_image_data, incorrect_image_data
    return True, correct_image_data, incorrect_image_data


# Start 
def download_image_from_drive(file_id, destination_path):
    try:
        # Google Drive file download URL
        URL = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # Send a GET request to the URL to download the file
        response = requests.get(URL, stream=True)
        response.raise_for_status()  # Raise an HTTPError if the response was an error

        # Write the downloaded content to the destination path
        with open(destination_path, 'wb') as image_file:
            for chunk in response.iter_content(chunk_size=1024):
                image_file.write(chunk)
        print(f"Image downloaded and saved to {destination_path}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while downloading the image: {e}")

import concurrent.futures
from functools import partial
import os
import requests
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class BulkImageUploader:
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
    
    def download_single_image(self, image_data: Dict, destination_path: str) -> Tuple[bool, str]:
        """Download a single image from Google Drive"""
        try:
            URL = f"https://drive.google.com/uc?export=download&id={image_data['id']}"
            response = requests.get(URL, stream=True)
            response.raise_for_status()

            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            with open(destination_path, 'wb') as image_file:
                for chunk in response.iter_content(chunk_size=8192):
                    image_file.write(chunk)
            return True, destination_path
        except Exception as e:
            logger.error(f"Error downloading image {image_data['name']}: {str(e)}")
            return False, str(e)

    def save_image_to_db(self, people_obj, image_path: str) -> bool:
        """Save image path to database"""
        try:
            people_obj.peopleimg = image_path
            people_obj.save(update_fields=['peopleimg'])
            return True
        except Exception as e:
            logger.error(f"Error saving to database for {people_obj.peoplecode}: {str(e)}")
            return False

    def process_single_image(self, image_data: Dict, base_path: str, people_obj) -> Dict:
        """Process a single image including download and database update"""
        result = {
            'peoplecode': people_obj.peoplecode,
            'success': False,
            'error': None
        }
        
        try:
            image_path = os.path.join(base_path, f"people/{people_obj.peoplecode}/{image_data['name']}")
            download_success, download_result = self.download_single_image(image_data, image_path)
            
            if download_success:
                relative_path = os.path.relpath(image_path, base_path)
                db_success = self.save_image_to_db(people_obj, relative_path)
                result['success'] = db_success
                if not db_success:
                    result['error'] = "Database update failed"
            else:
                result['error'] = download_result
                
        except Exception as e:
            result['error'] = str(e)
            
        return result

def save_image_and_image_path(drive_link: str, media_root: str) -> Tuple[int, List[Dict]]:
    """
    Optimized version of save_image_and_image_path using concurrent operations
    """
    from apps.peoples.models import People
    
    try:
        file_id = extract_file_id(drive_link)
        images_data = get_file_metadata(file_id)['files']
        
        # Prepare people objects dictionary for faster lookup
        peoplecodes = [img['name'].split('.')[0] for img in images_data]
        people_objects = {
            p.peoplecode: p for p in People.objects.filter(peoplecode__in=peoplecodes)
        }
        
        uploader = BulkImageUploader()
        results = []
        
        # Process images in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=uploader.max_workers) as executor:
            future_to_image = {
                executor.submit(
                    uploader.process_single_image,
                    image_data,
                    media_root,
                    people_objects[image_data['name'].split('.')[0]]
                ): image_data
                for image_data in images_data
                if image_data['name'].split('.')[0] in people_objects
            }
            
            for future in concurrent.futures.as_completed(future_to_image):
                result = future.result()
                results.append(result)
        
        successful_uploads = sum(1 for r in results if r['success'])
        return successful_uploads, results
    
    except Exception as e:
        logger.error(f"Error in bulk image upload: {str(e)}")
        raise


# End of New Code


def save_correct_image(correct_image_data):
    for image_data in correct_image_data:
        try:        
            image_id = image_data['id']
            image_name = image_data['name']
            file_path = download_image(image_id,image_name)
            db_image_path = "/".join(file_path.split('/')[4:])
            save_image_in_db(db_image_path, image_name)
        except Exception as e:
            print(f"Failed to save Image {image_name}: {e}")


def save_image_in_db(image_path, image_name):
    image_name = image_name.split('.')[0]
    people = People.objects.get(peoplecode=image_name)
    people.peopleimg = image_path
    people.save()


def get_upload_file_path(image_name):
    base_path = '/var/tmp/youtility4_media/master/sukhi_4/people'
    return os.path.join(base_path,image_name)
    


def download_image(image_id,image_name):
    url = f"https://www.googleapis.com/drive/v3/files/{image_id}?alt=media&key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        file_path = get_upload_file_path(image_name)
        with open(file_path, 'wb') as file:
            file.write(response.content)
        print(f"File Downloaded and saved to location {file_path}")
        return file_path
    else:
        raise Exception("Failed to download Image")
    
def get_resource_and_dataset(request, form, mode_resource_map):
    table = form.cleaned_data.get("table")

    if request.POST.get("action") == "confirmImport":
        tempfile = request.session["temp_file_name"]
        with open(tempfile, "rb") as file:
            df = pd.read_excel(file, skiprows=9)
    else:
        file = request.FILES["importfile"]
        df = pd.read_excel(file, skiprows=9)
        # save to temp storage
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tf:
            for chunk in file.chunks():
                tf.write(chunk)
            request.session["temp_file_name"] = tf.name
    # Replace NaN with None
    df = df.applymap(lambda x: None if pd.isna(x) else x)
    # Convert the DataFrame to a Dataset
    dataset = Dataset()
    dataset.headers = df.columns.tolist()
    for row in df.itertuples(index=False, name=None):
        dataset.append(row)
    res = mode_resource_map[table](
        request=request, ctzoffset=form.cleaned_data.get("ctzoffset")
    )
    return res, dataset

def get_designation_choices(request,P):

    form_instance = P['form_class'](request=request)
    designation_choices = {}

    for key,value in form_instance.fields['designation'].choices:
        designation_choices[str(key)] = value

    designation_choices = json.dumps(designation_choices)
    
    return designation_choices


def get_shift_data(obj):
    data = obj.shift_data.get('designation_details')
    if not data:
        return []
    for record in data:
        if 'overtime' not in record:
            record['overtime'] = 0
        if 'gracetime' not in record:
            record['gracetime'] = 0
    return data

def handle_shift_data_edit(request,self):  
    shift_id = request.POST.get('shift_id')
    shift = utils.get_model_obj(int(shift_id), request, self.params)
    dataa = request.POST.dict()
    action = dataa.get('action')

    data = {}
    
    for key, value in dataa.items():
        if key.startswith('data['):
            field_name = key.split('[')[-1][:-1]
            data[field_name] = value
        else:
            data[key] = value
    
    if not shift.shift_data:
        shift.shift_data = {'designation_details': []}
    elif 'designation_details' not in shift.shift_data:
        shift.shift_data['designation_details'] = []
    
    designation_details = shift.shift_data['designation_details']

    if action == 'create':
        new_data = {
            "id": len(designation_details) + 1,
            "designation":data.get('designation'),
            "count":data.get('count'),
            "overtime": data.get('overtime', '0'),
            "gracetime": data.get('gracetime', '0'),
            "people_code":[]
        }
        designation_details.append(new_data)

    elif action == 'edit':
        edit_id = data.get('id')
        for item in designation_details:
            if item['id'] == int(edit_id):
                item.update({
                    "designation": data.get('designation'),
                    "count": data.get('count'),
                    "overtime": data.get('overtime', item.get('overtime', '0')),
                    "gracetime": data.get('gracetime', item.get('gracetime', '0'))
                })
                break

    elif action == 'remove':
        remove_id =int(data.get('id'))
        designation_details = [item for item in designation_details if item['id'] != remove_id]
        for i, item in enumerate(designation_details, 1):
            item['id'] = i

    shift.shift_data['designation_details'] = designation_details
    shift.save()
    return rp.JsonResponse({'status': 'success'}, status=200)
