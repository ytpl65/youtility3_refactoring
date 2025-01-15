from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.attendance.models import PeopleEventlog
from apps.attendance.serializers import PeopleEventlogSerializer
import json


@receiver(post_save,sender=PeopleEventlog)
def peopleeventlog_post_save(sender,instance,created,**kwargs):
    print('I am here in Attendance Signals')
    from paho_client import MqttClient,SG_TO_NOC_TOPIC
    client = MqttClient()
    client.client.connect('localhost',1883,60)

    operation = 'CREATE' if created else 'UPDATE'
    serializer = PeopleEventlogSerializer(instance)

    data = {
        'operation':operation,
        'app':'attendance',
        'models':"PeopleEventlog",
        'payload':serializer.data
    }

    payload = json.dumps(data)
    client.publish_message(SG_TO_NOC_TOPIC,payload)
    client.client.disconnect()


