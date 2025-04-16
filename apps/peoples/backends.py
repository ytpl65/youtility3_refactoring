from django.contrib.auth.backends import BaseBackend
from django.db.models import Q
class MultiAuthentcationBackend(BaseBackend):
    """
    This is a ModelBacked that allows authentication
    with either a username or an email address or mobileno.
    """

    @staticmethod
    def authenticate(request, username = None, password = None):
        '''authenticates user for login credentials'''
        from .models import People
        result = None
        try:
            user = People.objects.get(
               Q(loginid = username) | Q(email = username) | Q(mobno = username))
            pwd_valid = user.check_password(password)
            if pwd_valid:
                result = user
        except People.DoesNotExist:
            pass
        return result

    @staticmethod
    def get_user(user_id):
        '''return user for given user_id'''
        from .models import People
        result = None
        try:
            user = People.objects.get(pk = user_id)
            result = user
        except People.DoesNotExist:
            pass
        return result
