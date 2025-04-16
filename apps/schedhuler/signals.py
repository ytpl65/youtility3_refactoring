
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.activity.models.job_model import Job,Jobneed,JobneedDetails
from apps.schedhuler.serializers import JobSerializers,JobneedSerializers,JobneedDetailsSerializers
import json

from background_tasks.tasks import publish_mqtt

TOPIC = "redmine_to_noc"


def build_payload(instance, model_name, created):
    serializer_cls = {
        "Job": JobSerializers,
        "JobNeed": JobneedSerializers,
        "JobneedDetails": JobneedDetailsSerializers
    }[model_name]
    serializer = serializer_cls(instance)
    return json.dumps({
        "operation": "CREATE" if created else "UPDATE",
        "app": "Activity",
        "models": model_name,
        "payload": serializer.data
    })


@receiver(post_save, sender=Job)
def job_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "Job", created)
    publish_mqtt.delay(TOPIC, payload)


@receiver(post_save, sender=Jobneed)
def jobneed_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "JobNeed", created)
    publish_mqtt.delay(TOPIC, payload)


@receiver(post_save, sender=JobneedDetails)
def jobneeddetails_post_save(sender, instance, created, **kwargs):
    payload = build_payload(instance, "JobneedDetails", created)
    publish_mqtt.delay(TOPIC, payload)

# @receiver(post_save,sender=Job)
# def job_post_save(sender,instance,created,**kwargs):
#     print('Job Signals')
#     from paho_client import MqttClient, REDMINE_TO_NOC
#     client = MqttClient()
#     client.client.connect('localhost',1883,60)

#     operation = 'CREATE' if created else 'UPDATE'
#     serializer = JobSerializers(instance)
#     data = {
#         "operation":operation,
#         "app":"Activity",
#         "models":"Job",
#         "payload":serializer.data
#     }
#     payload = json.dumps(data)
#     client.publish_message(REDMINE_TO_NOC,payload)
#     client.client.disconnect()

# @receiver(post_save,sender=Jobneed)
# def jobneed_post_save(sender,instance,created,**kwargs):
#     print('Job Need Signals')
#     from paho_client import MqttClient, REDMINE_TO_NOC
#     client = MqttClient()
#     client.client.connect('sg.youtility.in',1883,60)
    
#     operation = 'CREATE' if created else 'UPDATE'
#     serializer = JobneedSerializers(instance)
#     data = {
#         "operation":operation,
#         "app":"Activity",
#         "models":"JobNeed",
#         "payload":serializer.data
#     }
#     payload = json.dumps(data)
#     client.publish_message(REDMINE_TO_NOC,payload)
#     client.client.disconnect()

# @receiver(post_save,sender=JobneedDetails)
# def jobneeddetails_post_save(sender,instance,created,**kwargs):
#     print('Job need Details Signals')
#     from paho_client import MqttClient, REDMINE_TO_NOC
#     client = MqttClient()
#     client.client.connect('sg.youtility.in',1883,60)

#     operation = 'CREATE' if created else 'UPDATE'
#     serializer = JobneedDetailsSerializers(instance)
#     data = {
#         "operation":operation,
#         "app":"Activity",
#         "models":"JobneedDetails",
#         "payload":serializer.data
#     }
#     payload = json.dumps(data)
#     client.publish_message(REDMINE_TO_NOC,payload)
#     client.client.disconnect()