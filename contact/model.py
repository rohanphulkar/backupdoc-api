from db.db import Base
from sqlalchemy import Column, String, Text, DateTime
import uuid
from datetime import datetime

def generate_uuid():
    return str(uuid.uuid4())

class ContactUs(Base):
    __tablename__ = "contact_us"
    id = Column(String(36), nullable=True, unique=True, default=generate_uuid, primary_key=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    topic = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    company_size = Column(String(255), nullable=False)
    query = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    