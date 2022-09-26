from .base_settings import *

DEBUG = False

ALLOWED_HOSTS +=['django-local.youtility.in', '127.0.0.1']

try:
    SECRET_KEY = os.environ["SECRET_KEY"]
except KeyError as e:
    raise RuntimeError("Could not find a SECRET_KEY in environment") from e

DATABASES = {
    'default': {
        'ENGINE':   'django.contrib.gis.db.backends.postgis',
        'USER':     config.get('PRODUCTION', 'DBUSER'),
        'NAME':     'icici_django',
        'PASSWORD': config.get('PRODUCTION', 'DBPASS'),
        'HOST':     config.get('PRODUCTION', 'DBHOST'),
        'PORT':     '5432',
    }
}

CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True

# security.W004
SECURE_HSTS_SECONDS = 31536000 # One year in seconds

# Another security settings
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Media Files CONF...
MEDIA_ROOT = os.path.join(os.path.expanduser('~'), 'youtility4_media')
MEDIA_URL = '/youtility4_media/'


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = '/var/www/intelliwiz/static/'
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'frontend/static')]

# Email Verification CONF...
def verified_callback(user):
    user.isverified = True

EMAIL_VERIFIED_CALLBACK = verified_callback
EMAIL_FROM_ADDRESS = config.get('PRODUCTION', 'EMAIL_FROM_ADDRESS')
EMAIL_MAIL_SUBJECT = 'Confirm your email'
EMAIL_MAIL_HTML = 'email.html'
EMAIL_MAIL_PLAIN = 'mail_body.txt'
EMAIL_TOKEN_LIFE = 60**2
EMAIL_PAGE_TEMPLATE = 'email_verify.html'
EMAIL_PAGE_DOMAIN = config.get('PRODUCTION', 'EMAIL_PAGE_DOMAIN')
EMAIL_MULTI_USER = True


# For Django Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = config.get('PRODUCTION', 'DEFAULT_FROM_EMAIL')
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = config.get('PRODUCTION', 'EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config.get('PRODUCTION', 'EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True
DJANGO_SETTINGS_MODULE = 'intelliwiz_config.settings.prod_settings'
