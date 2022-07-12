from django.contrib.auth.backends import BaseBackend
from django.db.models import Q
from icecream import ic
class MultiAuthentcationBackend(BaseBackend):
    """
    This is a ModelBacked that allows authentication
    with either a username or an email address or mobileno.
    """

    def authenticate(self, request, username=None, password=None):
        '''authenticates user for login credentials'''
        ic("inside new authentication")
        from .models import People
        result = None
        try:
            user = People.objects.get(
               Q(loginid = username) | Q(email=username) | Q(mobno=username))
            ic(user)
            pwd_valid = user.check_password(password)
            ic(pwd_valid)
            if pwd_valid:
                result = user
        except People.DoesNotExist:
            pass
        return result


    def get_user(self, user_id):
        '''return user for given user_id'''
        from .models import People
        result = None
        try:
            user = People.objects.get(pk=user_id)
            result = user
        except People.DoesNotExist:
            pass
        return result