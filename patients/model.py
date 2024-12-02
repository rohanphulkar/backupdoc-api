from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLAlchemyEnum, Text, Integer
from sqlalchemy.orm import relationship
from db.db import Base
from datetime import datetime
import uuid
import enum

def generate_uuid():
    return str(uuid.uuid4())

class Gender(enum.Enum):
    MALE = "male"
    FEMALE = "female" 
    OTHER = "other"

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, unique=True, default=generate_uuid, nullable=False)
    doctor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False)
    age = Column(Integer, nullable=False)
    date_of_birth = Column(DateTime, nullable=False)
    gender = Column(SQLAlchemyEnum(Gender), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class PatientXray(Base):
    __tablename__ = "patient_xrays"

    id = Column(String(36), primary_key=True, unique=True, default=generate_uuid, nullable=False)
    patient = Column(String(50), ForeignKey("patients.id"), nullable=False)
    prediction_id = Column(String(255), nullable=True)
    original_image = Column(String(255), nullable=False)
    annotated_image = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)