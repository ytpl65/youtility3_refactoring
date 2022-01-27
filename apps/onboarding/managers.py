from django.db import models



class BtManager(models.Manager):
    use_in_migrations = True

    pass