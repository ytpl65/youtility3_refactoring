from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import ugettext_lazy as _

class PeopleManager(BaseUserManager):
    use_in_migrations =  True
   
    def _create_user(self, loginid, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not loginid:
            raise ValueError('The given loginid must be set')
        user = self.model(loginid=loginid, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, loginid, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(loginid, password, **extra_fields)

    
    def create_superuser(self, loginid, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(loginid, password, **extra_fields)