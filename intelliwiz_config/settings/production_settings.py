from .base_settings import *

DEBUG = False
SECRET_SALT = str(os.getenv('SECRET_SALT'))
ENCRYPT_KEY = str(os.getenv('ENCRYPT_KEY'))
