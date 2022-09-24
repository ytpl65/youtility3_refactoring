# PYTHON STANDARD LIBRARY IMPORTS
from pathlib import Path
import os
from icecream import ic
import configparser
import mimetypes
mimetypes.add_type("text/css", ".css", True)

config = configparser.RawConfigParser()
config.sections()
CONFIGPATH = os.path.join(os.path.abspath('intelliwiz_config/settings/config.ini'))
config.read(CONFIGPATH)



# DJANGO LEVEL IMPORTS
# USER DJANGO APP LEVEL IMPORTS

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ic(BASE_DIR)
DEBUG=True
SECRET_KEY = config.get('DEFAULT', 'SECRET_KEY')

ALLOWED_HOSTS = ['.localhost', '.youtility.local', 'barfi.youtility.in', '127.0.0.1', 'intelliwiz.youtility.in', '192.168.1.33', '192.168.1.254']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',

    # third_party_apps
    'graphene_django',
    'graphene_gis',
    'django_email_verification',
    'debug_toolbar',
    'import_export',
    "django_select2",
    "graphql_jwt.refresh_token.apps.RefreshTokenConfig",
    'rest_framework',




    # local apps
    'apps.peoples',
    'apps.onboarding',
    'apps.tenants',
    'apps.attendance',
    'apps.activity',
    'apps.schedhuler',
    'apps.reports',
    'apps.service',

    'django_cleanup.apps.CleanupConfig',
]

MIDDLEWARE = [
    'apps.tenants.middlewares.TenantMiddleware', # custom middleware
    'django.middleware.security.SecurityMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'intelliwiz_config.urls'
import jinja2
JINJA_TEMPLATES = os.path.join(BASE_DIR, 'frontend/templates')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

            ],

        },
    },
    # jinja2 configuration
    { 
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [JINJA_TEMPLATES],
        'APP_DIRS': True,
        'OPTIONS':{
            'extensions': ['jinja2.ext.loopcontrols',],
            'autoescape' : False,
            'auto_reload': True,
            'undefined'  : jinja2.StrictUndefined,
            'environment': 'intelliwiz_config.jinja.env.JinjaEnvironment'
        },
    },
]

WSGI_APPLICATION = 'intelliwiz_config.wsgi.application'

DBUSER  = config.get('DEVELOPMENT', 'DBUSER')
DBPASS = config.get('DEVELOPMENT', 'DBPASS')
DBNAME = config.get('DEVELOPMENT', 'DBNAME')


DBHOST  = config.get('DEVELOPMENT', 'DBHOST')
  
DATABASES = {
    'icici': {
        'ENGINE':   'django.contrib.gis.db.backends.postgis',
        'USER':     DBUSER,
        'NAME':     DBNAME,
        'PASSWORD': DBPASS,
        'HOST':     DBHOST,
        'PORT':     '5432',
    },
}   
DATABASE_ROUTERS = ['apps.tenants.middlewares.TenantDbRouter']

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
       "KEY_PREFIX": "youtility4"
    },
    "select2": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
       "KEY_PREFIX": "select2"
    }
}

# PASSWORD VALIDATORS...
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]



# SESSION CONF....
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

SESSION_COOKIE_SECURE = False

SESSION_EXPIRE_AT_BROWSER_CLOSE = False # close the session when user closes the browser

SESSION_COOKIE_AGE = 60**2

SESSION_SAVE_EVERY_REQUEST = True

# AUTHENTICATIN BACKENDS CONF...
AUTHENTICATION_BACKENDS = [
    "graphql_jwt.backends.JSONWebTokenBackend",
    'apps.peoples.backends.MultiAuthentcationBackend',
    'django.contrib.auth.backends.ModelBackend'
    ]

# USER MODEL
AUTH_USER_MODEL = 'peoples.People'


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/# default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATABASE_ROUTERS = ['apps.tenants.middlewares.TenantDbRouter']



