import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "intelliwiz_config.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django

django.setup()

from paho.mqtt import client as mqtt
from base64 import b64decode
from io import BytesIO
from paho.mqtt.enums import CallbackAPIVersion
import json
import logging
from pprint import pformat
log = logging.getLogger('message_q')
from django.conf import settings
from background_tasks.tasks import process_graphql_mutation_async, process_graphql_download_async
from celery.result import AsyncResult
MQTT_CONFIG = settings.MQTT_CONFIG 

# MQTT broker settings
BROKER_ADDRESS = MQTT_CONFIG['BROKER_ADDRESS']
BROKER_PORT = MQTT_CONFIG['BROKER_PORT']

MUTATION_TOPIC        = "graphql/mutation"
MUTATION_STATUS_TOPIC = "graphql/mutation/status"
GRAPHQL_DOWNLOAD      = "graphql/download"


RESPONSE_TOPIC        = "response"
RESPONSE_DOWNLOAD        = "response/download"
STATUS_TOPIC          = "response/status"

TESTMQ = "post"
TESTPUBMQ = "received"


def get_task_status(item):
    """
    Get status of a task
    """
    status = AsyncResult(item.get('taskId')).status
    item.update({'status':status})
    return item


class MqttClient:
    """
    MQTT client class
    """

    def __init__(self):
        """
        Initializes the MQTT client
        """
        self.client = mqtt.Client(CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
      

    # MQTT client callback functions
    def on_connect(self, client, userdata, flags, rc, props):
        if rc == 0:
            print("Connected to MQTT Broker!")
            client.subscribe(MUTATION_TOPIC)
            client.subscribe(MUTATION_STATUS_TOPIC)
            client.subscribe(TESTMQ)
            client.subscribe(GRAPHQL_DOWNLOAD)
        else:
            fail=f"Failed to connect, return code {rc}"
            print(fail)

    def on_message(self, client, userdata, msg):
        # Process the received message
        log.info(f"Received message: {msg.payload}")
        payload = msg.payload.decode()
        log.info("message: {} from MQTT broker on topic {} {}".format(msg.mid,msg.topic, "payload recieved" if payload else "payload not recieved"))
        log.info("processing started [+]")

        if msg.topic == GRAPHQL_DOWNLOAD:
            result = process_graphql_download_async(payload)
            post_data = json.loads(payload)
            service_name = post_data.get('serviceName')
            response = {'payload':result['data'], 'serviceName':service_name,
                        'tableName':post_data.get('tableName', ""), 'service':post_data.get('service')}
            response = json.dumps(response)
            log.info(f"Response published to {RESPONSE_DOWNLOAD} after accepting {service_name}")
            client.publish(RESPONSE_DOWNLOAD, response, qos=2)
        
        if msg.topic == MUTATION_TOPIC:
            # process graphql mutations received on this topicMUTATION_TOPIC
            result = process_graphql_mutation_async.delay(payload)
            post_data = json.loads(payload)
            print(f"{post_data.keys()}")
            uuids, service_name = post_data.get('uuids', []), post_data.get('serviceName', "")
            response = json.dumps(
                {'task_id':result.task_id, 'status':result.state,
                 'uuids':uuids, 'serviceName':service_name, 'payload':payload})
            log.info(f"Response published to {RESPONSE_TOPIC} after accepting {service_name}")
            client.publish(RESPONSE_TOPIC, response, qos=2)
        
        if msg.topic == MUTATION_STATUS_TOPIC:
            # enquire the status of tasks ids received on this topic
            payload = json.loads(payload)
            log.info(f"Received taskIds payload: {payload}")
            taskids = payload.get('taskIds', [])
            taskids_with_status = list(map(get_task_status, taskids))
            response = json.dumps(taskids_with_status)
            log.info(f"Response published to {STATUS_TOPIC}: {response}")
            client.publish(STATUS_TOPIC, response, qos=2)
        
        if msg.topic == TESTMQ:
            log.info(f"Received test message: {payload}")
            client.publish(TESTPUBMQ, f"Server Published a Response")
        log.info("processing completed [-]")



    def on_disconnect(self, client, userdata, disconnect_flags, rc, props):
        print("Disconnected from MQTT broker", userdata)

    def loop_forever(self):
        # Connect to MQTT broker
        self.client.connect(BROKER_ADDRESS, BROKER_PORT)
        self.client.loop_forever()


        

if __name__ == '__main__':
    client = MqttClient()
    client.loop_forever()