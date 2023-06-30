from django.db.models.signals import pre_save
from django.dispatch import receiver
from apps.work_order_management.models import Wom

@receiver(pre_save, sender=Wom)
def set_serial_no(sender, instance, **kwargs):
    if instance.id is None:  # if seqno is not set yet
        #ic(instance.other_data)
        latest_record = sender.objects.filter(client=instance.client, bu = instance.bu).order_by('-other_data__wp_seqno').first()
        #ic(latest_record.id)
        if latest_record is None:
            # This is the first record for the client
            instance.other_data['wp_seqno'] = 1
        else:
            instance.other_data['wp_seqno'] = latest_record.other_data['wp_seqno'] + 1  