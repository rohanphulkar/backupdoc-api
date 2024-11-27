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
    name: str | None
    phone: str | None 
    date_of_birth: datetime | None
    gender: Gender | None

    class Config:
        from_attributes = True
