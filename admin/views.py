from auth.model import User
from patients.model import Patient, PatientXray
from predict.model import Prediction, Label
from payment.models import Coupon, Order, CouponUsers, PaymentStatus, CouponType
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

    def chart_data(self):
        return {
            "labels": ["Annotated", "Not Annotated"],
            "datasets": [{
                "data": [
                    self.session.query(Prediction).filter_by(is_annotated=True).count(),
                    self.session.query(Prediction).filter_by(is_annotated=False).count()
                ]
            }]
        }


class CouponAdmin(ModelView, model=Coupon):
    column_list = ["id", "code", "type", "value", "max_uses", "used_count", "valid_from", "valid_until", "is_active"]
    column_searchable_list = ["code"]
    column_sortable_list = ["created_at", "used_count", "is_active", "valid_until"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at", "used_count", "used_by_users"]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    name_plural = "Coupons"
    icon = "fa-solid fa-ticket"


class OrderAdmin(ModelView, model=Order):
    column_list = ["id", "user", "plan", "duration_months", "amount", "discount_amount", "final_amount", "status", "payment_id"]
    column_searchable_list = ["id", "payment_id", "user"]
    column_sortable_list = ["created_at", "status", "amount", "final_amount"]
    column_default_sort = ("created_at", True)
    form_excluded_columns = ["id", "created_at", "updated_at"]
    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True
    name_plural = "Orders"
    icon = "fa-solid fa-shopping-cart"
    chart_type = "pie"

    def chart_data(self):
        return {
            "labels": ["Pending", "Paid", "Failed", "Refunded", "Cancelled"],
            "datasets": [{
                "data": [
                    self.session.query(Order).filter_by(status=PaymentStatus.PENDING).count(),
                    self.session.query(Order).filter_by(status=PaymentStatus.PAID).count(),
                    self.session.query(Order).filter_by(status=PaymentStatus.FAILED).count(),
                    self.session.query(Order).filter_by(status=PaymentStatus.REFUNDED).count(),
                    self.session.query(Order).filter_by(status=PaymentStatus.CANCELLED).count()
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
