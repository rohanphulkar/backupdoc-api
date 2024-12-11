from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Create Pydantic models for response serialization
class LabelResponse(BaseModel):
    id: str
    name: str
    percentage: float
    prediction_id: str
    include:bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PredictionResponse(BaseModel):
    id: str
    patient: str
    original_image: str
    predicted_image: Optional[str] = None
    is_annotated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True