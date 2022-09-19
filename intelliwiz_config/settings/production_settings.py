from .base_settings import *

DEBUG = True
SECRET_SALT = str(os.getenv('SECRET_SALT'))
ENCRYPT_KEY = str(os.getenv('ENCRYPT_KEY'))
INSTALLED_APPS += ['django_extensions']

DATABASES = {
    'icici': {
        'ENGINE':   'django.contrib.gis.db.backends.postgis',
        'USER':     'navin',
        'NAME':     'icici_django',
        'PASSWORD': 'admin',
        'HOST':     'localhost',
        'PORT':     '5432',
    }
}

# GOOGLE MAP API KEY...
#GOOGLE_MAP_SECRET_KEY  = 'AIzaSyC3PUZCB7u2PiV8whHeAshweOPIK_d690o'#str(os.getenv('GOOGLE_MAP_SECRET_KEY'))


#For Django Email Backend
#EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#DEFAULT_FROM_EMAIL = "snvnrock@gmail.com"
#EMAIL_HOST = 'smtp.gmail.com'
#EMAIL_PORT = 587
#EMAIL_HOST_USER = 'mwaghtest@gmail.com'
#EMAIL_HOST_PASSWORD = 'mwaghtest@123' #str(os.getenv('EMAIL_HOST_PASSWORD'))
#EMAIL_USE_TLS = True
