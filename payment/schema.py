from pydantic import BaseModel
from datetime import datetime
from .models import CouponType

class PlanSchema(BaseModel):
    name: str
    plan_id: str | None
    description: str | None
    amount: float
    currency: str = "INR"
    duration_days: int
    is_active: bool = True

    class Config:
        from_attributes = True

class CouponSchema(BaseModel):
    code: str
    type: CouponType
    value: float
    max_uses: int | None
    used_count: int = 0
    valid_from: datetime
    valid_until: datetime | None
    is_active: bool = True

    class Config:
        from_attributes = True

class PaymentCreateSchema(BaseModel):
    plan: str
    coupon: str | None
    plan_type: str = "monthly"

class PaymentVerifySchema(BaseModel):
    razorpay_payment_id:str
    razorpay_subscription_id:str
    razorpay_signature:str