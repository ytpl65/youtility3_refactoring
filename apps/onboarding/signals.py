from django.db.models.signals import post_save,pre_save
from apps.onboarding.models import Bt,TypeAssist,Shift,GeofenceMaster
from apps.onboarding.serializers import GeofenceMasterSerializers,BtSerializers,ShiftSerializers,TypeAssistSerializers
from django.dispatch import receiver
import json

@receiver(post_save,sender=Bt)
def bt_post_save(sender,instance,created,**kwargs):
    print("In BT Signals")
    from paho_client import MqttClient,REDMINE_TO_NOC
    client = MqttClient()
    client.client.connect('localhost',1883,60)
    operation = 'CREATE' if created else 'UPDATE'
    serializer = BtSerializers(instance)
    data = {
        "operation":operation,
        "app": 'onboarding',
        "models":"Bt",
        "payload": serializer.data
    }
    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()

@receiver(post_save,sender=TypeAssist)
def typeassist_post_save(sender,instance,created,**kwargs):
    print("In TypeAssist Signals")
    from paho_client import MqttClient,REDMINE_TO_NOC
    client = MqttClient()
    client.client.connect('localhost',1883,60)
    operation = 'CREATE' if created else 'UPDATE'
    serializer = TypeAssistSerializers(instance)
    data = {
        "operation":operation,
        "app": 'onboarding',
        "models":"TypeAssist",
        "payload": serializer.data
    }
    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()

@receiver(post_save,sender=Shift)
def shift_post_save(sender,instance,created,**kwargs):
    print("In Shift Signals")
    from paho_client import MqttClient,REDMINE_TO_NOC
    client = MqttClient()
    client.client.connect('localhost',1883,60)
    operation = 'CREATE' if created else 'UPDATE'
    serializer = ShiftSerializers(instance)
    data = {
        "operation":operation,
        "app": 'onboarding',
        "models":"Shift",
        "payload": serializer.data
    }
    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()

@receiver(post_save,sender=GeofenceMaster)
def geofencemaster_post_save(sender,instance,created,**kwargs):
    print("In GeofenceMaster Signals")
    from paho_client import MqttClient,REDMINE_TO_NOC
    client = MqttClient()
    client.client.connect('localhost',1883,60)
    operation = 'CREATE' if created else 'UPDATE'
    serializer = GeofenceMasterSerializers(instance)
    data = {
        "operation":operation,
        "app": 'onboarding',
        "models":"GeofenceMaster",
        "payload": serializer.data
    }
    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()