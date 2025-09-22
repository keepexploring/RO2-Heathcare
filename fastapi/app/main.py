from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import asyncio
from models import SensorData
from db import Base, engine, SessionLocal
from mqtt_handler import start_mqtt

app = FastAPI(title="Sensor Backend")

# Create tables automatically
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Startup: start MQTT subscriber
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_mqtt())

# Health endpoints
@app.get("/ping")
def ping():
    return {"msg": "pong"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Data endpoint for Panel
@app.get("/data")
def get_sensor_data(limit: int = 100, db: Session = Depends(get_db)):
    """
    Returns the latest `limit` sensor readings, ordered by newest first.
    Each reading includes: id, topic, value, timestamp.
    """
    readings = (
        db.query(SensorData)
        .order_by(SensorData.id.desc())
        .limit(limit)
        .all()
    )
    # Convert ORM objects to dicts
    return [
        {
            "id": r.id,
            "topic": r.topic,
            "value": r.value,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None
        }
        for r in readings
    ]
