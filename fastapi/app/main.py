from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
import asyncio
import io
import csv
import os
import json
import jwt
from datetime import datetime, timedelta, timezone
from app.models import SensorData, RawAccelerometerData, InferredAnalytics
from app.db import Base, engine, SessionLocal
from app.mqtt_handler import start_mqtt
from pydantic import BaseModel

app = FastAPI(title="Sensor Backend")

# Create tables automatically
Base.metadata.create_all(bind=engine)

# Authentication setup
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"

# Load users from environment variable (JSON string)
USERS_JSON = os.getenv("USERS", '{"admin": "admin123", "user": "password"}')
VALID_USERS = json.loads(USERS_JSON)

# Pydantic models for authentication
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Pydantic models for new data structures
class RawAccelerometerDataCreate(BaseModel):
    oxygen_concentrator_id: str
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float = None
    gyro_y: float = None
    gyro_z: float = None
    sample_rate: float
    sequence_number: int = None
    additional_sensors: dict = None  # JSON field for additional sensor data
    calibration_data: dict = None    # JSON field for calibration parameters
    processing_metadata: dict = None # JSON field for processing metadata

class InferredAnalyticsCreate(BaseModel):
    oxygen_concentrator_id: str
    cycle_time_seconds: float = None
    left_direction_seconds: float = None
    right_direction_seconds: float = None
    dominant_frequency_hz: float = None
    frequency_amplitude: float = None
    vibration_pattern: str = None
    efficiency_score: float = None
    anomaly_score: float = None
    operational_state: str
    confidence_level: float = None
    analysis_window_minutes: int = 5
    data_points_analyzed: int = None
    computed_metrics: dict = None     # JSON field for derived calculations
    algorithm_parameters: dict = None # JSON field for algorithm settings
    quality_indicators: dict = None   # JSON field for quality scores

# Authentication functions
def verify_credentials(username: str, password: str) -> bool:
    """Verify username and password against hardcoded credentials"""
    return VALID_USERS.get(username) == password

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

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

# Authentication endpoint
@app.post("/login", response_model=TokenResponse)
def login(login_request: LoginRequest):
    """Login with username and password to get JWT token"""
    if not verify_credentials(login_request.username, login_request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(data={"sub": login_request.username})
    return {"access_token": access_token, "token_type": "bearer"}

# Health endpoints (public)
@app.get("/ping")
def ping():
    return {"msg": "pong"}

@app.get("/health")
def health():
    return {"status": "healthy"}

# Data endpoint for Panel
@app.get("/data")
def get_sensor_data(
    limit: int = 100,
    oxygen_concentrator_id: str = None,
    system_in_use: bool = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Returns the latest `limit` sensor readings, ordered by newest first.
    Each reading includes: id, topic, value, timestamp.
    Supports filtering by oxygen_concentrator_id and system_in_use status.
    """
    query = db.query(SensorData).order_by(SensorData.id.desc())

    # Apply filters
    if oxygen_concentrator_id:
        query = query.filter(SensorData.oxygen_concentrator_id == oxygen_concentrator_id)

    if system_in_use is not None:
        query = query.filter(SensorData.system_in_use == system_in_use)

    readings = query.limit(limit).all()
    # Convert ORM objects to dicts with comprehensive sensor data
    return [
        {
            "id": r.id,
            "topic": r.topic,
            "value": r.value,  # Legacy compatibility
            "temperature": r.temperature,
            "humidity": r.humidity,
            "system_in_use": r.system_in_use,
            "oxygen_level": r.oxygen_level,
            "vibration_frequency": r.vibration_frequency,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "what3words_location": r.what3words_location,
            "oxygen_concentrator_id": r.oxygen_concentrator_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None
        }
        for r in readings
    ]

# Statistics endpoint
@app.get("/stats")
def get_operational_stats(
    oxygen_concentrator_id: str = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Returns operational statistics for the oxygen concentrator.
    Considers device operational if it receives data at least every 1 minute.
    """
    now = datetime.now(timezone.utc)

    # Define time periods
    periods = {
        "24h": now - timedelta(hours=24),
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30)
    }

    stats = {}

    for period_name, start_time in periods.items():
        query = db.query(SensorData).filter(SensorData.timestamp >= start_time)

        if oxygen_concentrator_id:
            query = query.filter(SensorData.oxygen_concentrator_id == oxygen_concentrator_id)

        # Get all readings in this period, ordered by timestamp
        readings = query.order_by(SensorData.timestamp).all()

        if not readings:
            stats[period_name] = {"operational_minutes": 0, "total_minutes": int((now - start_time).total_seconds() / 60)}
            continue

        # Calculate operational minutes (when we get data at least every 1 minute)
        operational_minutes = 0
        last_timestamp = None

        for reading in readings:
            if last_timestamp is not None:
                gap = (reading.timestamp - last_timestamp).total_seconds() / 60
                # If gap is <= 1 minute, count the minute as operational
                if gap <= 1:
                    operational_minutes += gap
                else:
                    # Only count 1 minute if there's a big gap
                    operational_minutes += 1
            else:
                # First reading counts as 1 minute
                operational_minutes += 1

            last_timestamp = reading.timestamp

        total_minutes = int((now - start_time).total_seconds() / 60)
        operational_hours = operational_minutes / 60

        stats[period_name] = {
            "operational_minutes": int(operational_minutes),
            "operational_hours": round(operational_hours, 1),
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 1)
        }

    return stats

