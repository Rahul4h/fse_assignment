import json
import time
import threading
import paho.mqtt.client as mqtt
from django.core.management.base import BaseCommand
from mqtt_integration.services import handle_challenge, set_mqtt_status
from mqtt_integration.latest_store import set_latest


CANDIDATE_ID = "17"
BROKER = "152.42.238.142"
PORT = 1883
CLIENT_ID = f"fse-01-{CANDIDATE_ID}-worker"


class Command(BaseCommand):
    help = 'Run MQTT worker to connect to factory broker'

    def handle(self, *args, **options):
        client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)

        def on_connect(client, userdata, flags, rc):
            self.stdout.write(f"Connected with result code {rc}")
            client.subscribe(f"fse-01/{CANDIDATE_ID}/challenge", qos=1)
            client.publish(f"fse-01/{CANDIDATE_ID}/status", "ONLINE", qos=1)
            set_mqtt_status('ONLINE')
            self.stdout.write(self.style.SUCCESS("Subscribed to challenge topic"))

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())
                challenge_id = payload.get('challenge_id')

                # Store latest challenge for the dashboard
                set_latest(challenge_id, payload, status="RECEIVED")

                self.stdout.write(f"Received: {challenge_id}")

                # Process it (writes to DB)
                response = handle_challenge(payload)

                # Update store with the response
                set_latest(challenge_id, payload, status=response.get('status', 'COMPLETED'))

                # Publish response back to broker
                client.publish(
                    f"fse-01/{CANDIDATE_ID}/response",
                    json.dumps(response),
                    qos=1
                )
                self.stdout.write(self.style.SUCCESS(f"Responded to {challenge_id}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

        def on_disconnect(client, userdata, rc):
            set_mqtt_status('OFFLINE')
            self.stdout.write(self.style.WARNING(f"Disconnected (rc={rc}). Reconnecting..."))
            time.sleep(5)
            try:
                client.reconnect()
            except Exception:
                pass

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        def heartbeat():
            while True:
                time.sleep(30)
                try:
                    client.publish(f"fse-01/{CANDIDATE_ID}/status", "HEARTBEAT", qos=1)
                    set_mqtt_status('ONLINE')
                except Exception:
                    pass

        threading.Thread(target=heartbeat, daemon=True).start()

        client.connect(BROKER, PORT, 60)
        self.stdout.write(self.style.SUCCESS(f"Connecting to {BROKER}:{PORT}..."))
        client.loop_forever()