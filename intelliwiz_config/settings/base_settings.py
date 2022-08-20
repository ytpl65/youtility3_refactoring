# PYTHON STANDARD LIBRARY IMPORTS
from pathlib import Path
import os

# PYTHON EXTERNAL PACAGE LEVEL IMPORTS
from dotenv import load_dotenv
load_dotenv() 

# DJANGO LEVEL IMPORTS
# USER DJANGO APP LEVEL IMPORTS

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEBUG=True
SECRET_KEY = str(os.getenv('SECRET_KEY'))

ALLOWED_HOSTS = ['.localhost', '.youtility.local', 'barfi.youtility.in', '127.0.0.1', 'intelliwiz.youtility.in', '192.168.0.33']

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

DBUSER  = str(os.getenv('DBUSER'))

DBPASWD = str(os.getenv('DBPASWD'))

DBHOST  = str(os.getenv('DBHOST'))

DATABASES = {
    'default': {
        'ENGINE':   'django.contrib.gis.db.backends.postgis',
        'USER':     'navin',
        'NAME':     'intelliwiz_django',
        'PASSWORD': 'admin',
        'HOST':     'localhost',
        'PORT':     '5433',
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
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'frontend/static')]

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



