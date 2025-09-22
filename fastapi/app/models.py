from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from db import Base

class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True)
    value = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)