from pydantic import BaseModel
from datetime import datetime
# Create Pydantic models for response serialization
class LabelResponse(BaseModel):
    id: str
    name: str
    percentage: float
    prediction_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class PredictionResponse(BaseModel):
    id: str
    patient: str
    original_image: str
    predicted_image: str | None
    is_annotated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True