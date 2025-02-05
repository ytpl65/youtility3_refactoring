from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Asset, AssetLog,Attachment
from .serializers import AttachmentSerializer
from django.utils import timezone
import json

@receiver(post_save, sender=Asset)
def create_asset_log(sender, instance, created, **kwargs):
    if not created:
        last_log = AssetLog.objects.filter(asset_id=instance.id).order_by('-cdtz').first()
        if last_log and last_log.newstatus != instance.runningstatus:
            AssetLog.objects.create(
                asset_id=instance.id,
                oldstatus=last_log.newstatus,
                newstatus=instance.runningstatus,
                cdtz=timezone.now(),
                bu_id=instance.bu_id,
                client_id=instance.client_id,
                ctzoffset=instance.ctzoffset,
                people_id=instance.muser_id
            )
        elif not last_log:
            AssetLog.objects.create(
                asset_id=instance.id,
                oldstatus=None,
                newstatus=instance.runningstatus,
                cdtz=timezone.now(),
                people_id=instance.muser_id,
                bu_id=instance.bu_id,
                client_id=instance.client_id,
                ctzoffset=instance.ctzoffset
            )

@receiver(post_save,sender=Attachment)
def create_attachment_record(sender,instance,created,**kwargs):
    print('I am here in Attachment Record Creation')
    from paho_client import MqttClient,REDMINE_TO_NOC
    client = MqttClient()
    client.client.connect('localhost',1883,60)

    operation = 'CREATE' if created else 'UPDATE'
    serializer = AttachmentSerializer(instance)

    data = {
        'operation':operation,
        'app':'activity',
        'models':'Attachment',
        'payload':serializer.data
    }

    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()
