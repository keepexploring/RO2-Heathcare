import time
import random
import json
import paho.mqtt.publish as publish

BROKER = "localhost"  # use Railway's Mosquitto hostname when deployed
PORT = 1883
CONCENTRATOR_ID = "OXY-001"  # Default oxygen concentrator ID

# Example what3words locations for realistic data
WHAT3WORDS_LOCATIONS = [
    "folder.clever.laptop",
    "daring.lion.grid",
    "pumps.widen.chef",
    "sleepy.doors.eggs"
]

while True:
    # Generate realistic sensor data
    temperature = round(random.uniform(18, 32), 2)  # Temperature in Celsius
    humidity = round(random.uniform(30, 80), 1)     # Humidity percentage
    system_in_use = random.choice([True, False])    # Boolean for usage
    oxygen_level = round(random.uniform(85, 99), 1) # Oxygen percentage
    vibration_frequency = round(random.uniform(10, 60), 2)  # Hz

    # GPS coordinates (example: London area)
    latitude = round(random.uniform(51.4, 51.6), 6)
    longitude = round(random.uniform(-0.3, 0.1), 6)
    what3words_location = random.choice(WHAT3WORDS_LOCATIONS)

    # Comprehensive sensor data
    data = {
        "temperature": temperature,
        "humidity": humidity,
        "system_in_use": system_in_use,
        "oxygen_level": oxygen_level,
        "vibration_frequency": vibration_frequency,
        "latitude": latitude,
        "longitude": longitude,
        "what3words_location": what3words_location,
        "oxygen_concentrator_id": CONCENTRATOR_ID,
        "value": temperature  # Legacy compatibility
    }

    publish.single("sensors/comprehensive", json.dumps(data), hostname=BROKER, port=PORT)

    # Create status string
    status = "🟢 IN USE" if system_in_use else "🔴 IDLE"
    print(f"📤 Sent: {temperature}°C, {humidity}%, O2: {oxygen_level}%, {status} from {CONCENTRATOR_ID}")

    time.sleep(2)
