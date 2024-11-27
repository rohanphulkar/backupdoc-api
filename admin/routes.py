from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from auth.model import *
from patients.model import *
from payment.models import *
from predict.model import *
from db.db import get_db
from sqlalchemy.orm import Session
from utils.auth import get_current_user


admin_router = APIRouter()

@admin_router.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    if str(user.user_type) != "admin":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    # Get user stats
    total_users = db.query(User).count()
    total_doctors = db.query(User).filter(User.user_type == "doctor").count()
    verified_users = db.query(User).filter(User.is_verified == 1).count()
    active_users = db.query(User).filter(User.is_active == 1).count()

    # Get patient stats
    total_patients = db.query(Patient).count()
    male_patients = db.query(Patient).filter(Patient.gender == Gender.MALE).count()
    female_patients = db.query(Patient).filter(Patient.gender == Gender.FEMALE).count()

    # Get subscription stats
    total_subscriptions = db.query(Subscription).count()
    active_subscriptions = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.ACTIVE
    ).count()
    expired_subscriptions = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.EXPIRED
    ).count()

    # Get order stats
    from sqlalchemy import func
    
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(Order.status == PaymentStatus.PENDING).count()
    paid_orders = db.query(Order).filter(Order.status == PaymentStatus.PAID).count()
    failed_orders = db.query(Order).filter(Order.status == PaymentStatus.FAILED).count()
    total_revenue = db.query(Order).filter(Order.status == PaymentStatus.PAID).with_entities(
        func.sum(Order.final_amount)
    ).scalar() or 0

    # Get plan stats
    total_plans = db.query(Plan).count()
    active_plans = db.query(Plan).filter(Plan.is_active == True).count()
    doctor_plans = db.query(Plan).filter(Plan.type == PlanType.DOCTOR).count()
    premium_plans = db.query(Plan).filter(Plan.type == PlanType.PREMIUM).count()

    # Get coupon stats
    total_coupons = db.query(Coupon).count()
    active_coupons = db.query(Coupon).filter(Coupon.is_active == True).count()
    expired_coupons = db.query(Coupon).filter(
        Coupon.valid_until < datetime.now()
    ).count()

    # Get prediction stats
    total_predictions = db.query(Prediction).count()
    annotated_predictions = db.query(Prediction).filter(Prediction.is_annotated == True).count()
    unannotated_predictions = db.query(Prediction).filter(Prediction.is_annotated == False).count()


    return JSONResponse(status_code=200, content={
        "users": {
            "total": total_users,
            "doctors": total_doctors,
            "verified": verified_users,
            "active": active_users
        },
        "patients": {
            "total": total_patients,
            "male": male_patients,
            "female": female_patients
        },
        "subscriptions": {
            "total": total_subscriptions,
            "active": active_subscriptions,
            "expired": expired_subscriptions
        },
        "orders": {
            "total": total_orders,
            "pending": pending_orders,
            "paid": paid_orders,
            "failed": failed_orders,
            "total_revenue": total_revenue
        },
        "plans": {
            "total": total_plans,
            "active": active_plans,
            "doctor": doctor_plans,
            "premium": premium_plans
        },
        "coupons": {
            "total": total_coupons,
            "active": active_coupons,
            "expired": expired_coupons
        },
        "predictions": {
            "total": total_predictions,
            "annotated": annotated_predictions,
            "unannotated": unannotated_predictions
        }
    })