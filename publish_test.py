import time
import random
import paho.mqtt.publish as publish

BROKER = "localhost"  # use Railway’s Mosquitto hostname when deployed
PORT = 1883

while True:
    value = round(random.uniform(20, 30), 2)
    publish.single("sensors/temperature", str(value), hostname=BROKER, port=PORT)
    print(f"📤 Sent: {value}")
    time.sleep(2)
