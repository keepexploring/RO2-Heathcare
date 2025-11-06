#!/usr/bin/env python3
"""
Test script to publish sensor data to the MQTT broker
Usage: python test_mqtt_publish.py
"""

import paho.mqtt.client as mqtt
import json
import sys

# Configuration
MQTT_BROKER = "159.65.48.40"
MQTT_PORT = 1883
MQTT_TOPIC = "sensors/comprehensive"  # Match publish_test.py topic

# Sample sensor data
message = {
    "temperature": 25.3,
    "humidity": 65.2,
    "system_in_use": True,
    "oxygen_level": 95.5,
    "vibration_frequency": 30.2,
    "latitude": 51.5074,
    "longitude": -0.1278,
    "what3words_location": "folder.clever.laptop",
    "oxygen_concentrator_id": "OXY-001",
    "value": 25.3  # Legacy compatibility field
}

def on_connect(client, userdata, flags, reason_code, properties):
    """Callback when connected to broker"""
    if reason_code == 0:
        print(f"✅ Connected to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"❌ Failed to connect, return code {reason_code}")

def on_publish(client, userdata, mid, reason_code, properties):
    """Callback when message is published"""
    print(f"✅ Message published to topic: {MQTT_TOPIC}")
    print(f"📊 Data sent: {json.dumps(message, indent=2)}")

try:
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    # Attach callbacks
    client.on_connect = on_connect
    client.on_publish = on_publish

    # Connect to broker
    print(f"🔌 Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Start network loop
    client.loop_start()

    # Publish message
    print(f"📤 Publishing sensor data...")
    result = client.publish(MQTT_TOPIC, json.dumps(message))

    # Wait for publish to complete
    result.wait_for_publish()

    # Stop loop and disconnect
    client.loop_stop()
    client.disconnect()

    print("\n🎉 Test completed successfully!")
    print(f"👉 Check your dashboard at: http://{MQTT_BROKER}:5006")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
