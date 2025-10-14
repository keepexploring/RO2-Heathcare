# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **Oxygen Concentrator Monitoring System** that collects sensor data via MQTT, stores it in PostgreSQL, exposes it through a FastAPI backend, and visualizes it using a Panel dashboard. The system tracks operational metrics, environmental conditions, and device location to monitor oxygen concentrator usage and health.

## Architecture

### Three-Tier System

1. **MQTT Layer** - Eclipse Mosquitto broker receives sensor data from oxygen concentrators
2. **Backend API** - FastAPI service handles MQTT subscriptions, database persistence, and REST API
3. **Dashboard** - Panel (HoloViz) web application for data visualization and user interaction

### Data Flow

```
IoT Sensors → MQTT (sensors/#) → FastAPI MQTT Handler → PostgreSQL → REST API → Panel Dashboard
```

### Key Components

- **fastapi/app/mqtt_handler.py** - Subscribes to MQTT topics, parses sensor payloads (JSON or legacy float), persists to database
- **fastapi/app/main.py** - REST API with JWT authentication, data endpoints, operational statistics, CSV export
- **fastapi/app/models.py** - SQLAlchemy ORM models for three data types:
  - `SensorData` - Primary sensor readings (temperature, humidity, oxygen level, vibration, location)
  - `RawAccelerometerData` - High-frequency accelerometer readings for vibration analysis
  - `InferredAnalytics` - Derived metrics (cycle times, efficiency scores, anomaly detection)
- **panel/app/dashboard.py** - Interactive dashboard with authentication, real-time updates (5s), plots, timeline visualization

### Database Schema

- **sensor_data** - Main table with comprehensive sensor fields, indexed on timestamp and oxygen_concentrator_id
- **raw_accelerometer_data** - Raw sensor data for advanced analytics (FFT, frequency analysis)
- **inferred_analytics** - Computed metrics and operational state classifications
- All tables include flexible JSON columns for extensibility (additional_data, device_metadata, etc.)

### Authentication

- JWT-based authentication for all protected endpoints (except /ping, /health, /login)
- Users configured via environment variable `USERS` (JSON format: `{"username": "password"}`)
- Token stored in Panel session cache, auto-refresh on 401 responses
- Both FastAPI and Panel services must share the same `JWT_SECRET`

## Development Commands

### Initial Setup

```bash
# Build and start all services (PostgreSQL, Mosquitto, FastAPI, Panel)
docker-compose up --build

# Create local PostgreSQL database (if running outside Docker)
createdb sensordb

# Set up Python virtual environment
pyenv virtualenv 3.13.8 .venv
pyenv local .venv
```

### Running Services

```bash
# Start all services
docker-compose up

# Stop all services
docker-compose down

# View logs for specific service
docker-compose logs -f fastapi
docker-compose logs -f panel
docker-compose logs -f mosquitto
docker-compose logs -f postgres
```

### Database Migrations

```bash
# Generate new migration from model changes
alembic revision --autogenerate -m "migration description"

# Apply migrations
alembic upgrade head
```

### Testing

```bash
# Test MQTT publishing (simulates sensor data)
python publish_test.py

# Test authentication
python test_auth.py

# Test logout
python test_logout.py
```

### Service Endpoints

- **PostgreSQL**: localhost:5432 (postgres/postgres/sensordb)
- **MQTT Broker**: localhost:1883
- **FastAPI Backend**: http://localhost:8000
  - Health: http://localhost:8000/ping → `{"msg":"pong"}`
  - Docs: http://localhost:8000/docs (Swagger UI)
- **Panel Dashboard**: http://localhost:5006

## Important Patterns

### MQTT Message Format

The system supports both legacy (single float) and comprehensive JSON formats:

```json
{
  "temperature": 25.3,
  "humidity": 65.2,
  "system_in_use": true,
  "oxygen_level": 95.5,
  "vibration_frequency": 30.2,
  "latitude": 51.5074,
  "longitude": -0.1278,
  "what3words_location": "folder.clever.laptop",
  "oxygen_concentrator_id": "OXY-001"
}
```

### Environment Variables

**FastAPI Service:**
- `DATABASE_URL` - PostgreSQL connection string
- `MQTT_BROKER_URL` - Mosquitto hostname (default: mosquitto)
- `MQTT_BROKER_PORT` - MQTT port (default: 1883)
- `JWT_SECRET` - Secret key for JWT token signing
- `USERS` - JSON string of valid users (e.g., `{"admin": "admin123"}`)

**Panel Service:**
- `DATABASE_URL` - PostgreSQL connection string
- `FASTAPI_URL` - FastAPI backend URL (e.g., http://fastapi:8000)

### Operational Statistics Logic

The `/stats` endpoint calculates operational time by measuring gaps between sensor readings. A device is considered operational when readings arrive within 1-minute intervals. This differs from the `/timeline` endpoint which uses 15-minute buckets to visualize usage patterns.

### Adding New Sensor Fields

1. Add column to model in `fastapi/app/models.py` (use nullable=True for optional fields)
2. Generate migration: `alembic revision --autogenerate -m "add new field"`
3. Apply migration: `alembic upgrade head`
4. Update MQTT handler in `mqtt_handler.py` to parse new field
5. Update API endpoints in `main.py` to return new field
6. Update dashboard in `panel/app/dashboard.py` to display/plot new field

### JSON Field Usage

Three tables include JSON fields for flexible data storage without schema changes:
- Use `additional_data`/`additional_sensors` for new sensor types
- Use `device_metadata`/`calibration_data` for device-specific parameters
- Use `processing_metadata`/`computed_metrics` for derived calculations

## Deployment

See DEPLOYMENT.md for Railway deployment instructions. Key points:
- Deploy as separate services (fastapi, panel, postgres)
- Ensure `JWT_SECRET` matches across services
- Update `FASTAPI_URL` in Panel service to point to deployed FastAPI service
- PostgreSQL `DATABASE_URL` is auto-set by Railway

## Code Style

- Backend: FastAPI with Pydantic models for request/response validation
- Database: SQLAlchemy ORM with Alembic migrations
- Frontend: Panel reactive components with periodic callbacks
- Async patterns: MQTT handler uses asyncio, FastAPI endpoints are sync (database I/O is blocking)
- Error handling: Try/except blocks log errors, return empty data on failure, 401 triggers re-authentication
