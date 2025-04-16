from django.db.models.signals import post_save
from apps.onboarding.models import Bt,TypeAssist,Shift,GeofenceMaster
from apps.onboarding.serializers import GeofenceMasterSerializers,BtSerializers,ShiftSerializers,TypeAssistSerializers
from django.dispatch import receiver
import json

from background_tasks.tasks import publish_mqtt
TOPIC = "redmine_to_noc"


def build_payload(instance, model_name, created):
    serializer_cls = {
        "Bt": BtSerializers,
        "TypeAssist": TypeAssistSerializers,
        "Shift": ShiftSerializers,
        "GeofenceMaster": GeofenceMasterSerializers
    }[model_name]
    serializer = serializer_cls(instance)
    return json.dumps({
        "operation": "CREATE" if created else "UPDATE",
        "app": "onboarding",
        "models": model_name,
        "payload": serializer.data
    })

@receiver(post_save, sender=Bt)
def bt_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "Bt", created)
    publish_mqtt.delay(TOPIC, payload)


@receiver(post_save, sender=TypeAssist)
def typeassist_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "TypeAssist", created)
    publish_mqtt.delay(TOPIC, payload)


@receiver(post_save, sender=Shift)
def shift_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "Shift", created)
    publish_mqtt.delay(TOPIC, payload)


@receiver(post_save, sender=GeofenceMaster)
def geofencemaster_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "GeofenceMaster", created)
    publish_mqtt.delay(TOPIC, payload)


# @receiver(post_save,sender=Bt)
# def bt_post_save(sender,instance,created,**kwargs):
#     print("In BT Signals")
#     from paho_client import MqttClient,REDMINE_TO_NOC
#     client = MqttClient()
#     client.client.connect('localhost',1883,60)
#     operation = 'CREATE' if created else 'UPDATE'
#     serializer = BtSerializers(instance)
#     data = {
#         "operation":operation,
#         "app": 'onboarding',
#         "models":"Bt",
#         "payload": serializer.data
#     }
#     payload = json.dumps(data)
#     client.publish_message(REDMINE_TO_NOC,payload)
#     client.client.disconnect()

# @receiver(post_save,sender=TypeAssist)
# def typeassist_post_save(sender,instance,created,**kwargs):
#     print("In TypeAssist Signals")
#     from paho_client import MqttClient,REDMINE_TO_NOC
#     client = MqttClient()
#     client.client.connect('localhost',1883,60)
#     operation = 'CREATE' if created else 'UPDATE'
#     serializer = TypeAssistSerializers(instance)
#     data = {
#         "operation":operation,
#         "app": 'onboarding',
#         "models":"TypeAssist",
#         "payload": serializer.data
#     }
#     payload = json.dumps(data)
#     client.publish_message(REDMINE_TO_NOC,payload)
#     client.client.disconnect()

# @receiver(post_save,sender=Shift)
# def shift_post_save(sender,instance,created,**kwargs):
#     print("In Shift Signals")
#     from paho_client import MqttClient,REDMINE_TO_NOC
#     client = MqttClient()
#     client.client.connect('localhost',1883,60)
#     operation = 'CREATE' if created else 'UPDATE'
#     serializer = ShiftSerializers(instance)
#     data = {
#         "operation":operation,
#         "app": 'onboarding',
#         "models":"Shift",
#         "payload": serializer.data
#     }
#     payload = json.dumps(data)
#     client.publish_message(REDMINE_TO_NOC,payload)
#     client.client.disconnect()

# @receiver(post_save,sender=GeofenceMaster)
# def geofencemaster_post_save(sender,instance,created,**kwargs):
#     print("In GeofenceMaster Signals")
#     from paho_client import MqttClient,REDMINE_TO_NOC
#     client = MqttClient()
#     client.client.connect('localhost',1883,60)
#     operation = 'CREATE' if created else 'UPDATE'
#     serializer = GeofenceMasterSerializers(instance)
#     data = {
#         "operation":operation,
#         "app": 'onboarding',
#         "models":"GeofenceMaster",
#         "payload": serializer.data
#     }
#     payload = json.dumps(data)
#     client.publish_message(REDMINE_TO_NOC,payload)
#     client.client.disconnect()