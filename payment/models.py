from sqlalchemy import Column, String, Integer, DateTime, Float, Enum as SQLAlchemyEnum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from db.db import Base
import uuid
import enum
from pydantic import validator

def generate_uuid():
    return str(uuid.uuid4())

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid" 
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"

class CouponType(enum.Enum):
    PERCENTAGE = "percentage"
    AMOUNT = "amount"

class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"


class CouponUsers(Base):
    __tablename__ = "coupon_users"
    
    coupon_id = Column(String(36), ForeignKey("coupons.id"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)

class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(String(36), primary_key=True, unique=True, default=generate_uuid, nullable=False)
    code = Column(String(255), nullable=False, unique=True)
    type = Column(SQLAlchemyEnum(CouponType), nullable=False)
    value = Column(Float, nullable=False)
    max_uses = Column(Integer, default=None)
    used_count = Column(Integer, default=0)
    valid_from = Column(DateTime, nullable=False, default=datetime.now)
    valid_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    used_by_users = relationship("User", secondary="coupon_users")

    @validator('code', pre=True, always=True)
    def validate_code(cls, v):
        if ' ' in v or not v.isalnum():
            raise ValueError('Code cannot contain spaces and special characters')
        return v.upper()

class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, unique=True, default=generate_uuid, nullable=False)
    user = Column(String(36), ForeignKey("users.id"), nullable=False)
    plan = Column(String(255), nullable=False)
    plan_duration = Column(Integer, nullable=True)
    coupon = Column(String(36), ForeignKey("coupons.id"), nullable=True)
    amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    final_amount = Column(Float, nullable=False)
    payment_id = Column(String(255), nullable=True)
    status = Column(SQLAlchemyEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, unique=True, default=generate_uuid, nullable=False)
    user = Column(String(36), ForeignKey("users.id"), nullable=False)
    order = Column(String(36), ForeignKey("orders.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(SQLAlchemyEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.PENDING)
    auto_renew = Column(Boolean, default=False)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
