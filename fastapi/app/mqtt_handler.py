import asyncio
import os
import paho.mqtt.client as mqtt
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/sensordb")
MQTT_BROKER_URL = os.getenv("MQTT_BROKER_URL", "mosquitto")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", 1883))

# SQLAlchemy setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ORM model with timestamp
class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    value = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

# Create table if not exists
Base.metadata.create_all(bind=engine)

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print("✅ Connected to MQTT broker with result code " + str(rc))
    client.subscribe("sensors/#")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    try:
        value = float(payload)
    except ValueError:
        print(f"⚠️ Could not parse payload: {payload}")
        return

    # Save to DB
    db = SessionLocal()
    try:
        sensor = SensorData(topic=msg.topic, value=value)
        db.add(sensor)
        db.commit()
        print(f"📥 Saved message from {msg.topic}: {value}")
    except Exception as e:
        print(f"❌ DB error: {e}")
        db.rollback()
    finally:
        db.close()

# MQTT starter
async def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Retry connection with exponential backoff
    max_retries = 10
    retry_count = 0
    while retry_count < max_retries:
        try:
            print(f"🔄 Attempting MQTT connection to {MQTT_BROKER_URL}:{MQTT_BROKER_PORT} (attempt {retry_count + 1}/{max_retries})")
            client.connect(MQTT_BROKER_URL, MQTT_BROKER_PORT, 60)
            break
        except Exception as e:
            retry_count += 1
            wait_time = min(2 ** retry_count, 60)
            print(f"❌ MQTT connection failed: {e}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)

    if retry_count >= max_retries:
        print(f"💥 Failed to connect to MQTT broker after {max_retries} attempts")
        return

    client.loop_start()

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        client.loop_stop()
        client.disconnect()
        print("🔌 MQTT client disconnected")