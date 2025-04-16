from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.attendance.models import PeopleEventlog
from apps.attendance.serializers import PeopleEventlogSerializer
import json
from background_tasks.tasks import publish_mqtt
TOPIC="redmine_to_noc"


def build_payload(instance, model_name, created):
    serializer_cls = {
        "PeopleEventlog": PeopleEventlogSerializer
    }[model_name]
    serializer = serializer_cls(instance)
    return json.dumps({
        "operation": "CREATE" if created else "UPDATE",
        "app": "Attendance",
        "models": model_name,
        "payload": serializer.data
    })

@receiver(post_save, sender=PeopleEventlog)
def peopleeventlog_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "PeopleEventlog", created)
    publish_mqtt.delay(TOPIC, payload)

# @receiver(post_save,sender=PeopleEventlog)
# def peopleeventlog_post_save(sender,instance,created,**kwargs):
#     print('I am here in Attendance Signals')
#     from paho_client import MqttClient,REDMINE_TO_NOC
#     client = MqttClient()
#     client.client.connect('localhost',1883,60)

#     operation = 'CREATE' if created else 'UPDATE'
#     serializer = PeopleEventlogSerializer(instance)

#     data = {
#         'operation':operation,
#         'app':'attendance',
#         'models':"PeopleEventlog",
#         'payload':serializer.data
#     }

#     payload = json.dumps(data)
#     client.publish_message(REDMINE_TO_NOC,payload)
#     client.client.disconnect()


