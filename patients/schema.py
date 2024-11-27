from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .model import Gender

class PatientCreateSchema(BaseModel):
    name: str
    phone: str
    date_of_birth: datetime
    gender: Gender

    class Config:
        from_attributes = True

class PatientUpdateSchema(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None 
    gender: Optional[Gender] = None

    class Config:
        from_attributes = True
