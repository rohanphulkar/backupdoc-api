from db.db import engine, SessionLocal
from auth.model import User
from utils.auth import verify_password
from admin.views import *
from sqlalchemy import select
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from sqladmin import Admin


# This page will implement the authentication for your admin panel
class AdminAuth(AuthenticationBackend):

    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")
        
        async with SessionLocal() as db:
            query = select(User).filter(User.email == email)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            if user and verify_password(str(password), str(user.password)):
                if str(user.user_type) == "admin":
                    request.session.update({"token": user.email})
                    return True
            return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
            
        async with SessionLocal() as db:
            query = select(User).filter(User.email == token)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            return user is not None and str(user.user_type) == "admin"


# add the views to admin
def create_admin(app):
    authentication_backend = AdminAuth(secret_key="supersecretkey")
    admin = Admin(app=app, engine=engine, authentication_backend=authentication_backend)
    admin.add_view(UserAdmin)
    admin.add_view(PatientAdmin) 
    admin.add_view(PredictionAdmin)
    admin.add_view(CouponAdmin)
    admin.add_view(OrderAdmin)
    admin.add_view(SubscriptionAdmin)
    admin.add_view(ContactAdmin)
    return admin



