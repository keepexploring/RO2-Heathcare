import asyncio
import os
import paho.mqtt.client as mqtt
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean
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

# ORM model with comprehensive sensor data
class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)

    # Legacy field for backward compatibility
    value = Column(Float)

    # Comprehensive sensor data fields
    temperature = Column(Float)
    humidity = Column(Float)
    system_in_use = Column(Boolean, default=False)
    oxygen_level = Column(Float)
    vibration_frequency = Column(Float)

    # Location data
    latitude = Column(Float)
    longitude = Column(Float)
    what3words_location = Column(String)

    # Device identification
    oxygen_concentrator_id = Column(String, index=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

# Create table if not exists
Base.metadata.create_all(bind=engine)

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print("✅ Connected to MQTT broker with result code " + str(rc))
    client.subscribe("sensors/#")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()

    # Try to parse as JSON first, fall back to legacy format
    try:
        import json
        data = json.loads(payload)

        # Extract comprehensive sensor data
        temperature = data.get("temperature")
        humidity = data.get("humidity")
        system_in_use = data.get("system_in_use", False)
        oxygen_level = data.get("oxygen_level")
        vibration_frequency = data.get("vibration_frequency")
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        what3words_location = data.get("what3words_location")
        oxygen_concentrator_id = data.get("oxygen_concentrator_id", "UNKNOWN")

        # Legacy support - use temperature or value field
        legacy_value = data.get("value", temperature)

    except (json.JSONDecodeError, KeyError):
        try:
            # Legacy format - single float value
            legacy_value = float(payload)
            temperature = legacy_value  # Assume it's temperature
            humidity = None
            system_in_use = False
            oxygen_level = None
            vibration_frequency = None
            latitude = None
            longitude = None
            what3words_location = None
            oxygen_concentrator_id = "LEGACY"
        except ValueError:
            print(f"⚠️ Could not parse payload: {payload}")
            return

    # Save to DB
    db = SessionLocal()
    try:
        sensor = SensorData(
            topic=msg.topic,
            value=legacy_value,  # Keep for backward compatibility
            temperature=temperature,
            humidity=humidity,
            system_in_use=system_in_use,
            oxygen_level=oxygen_level,
            vibration_frequency=vibration_frequency,
            latitude=latitude,
            longitude=longitude,
            what3words_location=what3words_location,
            oxygen_concentrator_id=oxygen_concentrator_id
        )
        db.add(sensor)
        db.commit()

        # Enhanced logging
        fields = []
        if temperature is not None: fields.append(f"temp: {temperature}°C")
        if humidity is not None: fields.append(f"humidity: {humidity}%")
        if system_in_use: fields.append("IN USE")
        if oxygen_level is not None: fields.append(f"O2: {oxygen_level}%")

        field_str = ", ".join(fields) if fields else f"value: {legacy_value}"
        print(f"📥 Saved from {msg.topic}: {field_str} (ID: {oxygen_concentrator_id})")

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