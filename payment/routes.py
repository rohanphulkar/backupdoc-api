from fastapi import APIRouter, Depends, Request, Path, Query, Body
from fastapi.responses import JSONResponse
from .models import *
from .schema import *
from db.db import get_db
from sqlalchemy.orm import Session
from utils.auth import get_current_user
import razorpay
from decouple import config
from auth.model import User
import time
import hmac
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import func, select


client = razorpay.Client(auth=(config("RAZORPAY_KEY_ID"), config("RAZORPAY_KEY_SECRET")))

payment_router = APIRouter()


plans = [
    {
        "name": "starter",
        "prices":{
            "monthly": 999,
            "half_yearly": 5994,
            "yearly": 11988,
        },
        "credits": 50,
    },
    {
        "name": "pro",
        "prices":{
            "monthly": 3999,
            "half_yearly": 3999 * 6,
            "yearly": 3999 * 12,
        },
        "credits": 300,
    },
    {
        "name": "max",
        "prices":{
            "monthly": 5999,
            "half_yearly": 5999 * 6,
            "yearly": 5999 * 12,
        },
        "credits": 600,
    }
]

    
@payment_router.get("/coupon/get-all-coupons",
    summary="Get all coupons", 
    description="Retrieves list of all available discount coupons",
    response_description="Returns list of coupon objects with details like code, discount etc",
    responses={
        200: {"description": "Successfully retrieved coupons list"},
        500: {"description": "Server error while fetching coupons"}
    }
)
async def get_all_coupons(db: Session = Depends(get_db)):
    try:
        coupons = db.query(Coupon).all()
        return JSONResponse(status_code=200, content={"coupons": [{
            "id": coupon.id,
            "code": coupon.code,
            "type": str(coupon.type),  # Convert enum to string
            "value": coupon.value,
            "max_uses": coupon.max_uses,
            "valid_from": coupon.valid_from.isoformat() if coupon.valid_from else None,
            "valid_until": coupon.valid_until.isoformat() if coupon.valid_until else None,
            "is_active": coupon.is_active
        } for coupon in coupons]})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@payment_router.get("/coupon/get-coupon-details/{coupon_id}",
    summary="Get coupon details",
    description="Retrieves detailed information about a specific coupon",
    response_description="Returns complete details of the requested coupon",
    responses={
        200: {"description": "Successfully retrieved coupon details"},
        404: {"description": "Coupon not found"},
        500: {"description": "Server error while fetching coupon"}
    }
)
async def get_coupon_details(
    coupon_id: str = Path(..., description="Unique identifier of the coupon"),
    db: Session = Depends(get_db)
):
    try:
        coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if not coupon:
            return JSONResponse(status_code=404, content={"error": "Coupon not found"})
        return JSONResponse(status_code=200, content={"coupon": {
            "id": coupon.id,
            "code": coupon.code,
            "type": str(coupon.type),
            "value": coupon.value,
            "max_uses": coupon.max_uses,
            "valid_from": coupon.valid_from.isoformat() if coupon.valid_from else None,
            "valid_until": coupon.valid_until.isoformat() if coupon.valid_until else None,
            "is_active": coupon.is_active
        }})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@payment_router.post("/coupon/create-coupon",
    summary="Create discount coupon",
    description="Creates a new discount coupon. Admin only.",
    response_description="Returns confirmation of coupon creation",
    responses={
        200: {"description": "Coupon created successfully"},
        401: {"description": "Unauthorized - Admin access required"},
        500: {"description": "Server error while creating coupon"}
    }
)
async def create_coupon(
    request: Request,
    coupon: CouponSchema = Body(..., description="Coupon details including code, discount value and validity"),
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
            
        user = db.query(User).filter(User.id == current_user).first()
        if not user or str(user.user_type) != "admin":
            return JSONResponse(status_code=401, content={"error": "Admin access required"})
            
        new_coupon = Coupon(
            code=coupon.code,
            type=coupon.type,
            value=coupon.value,
            max_uses=coupon.max_uses,
            valid_from=datetime.now(),
            valid_until=coupon.valid_until,
            is_active=coupon.is_active
        )
        db.add(new_coupon)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Coupon created successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@payment_router.patch("/coupon/update-coupon/{coupon_id}",
    summary="Update discount coupon",
    description="Updates an existing discount coupon. Admin only.",
    response_description="Returns confirmation of coupon update",
    responses={
        200: {"description": "Coupon updated successfully"},
        401: {"description": "Unauthorized - Admin access required"},
        404: {"description": "Coupon not found"},
        500: {"description": "Server error while updating coupon"}
    }
)
async def update_coupon(
    request: Request,
    coupon_id: str = Path(..., description="Unique identifier of coupon to update"),
    coupon: CouponSchema = Body(..., description="Updated coupon details"),
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
            
        user = db.query(User).filter(User.id == current_user).first()
        if not user or user.user_type != "admin":
            return JSONResponse(status_code=401, content={"error": "Admin access required"})
        
        coupon_details = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if not coupon_details:
            return JSONResponse(status_code=404, content={"error": "Coupon not found"})
        
        if coupon.code:
            coupon_details.code = coupon.code
        if coupon.type:
            coupon_details.type = coupon.type
        if coupon.value:
            coupon_details.value = coupon.value
        if coupon.max_uses:
            coupon_details.max_uses = coupon.max_uses
        if coupon.valid_from:
            coupon_details.valid_from = coupon.valid_from
        if coupon.valid_until:
            coupon_details.valid_until = coupon.valid_until
        if coupon.is_active is not None:
            coupon_details.is_active = coupon.is_active

        db.commit()
        return JSONResponse(status_code=200, content={"message": "Coupon updated successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@payment_router.delete("/coupon/delete-coupon/{coupon_id}",
    summary="Delete discount coupon",
    description="Permanently deletes a discount coupon. Admin only.",
    response_description="Returns confirmation of coupon deletion",
    responses={
        200: {"description": "Coupon deleted successfully"},
        401: {"description": "Unauthorized - Admin access required"},
        404: {"description": "Coupon not found"},
        500: {"description": "Server error while deleting coupon"}
    }
)
async def delete_coupon(
    request: Request,
    coupon_id: str = Path(..., description="Unique identifier of coupon to delete"),
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
            
        user = db.query(User).filter(User.id == current_user).first()
        if not user or user.user_type != "admin":
            return JSONResponse(status_code=401, content={"error": "Admin access required"})
        
        order_details = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if not order_details:
            return JSONResponse(status_code=404, content={"error": "Order not found"})
        
        db.delete(order_details)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Order deleted successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    

@payment_router.post("/payment/create",
    summary="Create one-time payment", 
    description="Initiates a new one-time payment with optional coupon",
    response_description="Returns payment order ID for verification",
    responses={
        200: {"description": "Payment initiated successfully"},
        401: {"description": "Unauthorized access"},
        404: {"description": "User/Plan not found"},
        500: {"description": "Server error while creating payment"}
    }
)
async def create_payment(
    request: Request,
    payment: PaymentCreateSchema = Body(..., description="Payment details including plan and optional coupon"),
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
        user = db.query(User).filter(User.id == current_user).first()
        if not user:
            return JSONResponse(status_code=404, content={"error": "User not found"})

        # Find selected plan
        selected_plan = None
        for p in plans:
            if p["name"] == payment.plan:
                selected_plan = p
                break
                
        if not selected_plan:
            return JSONResponse(status_code=404, content={"error": "Invalid plan selected"})

        # Get plan amount based on duration
        if payment.plan_type == "monthly":
            amount = selected_plan["prices"]["monthly"]
        elif payment.plan_type == "half_yearly":
            amount = selected_plan["prices"]["half_yearly"] 
        else:
            amount = selected_plan["prices"]["yearly"]

        # Handle coupon if provided
        coupon = None
        if payment.coupon:
            coupon = db.query(Coupon).filter(
                func.lower(Coupon.code) == payment.coupon.lower(),
                Coupon.is_active == True,
                Coupon.valid_until > datetime.now()
            ).first()
            
            if not coupon:
                return JSONResponse(status_code=400, content={"error": "Invalid or expired coupon"})
                
            coupon_usage = db.query(CouponUsers).filter(
                CouponUsers.coupon_id == coupon.id,
                CouponUsers.user_id == str(user.id)
            ).first()
            
            if coupon_usage:
                return JSONResponse(status_code=400, content={"error": "Coupon already used"})

            if str(coupon.type) == "CouponType.PERCENTAGE":
                discount_amount = int(amount * coupon.value / 100)
            else:
                discount_amount = int(coupon.value)
        else:
            discount_amount = 0

        final_amount = amount - discount_amount

        # Create Razorpay order
        order_data = {
            'amount': final_amount * 100,  # Convert to paise
            'currency': 'INR',
            'notes': {
                'plan_name': selected_plan['name'],
                'plan_type': payment.plan_type
            }
        }

        razorpay_order = client.order.create(data=order_data)

        # Create order record
        order = Order(
            user=current_user,
            plan=selected_plan["name"],
            duration_months=12 if payment.plan_type == "yearly" else (6 if payment.plan_type == "half_yearly" else 1),
            coupon=coupon.id if coupon else None,
            amount=amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            payment_id=razorpay_order["id"],
            status=PaymentStatus.PENDING
        )

        db.add(order)
        db.commit()
        
        return JSONResponse(status_code=200, content={
            "message": "Payment created successfully",
            "order_id": razorpay_order["id"],
            "amount": final_amount
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@payment_router.post("/payment/verify",
    summary="Verify payment",
    description="Verifies payment signature and activates plan", 
    response_description="Returns confirmation of payment verification and plan activation",
    responses={
        200: {"description": "Payment verified and plan activated"},
        400: {"description": "Invalid signature"},
        404: {"description": "Order/User/Plan not found"},
        500: {"description": "Server error while verifying payment"}
    }
)
async def verify_payment(
    payment: PaymentVerifySchema = Body(..., description="Payment verification details including signature"),
    db: Session = Depends(get_db)
):
    try:
        order = db.query(Order).filter(Order.payment_id == payment.razorpay_order_id).first()
        if not order:
            return JSONResponse(status_code=404, content={"error": "Order not found"})
        
        # Verify signature
        msg = f"{payment.razorpay_order_id}|{payment.razorpay_payment_id}"
        secret_key = str(config("RAZORPAY_KEY_SECRET"))
        generated_signature = hmac.new(
            secret_key.encode('utf-8'),
            msg.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if generated_signature != payment.razorpay_signature:
            order.status = PaymentStatus.FAILED
            db.commit()
            return JSONResponse(status_code=400, content={"error": "Invalid signature"})
        
        user = db.query(User).filter(User.id == order.user).first()
        if not user:
            return JSONResponse(status_code=404, content={"error": "User not found"})

        # Find plan details
        selected_plan = None
        for p in plans:
            if p["name"] == order.plan:
                selected_plan = p
                break

        if not selected_plan:
            return JSONResponse(status_code=404, content={"error": "Plan not found"})
        
        # Update user credits and expiry
        user.account_type = selected_plan["name"]
        user.credits = selected_plan["credits"]
        user.last_credit_updated_at = datetime.now()
        user.credit_expiry = datetime.now() + timedelta(days=order.duration_months * 30)
        
        order.status = PaymentStatus.PAID
        db.add(order)
        
        # Add coupon usage after successful payment if coupon was used
        if order.coupon:
            coupon_user = CouponUsers(
                coupon_id=order.coupon,
                user_id=str(user.id)
            )
            db.add(coupon_user)
            
            coupon = db.query(Coupon).filter(Coupon.id == order.coupon).first()
            if coupon:
                coupon.used_count += 1
                db.add(coupon)
        
        db.add(user)
        db.commit()

        return JSONResponse(status_code=200, content={"message": "Payment verified successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@payment_router.get("/cancel-subscription",
    summary="Cancel subscription",
    description="Cancels an active subscription for the authenticated user",
    response_description="Returns confirmation of subscription cancellation",
    responses={
        200: {"description": "Subscription cancelled successfully"},
        400: {"description": "Subscription not active/already cancelled"},
        401: {"description": "Unauthorized access"},
        404: {"description": "Order/Subscription not found"},
        500: {"description": "Server error while cancelling subscription"}
    }
)
async def cancel_subscription(
    request: Request,
    subscription_id: str = Query(..., description="Unique identifier of subscription to cancel"),
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
        subscription = client.subscription.fetch(subscription_id)

        print(subscription)
        if subscription["status"] not in ["active", "authenticated"]:
            return JSONResponse(status_code=400, content={"message": "Subscription is not active"})
        if subscription["status"] == "cancelled":
            return JSONResponse(status_code=400, content={"message": "Subscription is already cancelled"})
            
        subscription = client.subscription.cancel(subscription_id, {
            'cancel_at_cycle_end': 0
        })
        order = db.query(Order).filter(Order.payment_id == subscription_id).first()

        if not order:
            return JSONResponse(status_code=404, content={"error": "Order not found"})
            
        # Verify user owns the subscription or is admin
        user = db.query(User).filter(User.id == current_user).first()
        if not user or (user.user_type != "admin" and str(order.user_id) != current_user):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
        user_subscription = db.query(Subscription).filter(Subscription.order_id == order.id).first()
        if not user_subscription:
            return JSONResponse(status_code=404, content={"error": "User subscription not found"})
        
        user_subscription.status = SubscriptionStatus.CANCELLED
        db.add(user_subscription)
        db.commit()

        order.status = PaymentStatus.CANCELLED
        db.add(order)
        db.commit()
        
        # Reset user account type and credits if subscription cancelled
        subscription_user = db.query(User).filter(User.id == order.user_id).first()
        if subscription_user:
            subscription_user.account_type = "free"
            subscription_user.credits = 0
            subscription_user.credit_expiry = None
            db.add(subscription_user)
            db.commit()
            
        return JSONResponse(status_code=200, content={"message": "Subscription cancelled successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    

@payment_router.get("/fetch-plan-details",
    summary="Fetch plan details", 
    description="Fetches the details of a plan",
    response_description="Returns the plan details",
    responses={
        200: {"description": "Plan details fetched successfully"},
        400: {"description": "Invalid plan name"},
        500: {"description": "Server error while fetching plan details"}
    }
)
async def fetch_plan_details(
    plan_name: str = Query(..., description="Name of the plan to fetch details for"),
    db: Session = Depends(get_db)
):
    try:
        plan = next((p for p in plans if p["name"].lower() == plan_name.lower()), None)
        if not plan:
            return JSONResponse(status_code=400, content={"error": f"Plan '{plan_name}' not found"})

        return JSONResponse(status_code=200, content={
            "name": plan["name"],
            "prices": plan["prices"],
            "credits": plan["credits"]
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
@payment_router.get("/apply-coupon",
    summary="Apply coupon",
    description="Applies a discount coupon to the payment",
    response_description="Returns the coupon details and the final amount",
    responses={
        200: {"description": "Coupon applied successfully"},
        400: {"description": "Invalid coupon/Expired coupon/Invalid plan"},
        500: {"description": "Server error while applying coupon"}
    }
)
async def apply_coupon(
    plan_name: str = Query(..., description="Name of the plan to apply coupon to"),
    coupon_code: str = Query(..., description="Coupon code to apply"),
    billing: str = Query(..., description="Billing type (monthly/half_yearly/yearly)"),
    db: Session = Depends(get_db)
):
    try:
        # Validate and fetch coupon - case insensitive search
        coupon = db.query(Coupon).filter(
            func.lower(Coupon.code) == coupon_code.lower(),  # Case insensitive comparison
            Coupon.is_active.is_(True),
        ).first()
        
        if not coupon:
            return JSONResponse(
                status_code=400, 
                content={"error": "Invalid or expired coupon"}
            )

        # Validate and fetch plan
        plan = next(
            (p for p in plans if p["name"].lower() == plan_name.lower()), 
            None
        )
        if not plan:
            return JSONResponse(
                status_code=400,
                content={"error": f"Plan '{plan_name}' not found"}
            )

        # Validate billing type
        if billing not in plan["prices"]:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid billing type: {billing}"}
            )

        # Get plan amount based on billing type and calculate discount
        amount = plan["prices"][billing]
        
        discount_amount = (
            int(amount * coupon.value / 100)
            if str(coupon.type) == "CouponType.PERCENTAGE" or str(coupon.type) == "percentage"
            else min(int(coupon.value), amount)
        )

        final_amount = amount - discount_amount

        return JSONResponse(
            status_code=200, 
            content={
                "message": "Coupon applied successfully",
                "original_amount": amount,
                "discount_amount": discount_amount,
                "final_amount": final_amount,
                "coupon": {
                    "code": coupon.code,
                    "type": coupon.type.value,
                    "value": coupon.value
                }
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to apply coupon: {str(e)}"}
        )
