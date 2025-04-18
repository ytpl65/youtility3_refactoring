from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.activity.models.asset_model import AssetLog,Asset
from apps.activity.models.attachment_model import Attachment
from apps.activity.models.location_model import Location
from apps.activity.models.question_model import Question,QuestionSet,QuestionSetBelonging
from .serializers import AttachmentSerializer,AssetSerializer,LocationSerializer,QuestionSerializer,QuestionSetSerializer,QuestionSetBelongingSerializer
from django.utils import timezone
import json

from background_tasks.tasks import publish_mqtt
TOPIC = "redmine_to_noc"

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

# @receiver(post_save,sender=Attachment)
# def create_attachment_record(sender,instance,created,**kwargs):
#     print('I am here in Attachment Record Creation')
#     from paho_client import MqttClient,REDMINE_TO_NOC
#     client = MqttClient()
#     client.client.connect('localhost',1883,60)

#     operation = 'CREATE' if created else 'UPDATE'
#     serializer = AttachmentSerializer(instance)

#     data = {
#         'operation':operation,
#         'app':'activity',
#         'models':'Attachment',
#         'payload':serializer.data
#     }

#     payload = json.dumps(data)
#     client.publish_message(REDMINE_TO_NOC,payload)
#     client.client.disconnect()

def build_payload(instance, model_name, created):
    serializer_cls = {
        "Attachment": AttachmentSerializer,
        "Asset": AssetSerializer,
        "Location": LocationSerializer,
        "Question": QuestionSerializer,
        "QuestionSet": QuestionSetSerializer,
        "QuestionSetBelonging": QuestionSetBelongingSerializer
    }[model_name]
    serializer = serializer_cls(instance)
    return json.dumps({
        "operation": "CREATE" if created else "UPDATE",
        "app": "Activity",
        "models": model_name,
        "payload": serializer.data
    })

@receiver(post_save,sender=Attachment)
def attachment_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "Attachment", created)
    publish_mqtt.delay(TOPIC, payload)


@receiver(post_save,sender=Asset)
def asset_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "Asset", created)
    publish_mqtt.delay(TOPIC, payload)

@receiver(post_save,sender=Location)
def location_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "Location", created)
    publish_mqtt.delay(TOPIC, payload)

@receiver(post_save,sender=Question)
def question_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "Question", created)
    publish_mqtt.delay(TOPIC, payload)

@receiver(post_save,sender=QuestionSet)
def questionset_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "QuestionSet", created)
    publish_mqtt.delay(TOPIC, payload)

@receiver(post_save,sender=QuestionSetBelonging)
def questionsetbelonging_post_save(sender,instance,created,**kwargs):
    payload = build_payload(instance, "QuestionSetBelonging", created)
    publish_mqtt.delay(TOPIC, payload)

    


