from paho.mqtt import client as mqtt
from base64 import b64decode
from io import BytesIO
from paho.mqtt.enums import CallbackAPIVersion
import json
import logging
from pprint import pformat
log = logging.getLogger('mobile_service_log')
from django.conf import settings
from background_tasks.tasks import process_graphql_mutation_async
MQTT_CONFIG = settings.MQTT_CONFIG 

# MQTT broker settings
BROKER_ADDRESS = MQTT_CONFIG['BROKER_ADDRESS']
BROKER_PORT = MQTT_CONFIG['BROKER_PORT']

MUTATION_TOPIC = "graphql/mutation"
RESPONSE_TOPIC = "response/acknowledgement"
RESULT_TOPIC   = "response/result"


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
        else:
            fail=f"Failed to connect, return code {rc}"
            print(fail)

    def on_message(self, client, userdata, msg):
        # Process the received task
        payload = msg.payload.decode()
        log.info("message: {} from MQTT broker on topic{} {}".format(msg.mid,msg.topic, "payload recieved" if payload else "payload not recieved"))
        log.info("processing started [+]")
        if msg.topic == MUTATION_TOPIC:
            log.info(f"Decoded Paylod:\n{pformat(json.loads(payload))}")
            result = process_graphql_mutation_async.delay(payload)
            response = json.dumps({'task_id':result.task_id, 'status':result.state.lower()})
            log.info(f"Response published to {RESPONSE_TOPIC}: {response}")
            log.info("processing completed [-]")
            client.publish(RESPONSE_TOPIC, response) # Publish the response


    def on_disconnect(self, client, userdata, disconnect_flags, rc, props):
        print("Disconnected from MQTT broker", userdata)

    def loop_forever(self):
        # Connect to MQTT broker
        self.client.connect(BROKER_ADDRESS, BROKER_PORT)
        self.client.loop_forever()


        



