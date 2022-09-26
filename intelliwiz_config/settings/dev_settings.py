from .base_settings import *
DEBUG=True

ALLOWED_HOSTS = ['localhost', '.youtility.local', '192.168.1.33', '192.168.1.254', 'django-local.youtility.in', '127.0.0.1']


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    }
]

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "frontend/static/static_server")
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'frontend/static')]

DATABASES = {
        'default':{
            'ENGINE':   'django.contrib.gis.db.backends.postgis',
            'USER':     'youtilitydba',
            'NAME':     'icici_django',
            'PASSWORD': '!!sysadmin!!',
            'HOST':     'localhost',
            'PORT':     '5432',
        }
}

# Email Verification CONF...
def verified_callback(user):
    user.isverified = True

EMAIL_VERIFIED_CALLBACK = verified_callback
EMAIL_FROM_ADDRESS =  config.get('DEVELOPMENT', 'EMAIL_FROM_ADDRESS')
EMAIL_MAIL_SUBJECT = 'Confirm your email'
EMAIL_MAIL_HTML = 'email.html'
EMAIL_MAIL_PLAIN = 'mail_body.txt'
EMAIL_TOKEN_LIFE = 60**2
EMAIL_PAGE_TEMPLATE = 'email_verify.html'
EMAIL_PAGE_DOMAIN =  config.get('DEVELOPMENT', 'EMAIL_PAGE_DOMAIN')
EMAIL_MULTI_USER = True


# For Django Email Backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL =  config.get('DEVELOPMENT', 'DEFAULT_FROM_EMAIL')
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER =  config.get('DEVELOPMENT', 'EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD =  config.get('DEVELOPMENT', 'EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = True