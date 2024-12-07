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


client = razorpay.Client(auth=(config("RAZORPAY_KEY_ID"), config("RAZORPAY_KEY_SECRET")))

payment_router = APIRouter()

plans = [
    {
        "name": "doctor",
        "plan_id": config("DOCTOR_PLAN_ID"),
    },
    {
        "name": "premium", 
        "plan_id": config("PREMIUM_PLAN_ID"),
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
        return JSONResponse(status_code=200, content={"coupons": [coupon.to_dict() for coupon in coupons]})
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
        return JSONResponse(status_code=200, content={"coupon": coupon.to_dict()})
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
        if not user or user.role != "admin":
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
        if not user or user.role != "admin":
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
        if not user or user.role != "admin":
            return JSONResponse(status_code=401, content={"error": "Admin access required"})
        
        coupon_details = db.query(Coupon).filter(Coupon.id == coupon_id).first()
        if not coupon_details:
            return JSONResponse(status_code=404, content={"error": "Coupon not found"})
        
        db.delete(coupon_details)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Coupon deleted successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@payment_router.get("/orders/get-all-orders",
    summary="Get all orders",
    description="Retrieves list of all subscription orders. Admin only.",
    response_description="Returns list of order objects with payment details",
    responses={
        200: {"description": "Successfully retrieved orders list"},
        401: {"description": "Unauthorized - Admin access required"},
        500: {"description": "Server error while fetching orders"}
    }
)
async def get_all_orders(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
            
        user = db.query(User).filter(User.id == current_user).first()
        if not user or user.role != "admin":
            return JSONResponse(status_code=401, content={"error": "Admin access required"})
            
        orders = db.query(Order).all()
        return JSONResponse(status_code=200, content={"orders": [order.to_dict() for order in orders]})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@payment_router.get("/orders/get-orders-of-user",
    summary="Get user orders",
    description="Retrieves all subscription orders of the authenticated user",
    response_description="Returns list of user's order objects with payment details",
    responses={
        200: {"description": "Successfully retrieved user orders"},
        401: {"description": "Unauthorized access"},
        500: {"description": "Server error while fetching orders"}
    }
)
async def get_orders_of_user(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})

        orders = db.query(Order).filter(Order.user_id == current_user).all()
        return JSONResponse(status_code=200, content={"orders": [order.to_dict() for order in orders]})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@payment_router.get("/orders/get-order-details/{order_id}",
    summary="Get order details",
    description="Retrieves detailed information about a specific order",
    response_description="Returns complete details of the requested order",
    responses={
        200: {"description": "Successfully retrieved order details"},
        404: {"description": "Order not found"},
        500: {"description": "Server error while fetching order"}
    }
)
async def get_order_details(
    request: Request,
    order_id: str = Path(..., description="Unique identifier of the order"),
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
            
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return JSONResponse(status_code=404, content={"error": "Order not found"})
            
        # Only allow admin or order owner to view details
        user = db.query(User).filter(User.id == current_user).first()
        if not user or (user.role != "admin" and str(order.user_id) != current_user):
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
            
        return JSONResponse(status_code=200, content={"order": order.to_dict()})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@payment_router.delete("/orders/delete-order/{order_id}",
    summary="Delete order",
    description="Permanently deletes an order record. Admin only.",
    response_description="Returns confirmation of order deletion",
    responses={
        200: {"description": "Order deleted successfully"},
        401: {"description": "Unauthorized - Admin access required"},
        404: {"description": "Order not found"},
        500: {"description": "Server error while deleting order"}
    }
)
async def delete_order(
    request: Request,
    order_id: str = Path(..., description="Unique identifier of order to delete"),
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
            
        user = db.query(User).filter(User.id == current_user).first()
        if not user or user.role != "admin":
            return JSONResponse(status_code=401, content={"error": "Admin access required"})
        
        order_details = db.query(Order).filter(Order.id == order_id).first()
        if not order_details:
            return JSONResponse(status_code=404, content={"error": "Order not found"})
        
        db.delete(order_details)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Order deleted successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    



@payment_router.post("/payment/create",
    summary="Create subscription payment", 
    description="Initiates a new subscription payment or plan upgrade with optional coupon",
    response_description="Returns payment/subscription ID for verification",
    responses={
        200: {"description": "Payment initiated successfully"},
        401: {"description": "Unauthorized access"},
        404: {"description": "User/Plan not found"},
        500: {"description": "Server error while creating payment"}
    }
)
async def subscribe(
    request: Request,
    payment: PaymentCreateSchema = Body(..., description="Payment details including plan ID and optional coupon"),
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
        user = db.query(User).filter(User.id == current_user).first()
        if not user:
            return JSONResponse(status_code=404, content={"error": "User not found"})
        
        # Check if user has active subscription
        active_subscription = db.query(Subscription).filter(
            Subscription.user == str(user.id),
            Subscription.status == SubscriptionStatus.ACTIVE
        ).first()

        plan = next((p for p in plans if p["name"].lower() == payment.plan.lower()), None)
        if not plan:
            return JSONResponse(status_code=404, content={"message": "Plan not found"})

        # Validate plan upgrade
        if active_subscription:
            current_plan = user.account_type
            requested_plan = payment.plan.lower()
            
            if current_plan == "premium":
                return JSONResponse(status_code=400, content={"error": "Already on highest plan"})
            elif current_plan == "doctor" and requested_plan != "premium":
                return JSONResponse(status_code=400, content={"error": "Can only upgrade to premium plan"})
        
        coupon = None
        if payment.coupon:
            coupon = db.query(Coupon).filter(
                Coupon.code == payment.coupon,
                Coupon.is_active == True,
                Coupon.valid_until > datetime.now()
            ).first()
            if not coupon:
                return JSONResponse(status_code=400, content={"error": "Invalid or expired coupon"})

        plan_details = client.plan.fetch(plan["plan_id"])
        
        amount = plan_details["item"]["amount"]

        if coupon:
            if coupon.type == "percentage":
                discount_amount = int(amount * coupon.value / 100)
            else:
                discount_amount = int(coupon.value)
                if discount_amount > amount:
                    discount_amount = amount
        else:
            discount_amount = 0

        subscription_data = {
            'plan_id': plan["plan_id"],
            'customer_notify': 1,
            'quantity': 1 if payment.plan_type == "yearly" else 1,
            'total_count': 12 if payment.plan_type == "yearly" else 1,
            'start_at': int(time.time()) + 600,
            'notes': {'message': 'Subscription Payment'},
        }
        
        if discount_amount > 0:
            subscription_data['addons'] = [{
                'item': {
                    "name": f"Discount for {plan['name']}",
                    "amount": -discount_amount,
                    "currency": "INR",
                }
            }]

        subscription = client.subscription.create(data=subscription_data)

        # Cancel existing subscription if upgrading
        if active_subscription:
            active_subscription.status = SubscriptionStatus.CANCELLED
            db.add(active_subscription)
            db.commit()

        order = Order(
            user=current_user,
            plan=plan["name"],
            amount=amount,
            discount_amount=discount_amount,
            final_amount=amount - discount_amount,
            payment_id=subscription["id"],
            status=PaymentStatus.PENDING
        )

        db.add(order)
        db.commit()
        
        return JSONResponse(status_code=200, content={
            "message": "Payment created successfully",
            "subscription_id": subscription["id"],
            "amount": amount - discount_amount
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@payment_router.post("/payment/verify",
    summary="Verify subscription payment",
    description="Verifies payment signature and activates subscription",
    response_description="Returns confirmation of payment verification and subscription activation",
    responses={
        200: {"description": "Payment verified and subscription activated"},
        400: {"description": "Invalid signature/Inactive subscription"},
        404: {"description": "Order/User/Plan not found"},
        500: {"description": "Server error while verifying payment"}
    }
)
async def verify_payment(
    payment: PaymentVerifySchema = Body(..., description="Payment verification details including signature"),
    db: Session = Depends(get_db)
):
    try:
        order = db.query(Order).filter(Order.payment_id == payment.razorpay_subscription_id).first()
        if not order:
            return JSONResponse(status_code=404, content={"error": "Order not found"})
        
        msg = f"{payment.razorpay_payment_id}|{payment.razorpay_subscription_id}"
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
        
        subscription = client.subscription.fetch(payment.razorpay_subscription_id)
        
        user = db.query(User).filter(User.id == order.user).first()
        if not user:
            return JSONResponse(status_code=404, content={"error": "User not found"})
        
        duration_days = 365 if subscription["quantity"] == 12 else 30
        
        # Cancel any existing active subscriptions
        active_subscriptions = db.query(Subscription).filter(
            Subscription.user == str(user.id),
            Subscription.status == SubscriptionStatus.ACTIVE
        ).all()
        
        for sub in active_subscriptions:
            sub.status = SubscriptionStatus.CANCELLED
            db.add(sub)
        
        user_subscription = Subscription(
            user=str(user.id),
            order=str(order.id),
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=duration_days),
            status=SubscriptionStatus.ACTIVE
        )

        db.add(user_subscription)
        db.commit()

        order.status = PaymentStatus.PAID
        db.add(order)
        db.commit()

        if order.plan == "doctor":
            user.account_type = "doctor"
            user.credits = 150
        elif order.plan == "premium":
            user.account_type = "premium"
            user.credits = 500
        
        user.last_credit_updated_at = datetime.now()
        user.credit_expiry = user_subscription.end_date
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
        if subscription["status"] not in ["active", "authenticated"]:
            return JSONResponse(status_code=400, content={"message": "Subscription is not active"})
        if subscription["status"] == "cancelled":
            return JSONResponse(status_code=400, content={"message": "Subscription is already cancelled"})
            
        subscription = client.subscription.cancel(subscription_id)
        order = db.query(Order).filter(Order.payment_id == subscription_id).first()

        if not order:
            return JSONResponse(status_code=404, content={"error": "Order not found"})
            
        # Verify user owns the subscription or is admin
        user = db.query(User).filter(User.id == current_user).first()
        if not user or (user.role != "admin" and str(order.user_id) != current_user):
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
        
        plan_details = client.plan.fetch(plan["plan_id"])

        amount = plan_details["item"]["amount"]

        print(plan_details)

        return JSONResponse(status_code=200, content={"amount": amount })
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
    db: Session = Depends(get_db)
):
    try:
        # Validate and fetch coupon
        coupon = (
            db.query(Coupon)
            .filter(
                Coupon.code == coupon_code.upper(),
                Coupon.is_active.is_(True),
                Coupon.valid_until > datetime.now(),
                Coupon.max_uses.is_(None) | (Coupon.used_count < Coupon.max_uses)
            )
            .first()
        )
        
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

        # Get plan details and calculate discount
        plan_details = client.plan.fetch(plan["plan_id"])
        amount = plan_details["item"]["amount"]
        
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
                "original_amount": amount / 100,
                "discount_amount": discount_amount / 100,
                "final_amount": final_amount / 100,
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
    
@payment_router.post("/upgrade-subscription",
    summary="Upgrade subscription",
    description="Upgrades a subscription to a higher plan",
    response_description="Returns confirmation of subscription upgrade",
    responses={
        200: {"description": "Subscription upgraded successfully"},
        400: {"description": "Invalid subscription/Plan not found"},
        500: {"description": "Server error while upgrading subscription"}
    }
)
async def upgrade_subscription(
    request: Request,
    payment: PaymentCreateSchema = Body(..., description="Payment details including optional coupon"),
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
        user = db.query(User).filter(User.id == current_user).first()
        if not user:
            return JSONResponse(status_code=404, content={"error": "User not found"})
        
        user_subscription = db.query(Subscription).filter(Subscription.user == current_user).first()
        if not user_subscription:
            return JSONResponse(status_code=404, content={"error": "Subscription not found"})
        
        if user_subscription.status != SubscriptionStatus.ACTIVE:
            return JSONResponse(status_code=400, content={"error": "Subscription is not active"})
        
        if user_subscription.end_date < datetime.now():
            return JSONResponse(status_code=400, content={"error": "Subscription has expired"})

        # Determine upgrade plan based on current account type
        upgrade_plan = None
        if user.account_type == "free":
            upgrade_plan = next((p for p in plans if p["name"].lower() == "doctor"), None)
        elif user.account_type == "doctor":
            upgrade_plan = next((p for p in plans if p["name"].lower() == "premium"), None)
        else:
            return JSONResponse(status_code=400, content={"error": "Already on highest plan"})

        if not upgrade_plan:
            return JSONResponse(status_code=404, content={"message": "Upgrade plan not found"})

        # Handle coupon if provided
        coupon = None
        if payment.coupon:
            coupon = db.query(Coupon).filter(
                Coupon.code == payment.coupon,
                Coupon.is_active == True,
                Coupon.valid_until > datetime.now()
            ).first()
            if not coupon:
                return JSONResponse(status_code=400, content={"error": "Invalid or expired coupon"})

        # Get plan details and calculate amount
        plan_details = client.plan.fetch(upgrade_plan["plan_id"])
        amount = plan_details["item"]["amount"]

        # Calculate discount if coupon exists
        if coupon:
            if coupon.type == "percentage":
                discount_amount = int(amount * coupon.value / 100)
            else:
                discount_amount = int(coupon.value)
                if discount_amount > amount:
                    discount_amount = amount
        else:
            discount_amount = 0

        # Prepare subscription data
        subscription_data = {
            'plan_id': upgrade_plan["plan_id"],
            'customer_notify': 1,
            'quantity': 12 if payment.plan_type == "yearly" else 1,
            'total_count': 12 if payment.plan_type == "yearly" else 1,
            'start_at': int(time.time()) + 600,
            'notes': {'message': 'Subscription Upgrade Payment'},
        }

        if discount_amount > 0:
            subscription_data['addons'] = [{
                'item': {
                    "name": f"Discount for {upgrade_plan['name']}",
                    "amount": -discount_amount,
                    "currency": "INR",
                }
            }]

        # Create new subscription
        subscription = client.subscription.create(data=subscription_data)

        # Create order record
        order = Order(
            user=current_user,
            plan=upgrade_plan["name"],
            amount=amount,
            discount_amount=discount_amount,
            final_amount=amount - discount_amount,
            payment_id=subscription["id"],
            status=PaymentStatus.PENDING
        )

        db.add(order)
        db.commit()

        return JSONResponse(status_code=200, content={
            "message": "Upgrade payment created successfully",
            "subscription_id": subscription["id"],
            "amount": amount - discount_amount
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})