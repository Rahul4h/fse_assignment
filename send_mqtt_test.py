"""
MQTT Factory Simulator
ফ্যাক্টরি মেশিনের মতো MQTT challenge পাঠায়।
"""
import paho.mqtt.client as mqtt
import json
import time
import sys

BROKER = "152.42.238.142"
PORT = 1883
CANDIDATE_ID = "17"

# Command line থেকে quantity নিন, default 5
quantity = int(sys.argv[1]) if len(sys.argv) > 1 else 5
event_num = int(time.time())

def on_connect(client, userdata, flags, rc):
    print(f"✅ Connected to broker (code {rc})")
    client.subscribe(f"fse-01/{CANDIDATE_ID}/response", qos=1)

def on_message(client, userdata, msg):
    print(f"\n📨 Response received from server!")
    print("=" * 60)
    try:
        data = json.loads(msg.payload.decode())
        print(json.dumps(data, indent=2))
    except:
        print(msg.payload.decode())
    print("=" * 60)
    client.disconnect()

# Challenge payload তৈরি
challenge = {
    "protocol_version": "1.0",
    "candidate_id": CANDIDATE_ID,
    "challenge_id": f"CH-TEST-{event_num}",
    "command": "PROCESS_EVENTS",
    "sent_at": "2026-10-09T18:00:00Z",
    "expires_at": "2026-10-09T18:05:00Z",
    "events": [
        {
            "source_id": "LINE-01",
            "event_id": f"EV-MQTT-{event_num}",
            "type": "COUNT",
            "quantity": quantity,
            "target_event_id": None,
            "event_time": "2026-10-09T18:00:00Z"
        }
    ]
}

# ব্রোকারে কানেক্ট
client = mqtt.Client(client_id=f"simulator-{CANDIDATE_ID}-{event_num}")
client.on_connect = on_connect
client.on_message = on_message

print(f"\n🔌 Connecting to {BROKER}:{PORT}...")
client.connect(BROKER, PORT, 60)
client.loop_start()

time.sleep(1)

# চ্যালেঞ্জ publish
print(f"\n📤 Publishing challenge: CH-TEST-{event_num}")
print(f"   Event: EV-MQTT-{event_num}")
print(f"   Quantity: {quantity}")
print(f"   Topic: fse-01/{CANDIDATE_ID}/challenge\n")

client.publish(
    f"fse-01/{CANDIDATE_ID}/challenge",
    json.dumps(challenge),
    qos=1
)

# Response-এর জন্য অপেক্ষা
time.sleep(8)

client.loop_stop()
client.disconnect()
print("\n✅ Done")