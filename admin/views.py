from auth.model import User
from patients.model import Patient, PatientXray
from predict.model import Prediction, Label
from payment.models import Plan, Coupon, Order, Subscription, CouponUsers
from contact.model import ContactUs
from sqladmin import ModelView


class UserAdmin(ModelView, model=User):
    column_list = ["id", "email", "name", "user_type", "account_type", "credits", "is_active"]
    column_searchable_list = ["email", "name", "phone"]
    column_sortable_list = ["email", "name", "created_at", "credits"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at", "password"]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name_plural = "Users"
    icon = "fa-solid fa-users"


class PatientAdmin(ModelView, model=Patient):
    column_list = ["id", "first_name", "last_name", "phone", "age", "gender"]
    column_searchable_list = ["first_name", "last_name", "phone"]
    column_sortable_list = ["first_name", "last_name", "created_at"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at"]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name_plural = "Patients"
    icon = "fa-solid fa-hospital-user"


class PredictionAdmin(ModelView, model=Prediction):
    column_list = ["id", "patient", "is_annotated", "created_at"]
    column_sortable_list = ["created_at", "is_annotated"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at", "predicted_image"]
    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True
    name_plural = "Predictions"
    icon = "fa-solid fa-brain"
    chart_type = "bar"
    chart_data = lambda self: {
        "labels": ["Annotated", "Not Annotated"],
        "datasets": [{
            "data": [
                self.session.query(Prediction).filter_by(is_annotated=True).count(),
                self.session.query(Prediction).filter_by(is_annotated=False).count()
            ]
        }]
    }


class PlanAdmin(ModelView, model=Plan):
    column_list = ["id", "rzp_plan_id", "amount", "type"]
    column_sortable_list = ["created_at", "amount", "type"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at"]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name_plural = "Plans"
    icon = "fa-solid fa-credit-card"


class CouponAdmin(ModelView, model=Coupon):
    column_list = ["id", "code", "type", "value", "used_count", "is_active"]
    column_searchable_list = ["code"]
    column_sortable_list = ["created_at", "used_count", "is_active"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at", "used_count", "used_by_users"]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name_plural = "Coupons"
    icon = "fa-solid fa-ticket"


class OrderAdmin(ModelView, model=Order):
    column_list = ["id", "user", "plan", "amount", "final_amount", "status"]
    column_searchable_list = ["id", "payment_id"]
    column_sortable_list = ["created_at", "status"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at", "payment_id"]
    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True
    name_plural = "Orders"
    icon = "fa-solid fa-shopping-cart"
    chart_type = "pie"
    chart_data = lambda self: {
        "labels": ["Pending", "Paid", "Failed", "Refunded", "Cancelled"],
        "datasets": [{
            "data": [
                self.session.query(Order).filter_by(status="pending").count(),
                self.session.query(Order).filter_by(status="paid").count(),
                self.session.query(Order).filter_by(status="failed").count(),
                self.session.query(Order).filter_by(status="refunded").count(),
                self.session.query(Order).filter_by(status="cancelled").count()
            ]
        }]
    }


class SubscriptionAdmin(ModelView, model=Subscription):
    column_list = ["id", "user", "start_date", "end_date", "status", "auto_renew"]
    column_sortable_list = ["created_at", "start_date", "end_date", "status"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at"]
    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True
    name_plural = "Subscriptions"
    icon = "fa-solid fa-repeat"
    chart_type = "pie"
    chart_data = lambda self: {
        "labels": ["Active", "Inactive", "Expired", "Cancelled", "Pending"],
        "datasets": [{
            "data": [
                self.session.query(Subscription).filter_by(status="active").count(),
                self.session.query(Subscription).filter_by(status="inactive").count(),
                self.session.query(Subscription).filter_by(status="expired").count(),
                self.session.query(Subscription).filter_by(status="cancelled").count(),
                self.session.query(Subscription).filter_by(status="pending").count()
            ]
        }]
    }


class ContactAdmin(ModelView, model=ContactUs):
    column_list = ["id", "first_name", "last_name", "email", "topic", "company_name"]
    column_searchable_list = ["email", "first_name", "last_name"]
    column_sortable_list = ["created_at"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at"]
    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True
    name_plural = "Contact Requests"
    icon = "fa-solid fa-envelope"