# Media Files CONF...
MEDIA_ROOT = os.path.join(os.path.expanduser('~'), 'youtility4_media')
MEDIA_URL = '/youtility4_media/'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, "frontend/static/static_server")
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'frontend/static')]

ic(STATICFILES_DIRS)

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_L10N = False

USE_TZ = True

# Cache time to live is 15 minutes.
CACHE_TTL = 60 * 5

# LOGIN URL NAME...
LOGIN_URL = 'login'


# LOGGING CONF...
import logging.config
LOGGING_CONFIG = None

def get_logpath():
    logname = f'youtility_logs/{DBNAME}.log'
    logpath = o.path.join(os.path.expanduser('~'), logname)
    if not os.path.exists(logpath):
        open(logpath)
    return logpath

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
        'youtility3':{
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            #'filename': 'youtility2_logs/youtility.log',
            'filename': os.path.join(os.path.expanduser('~'), 'youtility3_logs/youtility.log'),
            'maxBytes': 1024 * 1024 * 10, # 10 MB
            'backupCount': 7,
            'formatter':'coloured',
        },
    },
    'loggers': { 
        '': {  # root logger
            'handlers': ['default', 'youtility3'],
            'level': 'INFO',
            'propagate': True 
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

# DATETIME INPUTS CONF...
DATETIME_INPUT_FORMATS = [
   '%d-%b-%Y %H:%M:%S',   # 22-May-1998 13:01
   "%Y-%m-%d %H:%M:%S",   # 1998-05-18 13:01:00
   "%d-%b-%Y %H:%M"
]
DATE_INPUT_FORMATS = [
    '%d-%b-%Y',
    '%d/%b/%Y',
    '%d/%m/%Y',
    "%Y-%m-%d",
    "%Y/%m/%d"
]

# GOOGLE MAP API KEY...
GOOGLE_MAP_SECRET_KEY  = 'AIzaSyC3PUZCB7u2PiV8whHeAshweOPIK_d690o' #str(os.getenv('GOOGLE_MAP_SECRET_KEY'))

# CELERY CONF...
CELERY_BROKER_URL = config.get('DEFAULT', 'CELERY_BROKER_URL')
CELERY_CACHE_BACKEND = config.get('DEFAULT', 'CELERY_CACHE_BACKEND')
CELERY_RESULT_BACKEND = config.get('DEFAULT', 'CELERY_RESULT_BACKEND')

# SELECT2 CONF...
SELECT2_CACHE_BACKEND = 'select2'
SELECT2_JS = ""
SELECT2_CSS = ""
SELECT2_I18N_PATH = 'assets/plugins/custom/select2-4.x/js/i18n'


# DJANGO TAGGIT CONF...
TAGGIT_CASE_INSENSITIVE = True

# GRAPHQL JWT CONF...
from datetime import timedelta
GRAPHQL_JWT = {
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_EXPIRATION_DELTA": timedelta(minutes = 7*24*60),
    "JWT_REFRESH_EXPIRATION_DELTA": timedelta(days = 7),
    # optional
    "JWT_LONG_RUNNING_REFRESH_TOKEN": True,
}


# GRAPHENE CONF...
GRAPHENE = {
    "ATOMIC_MUTATIONS": True,
    "SCHEMA": "apps.service.schema.schema",
    'MIDDLEWARE': [
        'graphene_django.debug.DjangoDebugMiddleware',
        "graphql_jwt.middleware.JSONWebTokenMiddleware",
    ]
}

# Email Verification CONF...
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
EMAIL_MULTI_USER = True


# For Django Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = "snvnrock@gmail.com"
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'mwaghtest@gmail.com'
EMAIL_HOST_PASSWORD = 'mwaghtest@123' #str(os.getenv('EMAIL_HOST_PASSWORD'))
EMAIL_USE_TLS = True

# DJANGO_IMPORT_EXPORT CONF...
IMPORT_EXPORT_USE_TRANSACTIONS = True

# DJANGO-EXTENSIONS CONF...
SHELL_PLUS_PRINT_SQL = True
GRAPH_MODELS = {
  'all_applications': True,
  'group_models': True,
}

