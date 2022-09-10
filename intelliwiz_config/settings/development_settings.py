from .base_settings import *

DEBUG = True

SECRET_SALT = str(os.getenv('SECRET_SALT'))
ENCRYPT_KEY = str(os.getenv('ENCRYPT_KEY'))

INSTALLED_APPS += ['django_extensions']


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DATABASES.update(
    {
        'default':{
            'ENGINE':   'django.contrib.gis.db.backends.postgis',
            'USER':     'navin',
            'NAME':     'icici_django',
            'PASSWORD': 'admin',
            'HOST':     'localhost',
            'PORT':     '5432',
        },
    }
)

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
]




