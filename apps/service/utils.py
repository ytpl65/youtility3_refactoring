def get_object(uuid, model):
    try:
        return model.objects.get(uuid = uuid)
    except model.DoesNotExist as e:
        raise Exception from e
    
    
def save_jobneeddetails(data):
    import json
    jobneeddetails_post_data = json.loads(data['jobneeddetails'])
    

        
def get_or_create_dir(path):
    try:
        import os
        created=True
        if not os.path.exists(path):
            os.makedirs(path)
        else: created= False
        return created
    except Exception:
        raise

def write_file_to_dir(filebuffer, uploadedfile):
    try:
        with open(uploadedfile, 'wb+') as destination:
            for fb in filebuffer:
                for chunk in fb.chunks():
                    destination.write(chunk)
                    del chunk
                del fb
    except Exception:
        raise

        