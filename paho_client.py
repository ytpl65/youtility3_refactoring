import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "intelliwiz_config.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import django

django.setup()
from paho.mqtt import client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from django.conf import settings
from background_tasks.tasks import (
    process_graphql_mutation_async,
    process_graphql_download_async,
)
from celery.result import AsyncResult
import json
import logging
from base64 import b64decode
from zlib import decompress

MQTT_CONFIG = settings.MQTT_CONFIG
log = logging.getLogger("message_q")

# MQTT broker settings
BROKER_ADDRESS = MQTT_CONFIG["BROKER_ADDRESS"]
BROKER_PORT = MQTT_CONFIG["BROKER_PORT"]

GRAPHQL_MUTATION = "graphql/mutation"
GRAPHQL_ATTACHMENT = "graphql/attachment"
MUTATION_STATUS = "graphql/mutation/status"
GRAPHQL_DOWNLOAD = "graphql/download"


RESPONSE_TOPIC = "response"
RESPONSE_DOWNLOAD = "response/download"
STATUS_TOPIC = "response/status"

TESTMQ = "post"
TESTPUBMQ = "received"


def get_task_status(item):
    """
    Get status of a task
    """
    status = AsyncResult(item.get("taskId")).status
    item.update({"status": status})
    return item


def unzip_string(encoded_input):
    # Decode the base64 encoded string to get compressed bytes
    compressed_bytes = b64decode(encoded_input)

    # Decompress the bytes using zlib
    bytes = decompress(compressed_bytes)

    # Convert the bytes back to a UTF-8 string
    return bytes.decode("utf-8")


class MqttClient:
    """
    MQTT client class listens for connection, messages,
    dis-connection
    """

    def __init__(self):
        """
        Initializes the MQTT client
        """
        self.client = mqtt.Client(CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        """
        Initializes the MQTT client and sets up the callback functions
        for connect, message, and disconnect events.
        """

    # MQTT client callback functions
    def on_connect(self, client, userdata, flags, rc, props):
        if rc == 0:
            print("Connected to MQTT Broker!")
            client.subscribe(GRAPHQL_MUTATION, qos=1)
            client.subscribe(MUTATION_STATUS, qos=1)
            client.subscribe(TESTMQ)
            client.subscribe(GRAPHQL_DOWNLOAD, qos=1)
            client.subscribe(GRAPHQL_ATTACHMENT, qos=1)
        else:
            fail = f"Failed to connect, return code {rc}"
            print(fail)

    def on_message(self, client, userdata, msg):
        try:
            log.info(
                "message: {} from MQTT broker on topic {} {}".format(
                    msg.mid,
                    msg.topic,
                    "payload recieved" if msg.payload else "payload not recieved",
                )
            )
            log.info("processing started [+]")

            if msg.topic == GRAPHQL_DOWNLOAD:
                payload = msg.payload.decode()
                log.info(f"\n\nReceived message: {payload}")
                result = process_graphql_download_async(payload)
                post_data = json.loads(payload)
                service_name = post_data.get("serviceName")
                records = result["data"][service_name]["records"]
                if not records:
                    double_decoded_records = []
                else:
                    decoded_records = json.loads(records)
                    double_decoded_records = json.loads(decoded_records)
                log.info(f"Decoded records type: {type(double_decoded_records)}")
                response = {
                    "payload": double_decoded_records,
                    "serviceName": service_name,
                    "tableName": post_data.get("tableName", ""),
                    "service": post_data.get("service"),
                }
                response = json.dumps(response)
                log.info(
                    f"Response published to {RESPONSE_DOWNLOAD} after accepting {service_name}"
                )
                client.publish(RESPONSE_DOWNLOAD, response, qos=1)

            if msg.topic == GRAPHQL_MUTATION:

                # Process the received message
                payload = msg.payload.decode("utf-8")
                original_message = unzip_string(payload)

                # process graphql mutations received on this topic GRAPHQL_MUTATION
                result = process_graphql_mutation_async.delay(original_message)
                post_data = json.loads(original_message)
                uuids, service_name = post_data.get("uuids", []), post_data.get(
                    "serviceName", ""
                )
                response = json.dumps(
                    {
                        "task_id": result.task_id,
                        "status": result.state,
                        "uuids": uuids,
                        "serviceName": service_name,
                        "payload": payload,
                    }
                )
                log.info(
                    f"Response published to {RESPONSE_TOPIC} after accepting {service_name}"
                )
                client.publish(RESPONSE_TOPIC, response, qos=2)

            if msg.topic == MUTATION_STATUS:
                payload = msg.payload.decode()
                # enquire the status of tasks ids received on this topic
                payload = json.loads(payload)
                log.info(f"Received taskIds payload: {payload}")
                taskids = payload.get("taskIds", [])
                taskids_with_status = list(map(get_task_status, taskids))
                response = json.dumps(taskids_with_status)
                log.info(f"Response published to {STATUS_TOPIC}: {response}")
                client.publish(STATUS_TOPIC, response, qos=2)
            
            if msg.topic == GRAPHQL_ATTACHMENT:
                payload = msg.payload.decode("utf-8")
                original_message = unzip_string(payload)
                result = process_graphql_mutation_async.delay(original_message)
                post_data = json.loads(original_message)
                uuids, service_name = post_data.get("uuids", []), post_data.get(
                    "serviceName", ""
                )
                response = json.dumps(
                    {
                        "task_id": result.task_id,
                        "status": result.state,
                        "uuids": uuids,
                        "serviceName": service_name,
                        "payload": payload,
                    }
                )
                client.publish(RESPONSE_TOPIC, response, qos=2)
            if msg.topic == TESTMQ:
                log.info(f"Received test message: {payload}")
                client.publish(TESTPUBMQ, f"Server Published a Response")
            log.info("processing completed [-]")
        except Exception as e:
            log.error(f"Error processing message: {e}", exc_info=True)
            raise e

    def on_disconnect(self, client, userdata, disconnect_flags, rc, props):
        print("Disconnected from MQTT broker", userdata)

    def loop_forever(self):
        # Connect to MQTT broker
        self.client.connect(BROKER_ADDRESS, BROKER_PORT)
        self.client.loop_forever()


if __name__ == "__main__":
    client = MqttClient()
    client.loop_forever()
