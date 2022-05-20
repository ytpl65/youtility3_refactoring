from django.conf import settings


def clean_point_field(val):
    
    from django.contrib.gis.geos import GEOSGeometry
    try:
        if 'SRID' not in val:
            lat, lng = val.split(',')
            return GEOSGeometry(f'SRID=4326;POINT({lng} {lat})')
        return GEOSGeometry(val)
    except Exception:
        raise
    

def clean_code(val):
    val = str(val)
    return val.uppper()


def clean_text(val):
    val = str(val)
    return val.title()            


def clean_datetimes(val, offset):
    from datetime import datetime, timedelta, timezone
    tz = timezone(timedelta(minutes=int(offset)))
    val = val.replace("+00:00", "")
    val = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
    return val.replace(tzinfo=tz, microsecond=0)


def clean_date(val):
    from datetime import datetime
    return datetime.strptime(val,  "%Y-%m-%d")



def clean_record(record):
    """
    Cleans the record like code, 
    desc, gps fields, datetime fields etc
    """
    import re
    for k, v in record.items():
        if k in ['jobdesc', 'remarks']:
            record[k] = clean_text(v)
        elif k in ['gpslocation' , 'startlocation', 'endlocation']:
            record[k] = clean_point_field(v)
        elif k in ['cdtz', 'mdtz', 'starttime', 'endtime', 'punchintime', 'punchouttime']:
            record[k] = clean_datetimes(v, record['ctzoffset'])
        elif k in ['geofencecode']:
            record[k] = clean_code(v)
    return record