from django.db import models
from django.db.models.functions import Concat, Cast
from django.db.models import CharField, Value as V
from django.db.models import Q, F, Count, Case, When
import logging
import json
logger = logging.getLogger('__main__')

class VendorManager(models.Manager):
    use_in_migrations = True
    
    def get_vendor_list(self, request, fields, related):
        R , S = request.GET, request.session
        if R.get('params'): P = json.loads(R.get('params', {}))
        
        qobjs =  self.select_related(*related).filter(
            bu_id = S['bu_id'],
            client_id = S['client_id'],
            enable=True
        ).values(*fields)
        return qobjs or self.none()