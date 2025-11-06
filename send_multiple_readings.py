#!/usr/bin/env python3
"""
Send multiple varied sensor readings to populate the dashboard
"""

import paho.mqtt.client as mqtt
import json
import time
import random

MQTT_BROKER = "159.65.48.40"
MQTT_PORT = 1883
MQTT_TOPIC = "sensors/comprehensive"

# Different device scenarios
readings = [
    {
        "temperature": 23.5,
        "humidity": 62.1,
        "system_in_use": True,
        "oxygen_level": 96.2,
        "vibration_frequency": 28.5,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "what3words_location": "folder.clever.laptop",
        "oxygen_concentrator_id": "OXY-001",
        "value": 23.5
    },
    {
        "temperature": 24.8,
        "humidity": 58.3,
        "system_in_use": True,
        "oxygen_level": 94.7,
        "vibration_frequency": 31.2,
        "latitude": 51.5120,
        "longitude": -0.1340,
        "what3words_location": "daring.lion.grid",
        "oxygen_concentrator_id": "OXY-001",
        "value": 24.8
    },
    {
        "temperature": 26.1,
        "humidity": 65.8,
        "system_in_use": False,
        "oxygen_level": 93.5,
        "vibration_frequency": 15.3,
        "latitude": 51.5090,
        "longitude": -0.1300,
        "what3words_location": "pumps.widen.chef",
        "oxygen_concentrator_id": "OXY-001",
        "value": 26.1
    },
    {
        "temperature": 22.3,
        "humidity": 70.2,
        "system_in_use": True,
        "oxygen_level": 97.1,
        "vibration_frequency": 29.8,
        "latitude": 51.5100,
        "longitude": -0.1250,
        "what3words_location": "sleepy.doors.eggs",
        "oxygen_concentrator_id": "OXY-002",
        "value": 22.3
    },
    {
        "temperature": 25.7,
        "humidity": 61.5,
        "system_in_use": True,
        "oxygen_level": 95.8,
        "vibration_frequency": 32.1,
        "latitude": 51.5110,
        "longitude": -0.1290,
        "what3words_location": "folder.clever.laptop",
        "oxygen_concentrator_id": "OXY-002",
        "value": 25.7
    },
    {
        "temperature": 27.2,
        "humidity": 55.9,
        "system_in_use": False,
        "oxygen_level": 92.3,
        "vibration_frequency": 18.7,
        "latitude": 51.5080,
        "longitude": -0.1320,
        "what3words_location": "daring.lion.grid",
        "oxygen_concentrator_id": "OXY-003",
        "value": 27.2
    },
]

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER, MQTT_PORT, 60)

print(f"📤 Sending {len(readings)} sensor readings...")

for i, reading in enumerate(readings, 1):
    result = client.publish(MQTT_TOPIC, json.dumps(reading))
    result.wait_for_publish()

    status = "🟢 IN USE" if reading["system_in_use"] else "🔴 IDLE"
    print(f"{i}. {reading['oxygen_concentrator_id']}: {reading['temperature']}°C, O2: {reading['oxygen_level']}%, {status}")

    time.sleep(0.5)  # Small delay between messages

client.disconnect()

print("\n✅ All readings sent!")
print(f"👉 Check dashboard: http://{MQTT_BROKER}:5006")
