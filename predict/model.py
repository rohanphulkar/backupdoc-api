from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Boolean, Text, JSON
from sqlalchemy.dialects.mysql import LONGTEXT
from db.db import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())



class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String(36), primary_key=True, unique=True, default=generate_uuid, nullable=False)
    patient = Column(String(36), ForeignKey("patients.id"), nullable=False)
    original_image = Column(String(255), nullable=False)  # Image path should not be null
    is_annotated = Column(Boolean, nullable=False, default=False)
    predicted_image = Column(String(255), nullable=True)  # Can be null initially
    prediction = Column(LONGTEXT, nullable=False)  # Changed to LONGTEXT to handle very large strings
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

class Label(Base):
    __tablename__ = "labels"

    id = Column(String(36), primary_key=True, unique=True, default=generate_uuid, nullable=False)
    prediction_id = Column(String(36), ForeignKey("predictions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    percentage = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)