from typing import Sequence
from django.db.models.signals import pre_save
from .models import Bt
from django.dispatch import receiver

@receiver(pre_save, sender=Bt)
def save_bupath_key(sender, instance, *args, **kwargs):
    if instance.parent in (None ,'NONE'):
        instance.bupath = instance.bucode
    else:
        print("parent bucode", instance.parent.bucode)
        parent = Bt.objects.values('parent').get(bucode=instance.parent.bucode)
        if instance.bupath != (parent['bupath'] + '>' + instance.bucode ):
            instance.bupath = ""
            instance.bupath += "%s > %s"%(parent['bupath'], instance.bucode)