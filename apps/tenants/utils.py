

# MAPPING OF HOSTNAME:DATABASE ALIAS NAME 
def get_tenants_map():
    return {
        'sps.youtility.local'       :'sps',
        'capgemini.youtility.local' :'capgemini',
        'dell.youtility.local'      :'dell',
        'icici.youtility.local'     :'icici'
    }

# RETURN HOSTNAME FROM REQUEST 
def hostname_from_request(request):
    # split on `:` to remove port
    hostname = request.get_host().split(':')[0].lower()
    return hostname


# RETURNS DB ALIAS FROM REQUEST
def tenant_db_from_request(request):
    hostname = hostname_from_request(request)
    print(f"Hostname from Request:{hostname}")
    tenants_map = get_tenants_map()
    return tenants_map.get(hostname, 'default')


def get_client_from_hostname(request):
    hostname = hostname_from_request(request)
    return hostname.split('.')[0]

