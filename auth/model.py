from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.dialects.mysql import TINYINT
from db.db import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), nullable=True, unique=True, default=generate_uuid, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(255), nullable=True, unique=True)
    password = Column(String(255), nullable=True)
    bio = Column(String(255), nullable=True)
    profile_url = Column(String(255), nullable=True)
    is_verified = Column(TINYINT(1), default=0)
    is_active = Column(TINYINT(1), default=1)
    user_type = Column(String(255), nullable=False, default="doctor")
    account_type = Column(String(255), nullable=False, default="free")
    credits = Column(Integer, default=3)
    credit_expiry = Column(DateTime, nullable=True)
    is_annual = Column(TINYINT(1), default=0)
    last_credit_updated_at = Column(DateTime, nullable=True)
    otp = Column(String(255), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)