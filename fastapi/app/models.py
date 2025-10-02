from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db import Base

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

    # Flexible JSON storage for additional parameters
    additional_data = Column(JSON, nullable=True)  # For calculated values, future parameters, etc.
    device_metadata = Column(JSON, nullable=True)  # For device metadata, calibration data, etc.

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class RawAccelerometerData(Base):
    """Raw accelerometer data for detailed analytics"""
    __tablename__ = "raw_accelerometer_data"

    id = Column(Integer, primary_key=True, index=True)

    # Device identification
    oxygen_concentrator_id = Column(String, index=True)

    # Raw accelerometer readings (3-axis)
    accel_x = Column(Float)
    accel_y = Column(Float)
    accel_z = Column(Float)

    # Additional raw sensor data
    gyro_x = Column(Float, nullable=True)
    gyro_y = Column(Float, nullable=True)
    gyro_z = Column(Float, nullable=True)

    # Sampling information
    sample_rate = Column(Float)  # Hz
    sequence_number = Column(Integer)  # For ordering samples

    # Flexible JSON storage for additional accelerometer data
    additional_sensors = Column(JSON, nullable=True)  # For magnetometer, pressure, temperature, etc.
    calibration_data = Column(JSON, nullable=True)  # For sensor calibration parameters
    processing_metadata = Column(JSON, nullable=True)  # For processing flags, quality indicators, etc.

    # Timestamp with high precision
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class InferredAnalytics(Base):
    """Derived analytics and inferred data from sensor readings"""
    __tablename__ = "inferred_analytics"

    id = Column(Integer, primary_key=True, index=True)

    # Device identification
    oxygen_concentrator_id = Column(String, index=True)

    # Cycle analysis
    cycle_time_seconds = Column(Float, nullable=True)  # Total cycle time
    left_direction_seconds = Column(Float, nullable=True)  # Time moving left
    right_direction_seconds = Column(Float, nullable=True)  # Time moving right

    # Vibration analysis
    dominant_frequency_hz = Column(Float, nullable=True)  # Main vibration frequency
    frequency_amplitude = Column(Float, nullable=True)  # Amplitude at dominant frequency
    vibration_pattern = Column(String, nullable=True)  # Pattern classification (e.g., "regular", "irregular", "stopped")

    # Performance metrics
    efficiency_score = Column(Float, nullable=True)  # 0-100 efficiency rating
    anomaly_score = Column(Float, nullable=True)  # 0-100 anomaly detection score

    # Operational state
    operational_state = Column(String)  # "running", "idle", "maintenance", "error"
    confidence_level = Column(Float)  # 0-1 confidence in the analysis

    # Analysis metadata
    analysis_window_minutes = Column(Integer, default=5)  # Time window used for analysis
    data_points_analyzed = Column(Integer)  # Number of raw samples used

    # Flexible JSON storage for additional analytics
    computed_metrics = Column(JSON, nullable=True)  # For derived calculations, FFT results, etc.
    algorithm_parameters = Column(JSON, nullable=True)  # For algorithm settings used in analysis
    quality_indicators = Column(JSON, nullable=True)  # For data quality scores, confidence intervals, etc.

    # Relationships
    sensor_data_start_id = Column(Integer, ForeignKey('sensor_data.id'), nullable=True)
    sensor_data_end_id = Column(Integer, ForeignKey('sensor_data.id'), nullable=True)

    # Timestamp for when analysis was performed
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    analysis_timestamp = Column(DateTime(timezone=True), server_default=func.now())