from .base_settings import *

DEBUG = True

SECRET_SALT = str(os.getenv('SECRET_SALT'))
ENCRYPT_KEY = str(os.getenv('ENCRYPT_KEY'))

INSTALLED_APPS += ['django_extensions']



EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


DATABASES.update(
    {
        'icicibank':{
            'ENGINE':   'django.contrib.gis.db.backends.postgis',
            'USER':     DBUSER,
            'NAME':     'icici_django',
            'PASSWORD': DBPASWD,
            'HOST':     DBHOST,
            'PORT':     '5432',
        },
        'testDB':{
            'ENGINE':   'django.contrib.gis.db.backends.postgis',
            'USER':     DBUSER,
            'NAME':     'testDB',
            'PASSWORD': DBPASWD,
            'HOST':     DBHOST,
            'PORT':     '5432',
        },
    }
)

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
]

#GRAPHENE CONF...
GRAPHENE = {
    # ...
    "ATOMIC_MUTATIONS": True,
    "SCHEMA": "apps.service.schema.schema",
    'MIDDLEWARE': [
        'graphene_django.debug.DjangoDebugMiddleware',
        "graphql_jwt.middleware.JSONWebTokenMiddleware",
    ]
}


#Email Verification CONF...
def verified_callback(user):
    user.isverified = True


EMAIL_VERIFIED_CALLBACK = verified_callback
EMAIL_FROM_ADDRESS = 'snvnrock@gmail.com'
EMAIL_MAIL_SUBJECT = 'Confirm your email'
EMAIL_MAIL_HTML = 'email.html'
EMAIL_MAIL_PLAIN = 'mail_body.txt'
EMAIL_TOKEN_LIFE = 60**2
EMAIL_PAGE_TEMPLATE = 'email_verify.html'
EMAIL_PAGE_DOMAIN = 'http://127.0.0.1:8000/'
EMAIL_MULTI_USER = True  # optional (defaults to False)



# For Django Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = "snvnrock@gmail.com"
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'mwaghtest@gmail.com'
EMAIL_HOST_PASSWORD = 'mwaghtest@123'  # os.environ['password_key'] suggested
EMAIL_USE_TLS = True


#DJANGO_IMPORT_EXPORT CONF...
IMPORT_EXPORT_USE_TRANSACTIONS = True


#DJANGO-EXTENSIONS CONF...
SHELL_PLUS_PRINT_SQL = True
GRAPH_MODELS = {
  'all_applications': True,
  'group_models': True,
}

#GRAPHQL JWT CONF...
from datetime import timedelta
GRAPHQL_JWT = {
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_EXPIRATION_DELTA": timedelta(minutes = 7*24*60),
    "JWT_REFRESH_EXPIRATION_DELTA": timedelta(days = 7),
    # optional
    "JWT_LONG_RUNNING_REFRESH_TOKEN": True,
}




#GOOGLE MAP API KEY...
GOOGLE_MAP_SECRET_KEY  = str(os.getenv('GOOGLE_MAP_SECRET_KEY'))


#CELERY CONF...
CELERY_BROKER_URL = str(os.getenv('CELERY_BROKER_URL'))
CELERY_CACHE_BACKEND = str(os.getenv('CELERY_CACHE_BACKEND'))
CELERY_RESULT_BACKEND = str(os.getenv('CELERY_RESULT_BACKEND'))

#SELECT2 CONF...
SELECT2_CACHE_BACKEND = 'select2'
SELECT2_JS = ""
SELECT2_CSS = ""
SELECT2_I18N_PATH = 'assets/plugins/custom/select2-4.x/js/i18n'




#LOGGING CONF...
import logging.config
LOGGING_CONFIG = None
LOGGING_CONFIG_ = { 
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': { 
        'coloured': { 
            '()': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s %(asctime)s  %(levelname)-10s  from method: %(funcName)-32s  << %(message)s >>'
        },
    }, 
    'handlers': {
        'default': { 
            #'level': 'INFO',
            'formatter': 'coloured',
            'class': 'logging.StreamHandler', 
            'stream': 'ext://sys.stdout',  # Default is stderr
        },
    },
    'loggers': { 
        '': {  # root logger
            'handlers': ['default'],
            'level': 'WARNING',
            'propagate': False 
        },
        'django': { 
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        },
        '__main__': {  # if __name__ == '__main__'
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': False
        },                 
    } 
}
logging.config.dictConfig(LOGGING_CONFIG_)


#DATETIME INPUTS CONF...
DATETIME_INPUT_FORMATS = [
    '%d-%b-%Y %H:%M:%S',   #22-May-1998 13:01
   "%Y-%m-%d %H:%M:%S",   #1998-05-18 13:01:00
   "%d-%b-%Y %H:%M"
]
DATE_INPUT_FORMATS = [
    '%d-%b-%Y',
    '%d/%b/%Y',
    '%d/%m/%Y',
    "%Y-%m-%d",
    "%Y/%m/%d"
]

#DJANGO TAGGIT CONF...
TAGGIT_CASE_INSENSITIVE = True

