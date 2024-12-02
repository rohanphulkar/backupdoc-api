from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from db.db import Base, engine
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import os
from auth.routes import user_router
from patients.routes import patient_router
from payment.routes import payment_router
from predict.routes import prediction_router

Base.metadata.create_all(bind=engine)


middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*']
    )
]


app = FastAPI(
    title="Backupdoc API",
    middleware=middleware, 
    license_info={"name": "Backupdoc", "url": "https://backupdoc.ai"}
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="profile_pictures")

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(patient_router, prefix="/patient", tags=["patient"])
app.include_router(prediction_router, prefix="/predict", tags=["predict"])
app.include_router(payment_router, tags=["payment"])
