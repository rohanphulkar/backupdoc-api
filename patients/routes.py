from fastapi import APIRouter, Request, Depends, File, UploadFile
from sqlalchemy.orm import Session
from .schema import PatientCreateSchema, PatientUpdateSchema
from .model import Patient, PatientXray
from db.db import get_db
from auth.model import User
from fastapi.responses import JSONResponse
from utils.auth import get_current_user
from sqlalchemy import insert, select, update, delete
import os
patient_router = APIRouter()

@patient_router.post("/create",
    response_model=dict,
    status_code=201,
    summary="Create a new patient",
    description="""
    Create a new patient record with name, phone, date of birth and gender
    
    Required fields:
    - name: Patient's full name
    - phone: Valid phone number
    - date_of_birth: Date of birth in ISO format
    - gender: One of ["male", "female", "other"]
    
    Required headers:
    - Authorization: Bearer token from login
    """,
    responses={
        201: {"description": "Patient created successfully"},
        400: {"description": "Bad request - Invalid input"},
        401: {"description": "Unauthorized - Invalid token"},
        500: {"description": "Internal server error"}
    }
)
async def create_patient(request: Request, patient: PatientCreateSchema, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        if patient.name == "" or patient.phone == "" or patient.date_of_birth == "" or patient.gender == "":
            return JSONResponse(status_code=400, content={"error": "All fields are required"})
        
        stmt = insert(Patient).values(doctor_id=current_user, **patient.model_dump())
        db.execute(stmt)
        db.commit()
        return JSONResponse(status_code=201, content={"message": "Patient created successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error creating patient", "error": str(e)})

@patient_router.get("/all",
    response_model=dict,
    status_code=200, 
    summary="Get all patients",
    description="""
    Get list of all patients in the system
    
    Required headers:
    - Authorization: Bearer token from login
    """,
    responses={
        200: {"description": "List of patients retrieved successfully"},
        401: {"description": "Unauthorized - Invalid token"},
        500: {"description": "Internal server error"}
    }
)
async def get_all_patients(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        stmt = select(Patient)
        patients = db.execute(stmt).scalars().all()
        return JSONResponse(status_code=200, content={"patients": patients})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error getting patients", "error": str(e)})
    
@patient_router.get("/details/{patient_id}",
    response_model=dict,
    status_code=200,
    summary="Get patient details",
    description="""
    Get details of a specific patient by ID
    
    Required parameters:
    - patient_id: UUID of the patient
    
    Required headers:
    - Authorization: Bearer token from login
    """,
    responses={
        200: {"description": "Patient details retrieved successfully"},
        401: {"description": "Unauthorized - Invalid token"},
        404: {"description": "Patient not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_patient(request: Request, patient_id: str, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        stmt = select(Patient).where(Patient.id == patient_id)
        patient = db.execute(stmt).scalar_one_or_none()
        if not patient:
            return JSONResponse(status_code=404, content={"error": "Patient not found"})
        return JSONResponse(status_code=200, content={"patient": patient})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error getting patient", "error": str(e)})
    
@patient_router.get("/doctor",
    response_model=dict,
    status_code=200,
    summary="Get doctor's patients",
    description="""
    Get all patients assigned to the authenticated doctor
    
    Required headers:
    - Authorization: Bearer token from login
    """,
    responses={
        200: {"description": "Doctor's patients retrieved successfully"},
        401: {"description": "Unauthorized - Invalid token"},
        500: {"description": "Internal server error"}
    }
)
async def get_patient_by_doctor(request: Request, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        stmt = select(Patient).where(Patient.doctor_id == current_user)
        patient = db.execute(stmt).scalar_one_or_none()
        return JSONResponse(status_code=200, content={"patient": patient})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error getting patient", "error": str(e)})

@patient_router.patch("/update/{patient_id}",
    response_model=dict,
    status_code=200,
    summary="Update patient details",
    description="""
    Update details of a specific patient
    
    Optional fields (at least one required):
    - name: Patient's full name
    - phone: Valid phone number  
    - date_of_birth: Date of birth in ISO format
    - gender: One of ["male", "female", "other"]
    
    Required parameters:
    - patient_id: UUID of the patient
    
    Required headers:
    - Authorization: Bearer token from login
    """,
    responses={
        200: {"description": "Patient updated successfully"},
        401: {"description": "Unauthorized - Invalid token"},
        404: {"description": "Patient not found"},
        500: {"description": "Internal server error"}
    }
)
async def update_patient(request: Request, patient_id: str, patient: PatientUpdateSchema, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        # partial update
        stmt = update(Patient).where(Patient.id == patient_id).values(**patient.model_dump(exclude_unset=True))
        db.execute(stmt)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Patient updated successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error updating patient", "error": str(e)})

@patient_router.delete("/delete/{patient_id}",
    response_model=dict,
    status_code=200,
    summary="Delete patient",
    description="""
    Delete a specific patient record
    
    Required parameters:
    - patient_id: UUID of the patient
    
    Required headers:
    - Authorization: Bearer token from login
    """,
    responses={
        200: {"description": "Patient deleted successfully"},
        401: {"description": "Unauthorized - Invalid token"},
        404: {"description": "Patient not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_patient(request: Request, patient_id: str, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        stmt = delete(Patient).where(Patient.id == patient_id)
        db.execute(stmt)
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Patient deleted successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error deleting patient", "error": str(e)})
    

@patient_router.post("/upload-xray/{patient_id}",
    response_model=dict,
    status_code=200,
    summary="Upload patient X-ray",
    description="""
    Upload an X-ray image for a specific patient
    
    Required parameters:
    - patient_id: UUID of the patient
    
    Required form data:
    - file: X-ray image file (jpg, png, etc)
    
    Required headers:
    - Authorization: Bearer token from login
    """,
    responses={
        200: {"description": "X-ray uploaded successfully"},
        401: {"description": "Unauthorized - Invalid token"},
        404: {"description": "Patient or user not found"},
        500: {"description": "Internal server error"}
    }
)
async def upload_xray(
    request: Request, 
    patient_id: str,
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        user = db.query(User).filter(User.id == current_user).first()
        if not user:
            return JSONResponse(status_code=404, content={"error": "User not found"})
        
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return JSONResponse(status_code=404, content={"error": "Patient not found"})

        # Create uploads directory if it doesn't exist
        os.makedirs("uploads/original", exist_ok=True)
            
        file_path = f"uploads/original/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        xray = PatientXray(patient=patient.id, original_image=file_path)
        db.add(xray)
        db.commit()
        
        return JSONResponse(status_code=200, content={"message": "X-ray uploaded successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})