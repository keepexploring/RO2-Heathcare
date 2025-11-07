from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Date, Numeric
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


# ============================================================================
# CRM MODELS - Phase 1 & 2: User Management and Concentrator Registry
# ============================================================================

class User(Base):
    """User authentication and profiles"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Role-based access control
    role = Column(String(20), nullable=False, default='user')  # 'user' or 'admin'

    # Profile information
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    organization = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    concentrators = relationship("Concentrator", back_populates="owner", foreign_keys="[Concentrator.user_id]")
    service_records_created = relationship("ServiceRecord", back_populates="creator", foreign_keys="[ServiceRecord.created_by]")
    notifications = relationship("Notification", back_populates="user")


class Concentrator(Base):
    """Oxygen concentrator registry and lifecycle management"""
    __tablename__ = "concentrators"

    id = Column(Integer, primary_key=True, index=True)

    # Device identification - links to sensor_data.oxygen_concentrator_id
    concentrator_id = Column(String(50), unique=True, nullable=False, index=True)

    # Ownership
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)

    # Device specifications
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    oxygen_capacity_lpm = Column(Numeric(5, 2), nullable=True)  # Litres per minute

    # Procurement and age
    procurement_date = Column(Date, nullable=True)
    age_months = Column(Integer, nullable=True)

    # Location and association
    associated_hospital = Column(String(255), nullable=True)
    location_notes = Column(Text, nullable=True)

    # Status and removal workflow
    status = Column(String(20), default='active')  # 'active', 'pending_removal', 'removed'
    removal_reason = Column(Text, nullable=True)
    removal_requested_at = Column(DateTime(timezone=True), nullable=True)
    removal_requested_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    removal_approved_at = Column(DateTime(timezone=True), nullable=True)
    removal_approved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # General notes
    notes = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="concentrators", foreign_keys=[user_id])
    service_records = relationship("ServiceRecord", back_populates="concentrator", cascade="all, delete-orphan")
    service_intervals = relationship("ServiceInterval", back_populates="concentrator", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="concentrator", cascade="all, delete-orphan")
    manuals = relationship("ConcentratorManual", back_populates="concentrator", cascade="all, delete-orphan")


class ServiceRecord(Base):
    """Service needed and service completed records"""
    __tablename__ = "service_records"

    id = Column(Integer, primary_key=True, index=True)
    concentrator_id = Column(Integer, ForeignKey('concentrators.id', ondelete='CASCADE'), nullable=False, index=True)

    # Record type
    record_type = Column(String(20), nullable=False)  # 'service_needed' or 'service_completed'

    # Service details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default='normal')  # 'low', 'normal', 'high', 'urgent'

    # Resolution status
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=False)

    # Relationships
    concentrator = relationship("Concentrator", back_populates="service_records")
    creator = relationship("User", back_populates="service_records_created", foreign_keys=[created_by])
    attachments = relationship("ServiceAttachment", back_populates="service_record", cascade="all, delete-orphan")


class ServiceAttachment(Base):
    """Photos and videos attached to service records"""
    __tablename__ = "service_attachments"

    id = Column(Integer, primary_key=True, index=True)
    service_record_id = Column(Integer, ForeignKey('service_records.id', ondelete='CASCADE'), nullable=False, index=True)

    # File information
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # 'image' or 'video'
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)

    # Metadata
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=False)

    # Relationships
    service_record = relationship("ServiceRecord", back_populates="attachments")


class ServiceInterval(Base):
    """Preventive maintenance schedules and intervals"""
    __tablename__ = "service_intervals"

    id = Column(Integer, primary_key=True, index=True)
    concentrator_id = Column(Integer, ForeignKey('concentrators.id', ondelete='CASCADE'), nullable=False, index=True)

    # Interval definition
    interval_type = Column(String(20), nullable=False)  # 'time_based', 'usage_based', 'hours_based'
    description = Column(Text, nullable=False)

    # Time-based intervals
    interval_value = Column(Integer, nullable=True)  # e.g., 6 for "6 months"
    interval_unit = Column(String(20), nullable=True)  # 'days', 'weeks', 'months', 'years'

    # Usage-based intervals
    max_idle_days = Column(Integer, nullable=True)  # e.g., 14 for "must run every 2 weeks"

    # Hours-based intervals
    hours_interval = Column(Integer, nullable=True)  # e.g., 10000 for "every 10,000 hours"

    # Scheduling
    last_completed_at = Column(DateTime(timezone=True), nullable=True)
    next_due_date = Column(DateTime(timezone=True), nullable=True)

    # Notification status
    notification_sent_at = Column(DateTime(timezone=True), nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    concentrator = relationship("Concentrator", back_populates="service_intervals")
    notifications = relationship("Notification", back_populates="service_interval", cascade="all, delete-orphan")


class Notification(Base):
    """Service reminders and alerts"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    concentrator_id = Column(Integer, ForeignKey('concentrators.id', ondelete='CASCADE'), nullable=False, index=True)
    service_interval_id = Column(Integer, ForeignKey('service_intervals.id', ondelete='CASCADE'), nullable=True)

    # Notification details
    notification_type = Column(String(50), nullable=False)  # 'service_due', 'no_recent_data', 'service_overdue'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(20), default='normal')  # 'low', 'normal', 'high', 'urgent'

    # Status
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Delivery
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_via = Column(String(20), nullable=True)  # 'email', 'sms', 'in_app'

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="notifications")
    concentrator = relationship("Concentrator", back_populates="notifications")
    service_interval = relationship("ServiceInterval", back_populates="notifications")


class ConcentratorManual(Base):
    """Manuals, repair guides, and documentation resources"""
    __tablename__ = "concentrator_manuals"

    id = Column(Integer, primary_key=True, index=True)

    # Association (can be specific concentrator or brand/model)
    concentrator_id = Column(Integer, ForeignKey('concentrators.id', ondelete='CASCADE'), nullable=True, index=True)
    brand = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)

    # Document information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    document_type = Column(String(50), nullable=False)  # 'manual', 'repair_guide', 'faq', 'video', 'link'

    # File or URL
    file_path = Column(String(500), nullable=True)
    url = Column(String(500), nullable=True)

    # Metadata
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    uploaded_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    concentrator = relationship("Concentrator", back_populates="manuals")