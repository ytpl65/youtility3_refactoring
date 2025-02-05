
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.activity.models import Job,Jobneed,JobneedDetails
from django.utils import timezone
from apps.schedhuler.serializers import JobSerializers,JobneedSerializers,JobneedDetailsSerializers
import json




@receiver(post_save,sender=Job)
def job_post_save(sender,instance,created,**kwargs):
    print('Job Signals')
    from paho_client import MqttClient, SG_TO_NOC_TOPIC
    client = MqttClient()
    client.client.connect('localhost',1883,60)

    operation = 'CREATE' if created else 'UPDATE'
    serializer = JobSerializers(instance)
    data = {
        "operation":operation,
        "app":"Activity",
        "models":"Job",
        "payload":serializer.data
    }
    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()

@receiver(post_save,sender=Jobneed)
def jobneed_post_save(sender,instance,created,**kwargs):
    print('Job Need Signals')
    from paho_client import MqttClient, REDMINE_TO_NOC
    client = MqttClient()
    client.client.connect('localhost',1883,60)
    
    operation = 'CREATE' if created else 'UPDATE'
    serializer = JobneedSerializers(instance)
    data = {
        "operation":operation,
        "app":"Activity",
        "models":"JobNeed",
        "payload":serializer.data
    }
    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()

@receiver(post_save,sender=JobneedDetails)
def jobneeddetails_post_save(sender,instance,created,**kwargs):
    print('Job need Details Signals')
    from paho_client import MqttClient, REDMINE_TO_NOC
    client = MqttClient()
    client.client.connect('localhost',1883,60)

    operation = 'CREATE' if created else 'UPDATE'
    serializer = JobneedDetailsSerializers(instance)
    data = {
        "operation":operation,
        "app":"Activity",
        "models":"JobneedDetails",
        "payload":serializer.data
    }
    payload = json.dumps(data)
    client.publish_message(REDMINE_TO_NOC,payload)
    client.client.disconnect()