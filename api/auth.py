from django.contrib.auth import  login, logout

from apps.peoples.models import People

class Messages:
    AUTHFAILED     = "Authentication Failed "
    AUTHSUCCESS    = "Authentication Successfull"
    NOSITE         = "Unable to find site!"
    INACTIVE       = "Inactive client or people"
    NOCLIENTPEOPLE = "Unable to find client or People"
    MULTIDEVICES   = "Cannot login on multiple devices, Please logout from the other device"
    WRONGCREDS     = "Incorrect Username or Password"
    NOTREGISTERED  = "Device Not Registered"
    

def LoginUser(response, request):
    if response['isauthenticated']:
        People.objects.filter(
            id = response['user'].id).update(
                deviceid = response['authinput'].deviceid)
        ic(request.user)
    
def LogOutUser(response, request):
    if response['isauthenticated']:
        People.objects.filter(
            id = response['user'].id).update(
                deviceid = -1
            )
        ic(request.user)
            
def auth_check(info, authinput, uclientip=None):
    from django.contrib.auth import authenticate
    from django.forms import model_to_dict
    from apps.peoples.models import People
    import json
    clientcode, sitecode = authinput.sitecode.split('.')
    resp = {'msg':"", 'user':None, 'isauthenticated':False}
    isAuth = True
    try:
        user = People.objects.get(
            client__bucode = clientcode, 
            loginid = authinput.loginid
        )
        user = authenticate(
            info.context,
            username=authinput.loginid,
            password=authinput.password)
        if not user: raise ValueError
    
    except People.DoesNotExist:
        resp['msg'] = Messages.NOCLIENTPEOPLE
    except ValueError:
        resp['msg'] = Messages.WRONGCREDS
    else:
        if isAuth:
            allowAccess = isValidDevice = isUniqueDevice = True
            people_validips = user.client.bu_preferences['validip']
            people_validimeis = user.client.bu_preferences["validimei"].replace(" ", "").split(",")
            
            if people_validips is not None and len(people_validips.replace(" ", "")) > 0:
                clientIpList = people_validips.replace(" ", "").split(",")
                if uclientip is not None and uclientip not in clientIpList:
                    allowAccess = isAuth =False
            if user.deviceid == '-1' or authinput.deviceid == '-1': allowAccess=True
            else:
                if authinput.deviceid not in people_validimeis: isValidDevice=False
                if user.deviceid != authinput.deviceid:
                    resp['msg'] = Messages.MULTIDEVICES
                    allowAccess = isAuth =False
                if not isValidDevice:
                    resp['msg'] = Messages.NOTREGISTERED
                    allowAccess = isAuth =False
            if allowAccess:
                if not user.client.enable or not user.enable:
                    resp['msg'] = Messages.NOCLIENTPEOPLE
                else:
                    resp['isauthenticated'] = True
                    resp['user'] = user
                    resp['msg'] = Messages.AUTHSUCCESS
                    resp['authinput'] = authinput
        
    return resp


def authenticate_user(input, request, msg, returnUser):
    loginid = input.loginid
    password = input.password
    deviceid = input.deviceid

    from graphql import GraphQLError
    from apps.peoples.models import People
    from django.contrib.auth import authenticate
    
    user = authenticate(request, username = loginid, password = password)
    valid_imeis = user.client.bu_preferences["validimei"].replace(" ", "").split(",")
    

    if not user:
        raise GraphQLError(msg.WRONGCREDS)
    if deviceid != '-1' and user.deviceid == '-1':
        if all([user.client.enable, user.enable, user.is_verified]):
            return returnUser(user, request), user
        else:
            raise GraphQLError(msg.NOCLIENTPEOPLE)
    if deviceid not in valid_imeis:
        raise GraphQLError(msg.NOTREGISTERED)
    if deviceid != user.deviceid:
        raise GraphQLError(msg.MULTIDEVICES)
    return returnUser(user, request), user