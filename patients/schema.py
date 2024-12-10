from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .model import Gender

class PatientCreateSchema(BaseModel):
    first_name: str
    last_name: str
    phone: str
    age: int
    gender: Gender

    class Config:
        from_attributes = True

class PatientUpdateSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[Gender] = None

    class Config:
        from_attributes = True
