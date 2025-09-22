import asyncio
import json
import paho.mqtt.client as mqtt
import sqlalchemy
from sqlalchemy import Table, Column, Integer, Float, String, MetaData
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/sensordb")
MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "mosquitto")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

engine = sqlalchemy.create_engine(DATABASE_URL)
metadata = MetaData()

# Simple sensor table
sensors = Table(
    "sensors",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("topic", String),
    Column("value", Float),
)

# Create table if not exists
metadata.create_all(engine)

def on_connect(client, userdata, flags, rc):
    print("✅ Connected to MQTT broker with result code " + str(rc))
    client.subscribe("sensors/#")  # subscribe to all sensor topics

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    try:
        value = float(payload)
    except ValueError:
        print(f"⚠️ Could not parse payload: {payload}")
        return

    with engine.begin() as conn:
        conn.execute(sensors.insert().values(topic=msg.topic, value=value))
    print(f"📥 Saved message from {msg.topic}: {value}")

async def start_mqtt():
    loop = asyncio.get_event_loop()
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER_URL, MQTT_BROKER_PORT, 60)

    # Run loop in executor
    def run():
        client.loop_forever()

    await loop.run_in_executor(None, run)
