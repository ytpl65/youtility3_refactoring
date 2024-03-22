from django.core.management.base import BaseCommand
from apps.mqtt.client import MqttClient

class Command(BaseCommand):
    help = 'Start the MQTT client'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting MQTT client...'))
        client = MqttClient()
        client.loop_forever()