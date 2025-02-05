from django.db.models.signals import pre_save,post_save
from django.dispatch import receiver
from apps.work_order_management.models import Wom,WomDetails
from apps.work_order_management.serializers import WomSerializers,WomDetailsSerializers
from django.db.models import Q
import json

@receiver(pre_save, sender=Wom)
def set_serial_no(sender, instance, **kwargs):
    if instance.id is None:  # Ensure the object is new and doesn't already exist in the database
        print("Instance: ",instance, instance.identifier)
        if instance.description == 'THIS SECTION TO BE COMPLETED ON RETURN OF PERMIT':
            return
        if instance.identifier == 'SLA':
            # Query for SLA condition
            latest_record = sender.objects.filter(
                client=instance.client,
                bu=instance.bu,
                parent_id=1,
                identifier='SLA'
            ).order_by('-other_data__wp_seqno').first()
        elif instance.identifier == 'WP':
            # Query for the null identifier condition
            latest_record = sender.objects.filter(
                client=instance.client,
                bu=instance.bu,
                parent_id=1,  # Example: Adjust this if needed
                identifier='WP'
            ).order_by('-other_data__wp_seqno').first()
        else:
            latest_record = None  # Fallback for unexpected cases (optional)

        print("Latest Record: ", latest_record)
        if latest_record is None:
            # This is the first record for the client
            instance.other_data['wp_seqno'] = 1
        elif instance.other_data['wp_seqno'] != latest_record.other_data['wp_seqno']:
            instance.other_data['wp_seqno'] = latest_record.other_data['wp_seqno'] + 1

@receiver(post_save, sender=Wom)
def wom_post_save(sender,instance,created,**kwargs):
    print('I am here in signals')
    from paho_client import MqttClient,REDMINE_TO_NOC
    client = MqttClient()
    client.client.connect('localhost',1883,60)

    operation = 'CREATE' if created else 'UPDATE'
    serializer = WomSerializers(instance)
    data = {
        "operation":operation,
        "app": 'work_order_management',
        "models":"Wom",
        "payload": serializer.data
    }
    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()


@receiver(post_save, sender=WomDetails)
def wom_details_post_save(sender,instance,created,**kwargs):
    print('I am here in signals')
    from paho_client import MqttClient,REDMINE_TO_NOC
    client = MqttClient()
    client.client.connect('localhost',1883,60)

    operation = 'CREATE' if created else 'UPDATE'
    serializer = WomDetailsSerializers(instance)
    data = {
        "operation":operation,
        "app": 'work_order_management',
        "models":"WomDetails",
        "payload": serializer.data
    }
    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()