# Endpoint to get unique oxygen concentrator IDs for filtering
@app.get("/concentrators")
def get_concentrator_ids(
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Returns list of unique oxygen concentrator IDs"""
    ids = db.query(SensorData.oxygen_concentrator_id).distinct().filter(
        SensorData.oxygen_concentrator_id.isnot(None)
    ).all()
    return [id[0] for id in ids if id[0]]

# Latest reading endpoint
@app.get("/latest")
def get_latest_reading(
    oxygen_concentrator_id: str = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Returns the most recent reading"""
    query = db.query(SensorData).order_by(SensorData.timestamp.desc())

    if oxygen_concentrator_id:
        query = query.filter(SensorData.oxygen_concentrator_id == oxygen_concentrator_id)

    latest = query.first()

    if latest:
        return {
            "id": latest.id,
            "topic": latest.topic,
            "value": latest.value,  # Legacy compatibility
            "temperature": latest.temperature,
            "humidity": latest.humidity,
            "system_in_use": latest.system_in_use,
            "oxygen_level": latest.oxygen_level,
            "vibration_frequency": latest.vibration_frequency,
            "latitude": latest.latitude,
            "longitude": latest.longitude,
            "what3words_location": latest.what3words_location,
            "oxygen_concentrator_id": latest.oxygen_concentrator_id,
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None
        }
    return None

# Timeline data endpoint for usage visualization
@app.get("/timeline")
def get_timeline_data(
    hours: int = 24,
    oxygen_concentrator_id: str = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Returns time-bucketed data for usage visualization.
    Each bucket represents operational status in time periods.
    """
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=hours)

    query = db.query(SensorData).filter(SensorData.timestamp >= start_time)

    if oxygen_concentrator_id:
        query = query.filter(SensorData.oxygen_concentrator_id == oxygen_concentrator_id)

    readings = query.order_by(SensorData.timestamp).all()

    if not readings:
        return {"buckets": [], "start_time": start_time.isoformat(), "end_time": now.isoformat()}

    # Create time buckets (15-minute intervals)
    bucket_size_minutes = 15
    bucket_size_seconds = bucket_size_minutes * 60
    total_buckets = int((now - start_time).total_seconds() / bucket_size_seconds) + 1

    buckets = []
    for i in range(total_buckets):
        bucket_start = start_time + timedelta(seconds=i * bucket_size_seconds)
        bucket_end = bucket_start + timedelta(seconds=bucket_size_seconds)

        # Count readings in this bucket
        bucket_readings = [r for r in readings if bucket_start <= r.timestamp < bucket_end]

        # Consider operational if there are readings (at least 1 per bucket)
        operational = len(bucket_readings) > 0

        buckets.append({
            "start": bucket_start.isoformat(),
            "end": bucket_end.isoformat(),
            "operational": operational,
            "reading_count": len(bucket_readings)
        })

    return {
        "buckets": buckets,
        "start_time": start_time.isoformat(),
        "end_time": now.isoformat(),
        "bucket_size_minutes": bucket_size_minutes
    }

# Raw accelerometer data endpoints
@app.post("/raw-accelerometer")
def create_raw_accelerometer_data(
    data: RawAccelerometerDataCreate,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create raw accelerometer data entry"""
    db_data = RawAccelerometerData(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return {"id": db_data.id, "message": "Raw accelerometer data created successfully"}

@app.get("/raw-accelerometer")
def get_raw_accelerometer_data(
    limit: int = 1000,
    oxygen_concentrator_id: str = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get raw accelerometer data"""
    query = db.query(RawAccelerometerData).order_by(RawAccelerometerData.timestamp.desc())

    if oxygen_concentrator_id:
        query = query.filter(RawAccelerometerData.oxygen_concentrator_id == oxygen_concentrator_id)

    readings = query.limit(limit).all()

    return [
        {
            "id": r.id,
            "oxygen_concentrator_id": r.oxygen_concentrator_id,
            "accel_x": r.accel_x,
            "accel_y": r.accel_y,
            "accel_z": r.accel_z,
            "gyro_x": r.gyro_x,
            "gyro_y": r.gyro_y,
            "gyro_z": r.gyro_z,
            "sample_rate": r.sample_rate,
            "sequence_number": r.sequence_number,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None
        }
        for r in readings
    ]

# Inferred analytics endpoints
@app.post("/analytics")
def create_analytics(
    data: InferredAnalyticsCreate,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create inferred analytics entry"""
    db_data = InferredAnalytics(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return {"id": db_data.id, "message": "Analytics data created successfully"}

@app.get("/analytics")
def get_analytics(
    limit: int = 100,
    oxygen_concentrator_id: str = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get inferred analytics data"""
    query = db.query(InferredAnalytics).order_by(InferredAnalytics.timestamp.desc())

    if oxygen_concentrator_id:
        query = query.filter(InferredAnalytics.oxygen_concentrator_id == oxygen_concentrator_id)

    analytics = query.limit(limit).all()

    return [
        {
            "id": a.id,
            "oxygen_concentrator_id": a.oxygen_concentrator_id,
            "cycle_time_seconds": a.cycle_time_seconds,
            "left_direction_seconds": a.left_direction_seconds,
            "right_direction_seconds": a.right_direction_seconds,
            "dominant_frequency_hz": a.dominant_frequency_hz,
            "frequency_amplitude": a.frequency_amplitude,
            "vibration_pattern": a.vibration_pattern,
            "efficiency_score": a.efficiency_score,
            "anomaly_score": a.anomaly_score,
            "operational_state": a.operational_state,
            "confidence_level": a.confidence_level,
            "analysis_window_minutes": a.analysis_window_minutes,
            "data_points_analyzed": a.data_points_analyzed,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "analysis_timestamp": a.analysis_timestamp.isoformat() if a.analysis_timestamp else None
        }
        for a in analytics
    ]

@app.get("/analytics/latest")
def get_latest_analytics(
    oxygen_concentrator_id: str = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get the latest analytics entry"""
    query = db.query(InferredAnalytics).order_by(InferredAnalytics.timestamp.desc())

    if oxygen_concentrator_id:
        query = query.filter(InferredAnalytics.oxygen_concentrator_id == oxygen_concentrator_id)

    latest = query.first()

    if latest:
        return {
            "id": latest.id,
            "oxygen_concentrator_id": latest.oxygen_concentrator_id,
            "cycle_time_seconds": latest.cycle_time_seconds,
            "left_direction_seconds": latest.left_direction_seconds,
            "right_direction_seconds": latest.right_direction_seconds,
            "dominant_frequency_hz": latest.dominant_frequency_hz,
            "frequency_amplitude": latest.frequency_amplitude,
            "vibration_pattern": latest.vibration_pattern,
            "efficiency_score": latest.efficiency_score,
            "anomaly_score": latest.anomaly_score,
            "operational_state": latest.operational_state,
            "confidence_level": latest.confidence_level,
            "analysis_window_minutes": latest.analysis_window_minutes,
            "data_points_analyzed": latest.data_points_analyzed,
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
            "analysis_timestamp": latest.analysis_timestamp.isoformat() if latest.analysis_timestamp else None
        }
    return None

# Enhanced vibration frequency endpoint
@app.get("/vibration/frequency")
def get_vibration_frequency_data(
    hours: int = 24,
    oxygen_concentrator_id: str = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get vibration frequency data over time"""
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=hours)

    query = db.query(SensorData).filter(SensorData.timestamp >= start_time)

    if oxygen_concentrator_id:
        query = query.filter(SensorData.oxygen_concentrator_id == oxygen_concentrator_id)

    readings = query.order_by(SensorData.timestamp).all()

    return [
        {
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "vibration_frequency": r.vibration_frequency,
            "oxygen_concentrator_id": r.oxygen_concentrator_id
        }
        for r in readings if r.vibration_frequency is not None
    ]

# CSV download endpoint (protected)
@app.get("/download/csv")
def download_csv(
    start_date: str = None,
    end_date: str = None,
    oxygen_concentrator_id: str = None,
    current_user: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """
    Download sensor data as CSV.
    start_date and end_date should be in ISO format: 2025-09-30T00:00:00
    """
    query = db.query(SensorData)

    # Apply date filters if provided
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(SensorData.timestamp >= start_dt)
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(SensorData.timestamp <= end_dt)
        except ValueError:
            pass

    if oxygen_concentrator_id:
        query = query.filter(SensorData.oxygen_concentrator_id == oxygen_concentrator_id)

    # Get data ordered by timestamp
    readings = query.order_by(SensorData.timestamp).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'id', 'topic', 'timestamp', 'oxygen_concentrator_id',
        'temperature', 'humidity', 'system_in_use', 'oxygen_level',
        'vibration_frequency', 'latitude', 'longitude', 'what3words_location'
    ])

    # Write data rows
    for reading in readings:
        writer.writerow([
            reading.id,
            reading.topic,
            reading.timestamp.isoformat() if reading.timestamp else '',
            reading.oxygen_concentrator_id,
            reading.temperature,
            reading.humidity,
            reading.system_in_use,
            reading.oxygen_level,
            reading.vibration_frequency,
            reading.latitude,
            reading.longitude,
            reading.what3words_location
        ])

    # Generate filename
    filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # Return CSV as download
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
