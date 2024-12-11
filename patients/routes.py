from fastapi import APIRouter, Request, Depends, File, UploadFile, status
from sqlalchemy.orm import Session
from .schema import PatientCreateSchema, PatientUpdateSchema
from .model import Patient, PatientXray, Gender
from db.db import get_db
from auth.model import User
from fastapi.responses import JSONResponse
from utils.auth import get_current_user, verify_token
from sqlalchemy import insert, select, update, delete
import os
from predict.model import Prediction, Label
from sqlalchemy.exc import SQLAlchemyError


patient_router = APIRouter()

@patient_router.get("/search",
    response_model=dict,
    status_code=200,
    summary="Search patients",
    description="""
    Search patients by name or phone number. Returns matching patients for the logged in doctor.
    
    Required parameters:
    - query: Search term to match against patient name or phone
    
    Required headers:
    - Authorization: Bearer token from login
    """,
    responses={
        200: {"description": "Patients retrieved successfully"},
        401: {"description": "Unauthorized - Invalid token"},
        500: {"description": "Internal server error"}
    }
)
async def search_patients(request: Request, query: str, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})

        # Split query into words and create search conditions for each word
        search_terms = query.split()
        search_conditions = []
        
        for term in search_terms:
            search_conditions.append(
                (
                    Patient.first_name.ilike(f"%{term}%") |
                    Patient.last_name.ilike(f"%{term}%") |
                    Patient.phone.ilike(f"%{term}%")
                )
            )

        # Search patients belonging to current doctor
        stmt = (
            select(Patient)
            .where(
                Patient.doctor_id == current_user,
                *search_conditions  # Unpack all search conditions
            )
        )
        result = db.execute(stmt)
        patients = result.scalars().all()

        return JSONResponse(
            status_code=200, 
            content={
                "patients": [
                    {
                        "id": p.id,
                        "first_name": p.first_name,
                        "last_name": p.last_name,
                        "phone": p.phone,
                        "age": p.age,
                        "gender": p.gender.value
                    } 
                    for p in patients
                ]
            }
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@patient_router.get("/validate-patient/{patient_id}",
    response_model=dict,
    status_code=200,
    summary="Validate patient",
    description="""
    Validate a patient by ID
    """,
    responses={
        200: {"description": "Patient validated successfully"},
        401: {"description": "Unauthorized - Invalid token"},
        500: {"description": "Internal server error"}
    }
)
async def validate_patient(request: Request, patient_id: str, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        stmt = select(Patient).where(Patient.id == patient_id)
        result = db.execute(stmt)
        patient = result.scalar_one_or_none()
        
        if not patient:
            return JSONResponse(status_code=404, content={"error": "Patient not found"})
        
        return JSONResponse(status_code=200, content={"patient": {
            "id": patient.id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "phone": patient.phone,
        }})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
        

@patient_router.post("/create",
    response_model=dict,
    status_code=201,
    summary="Create a new patient",
    description="""
    Create a new patient record with first name, last name, phone, age and gender
    
    Required fields:
    - first_name: Patient's first name
    - last_name: Patient's last name 
    - phone: Valid phone number
    - age: Patient's age
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
        if not all([patient.first_name, patient.last_name, patient.phone, patient.age, patient.gender]):
            return JSONResponse(status_code=400, content={"error": "All fields are required"})
        
        # Check if patient already exists
        stmt = select(Patient).where(Patient.phone == patient.phone)
        result = db.execute(stmt)
        existing_patient = result.scalar_one_or_none()
        
        if existing_patient:
            return JSONResponse(status_code=400, content={"error": "Patient already exists with this phone number"})
        
        stmt = insert(Patient).values(doctor_id=current_user, **patient.model_dump())
        result = db.execute(stmt)

        # Get the newly created patient
        stmt = select(Patient).where(Patient.id == result.inserted_primary_key[0])
        result = db.execute(stmt)
        new_patient = result.scalar_one()
      
        return JSONResponse(status_code=201, content={"message": "Patient created successfully", "patient": {
            "id": new_patient.id,
            "first_name": new_patient.first_name,
            "last_name": new_patient.last_name,
            "phone": new_patient.phone,
            "age": new_patient.age,
            "gender": new_patient.gender.value,
            "created_at": new_patient.created_at.isoformat(),
            "updated_at": new_patient.updated_at.isoformat()
        }})
    except SQLAlchemyError as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

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
        result = db.execute(stmt)
        patients = result.scalars().all()
        
        return JSONResponse(status_code=200, content={"patients": [
            {
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "phone": p.phone,
                "age": p.age,
                "gender": p.gender.value,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat()
            } for p in patients
        ]})
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
        
        stmt = select(User).where(User.id == current_user)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        stmt = select(Patient).where(Patient.id == patient_id)
        result = db.execute(stmt)
        patient = result.scalar_one_or_none()
        
        if not patient:
            return JSONResponse(status_code=404, content={"error": "Patient not found"})
            
        return JSONResponse(status_code=200, content={"patient": {
            "id": patient.id,
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "phone": patient.phone,
            "age": patient.age,
            "gender": patient.gender.value,
            "created_at": patient.created_at.isoformat(),
            "updated_at": patient.updated_at.isoformat()
        }, "doctor": {
            "id": user.id,
            "credits": user.credits
        }})
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
        decoded_user = verify_token(request)

        if not decoded_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        user_id = decoded_user['user_id']

        stmt = select(User).where(User.id == user_id)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        stmt = select(Patient).where(Patient.doctor_id == user_id).order_by(Patient.created_at.desc())
        result = db.execute(stmt)
        patients = result.scalars().all()
        
        if not patients:
            return JSONResponse(status_code=200, content={"patients": []})
            
        return JSONResponse(status_code=200, content={"patients": [
            {
                "id": p.id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "phone": p.phone,
                "age": p.age,
                "gender": p.gender.value,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat()
            } for p in patients
        ]})
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": "Error getting patients", "error": str(e)})

@patient_router.patch("/update/{patient_id}",
    response_model=dict,
    status_code=200,
    summary="Update patient details",
    description="""
    Update details of a specific patient
    
    Optional fields (at least one required):
    - first_name: Patient's first name
    - last_name: Patient's last name
    - phone: Valid phone number
    - age: Patient's age  
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
        
        # Check if patient exists
        stmt = select(Patient).where(Patient.id == patient_id)
        result = db.execute(stmt)
        existing_patient = result.scalar_one_or_none()
        
        if not existing_patient:
            return JSONResponse(status_code=404, content={"error": "Patient not found"})
        
        # partial update
        stmt = update(Patient).where(Patient.id == patient_id).values(**patient.model_dump(exclude_unset=True))
        db.execute(stmt)
        return JSONResponse(status_code=200, content={"message": "Patient updated successfully"})
    except SQLAlchemyError as e:
        return JSONResponse(status_code=500, content={"message": "Error updating patient", "error": str(e)})
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
        
        # Check if patient exists and get patient record
        stmt = select(Patient).where(Patient.id == patient_id)
        result = db.execute(stmt)
        existing_patient = result.scalar_one_or_none()
        
        if not existing_patient:
            return JSONResponse(status_code=404, content={"error": "Patient not found"})
            
        # Delete all associated records in a transaction
        try:
            # Delete all x-rays for this patient
            x_ray_stmt = delete(PatientXray).where(PatientXray.patient == patient_id)
            db.execute(x_ray_stmt)

            # Get and delete all labels for patient's predictions
            pred_stmt = select(Prediction).where(Prediction.patient == patient_id)
            result = db.execute(pred_stmt)
            predictions = result.scalars().all()
            
            for prediction in predictions:
                label_stmt = delete(Label).where(Label.prediction_id == prediction.id)
                db.execute(label_stmt)

            # Delete all predictions
            pred_stmt = delete(Prediction).where(Prediction.patient == patient_id)
            db.execute(pred_stmt)
            
            # Finally delete the patient
            patient_stmt = delete(Patient).where(Patient.id == patient_id)
            db.execute(patient_stmt)
            
            return JSONResponse(status_code=200, content={"message": "Patient deleted successfully"})
            
        except SQLAlchemyError as e:
            raise e
            
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
        
        stmt = select(User).where(User.id == current_user)
        result = db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return JSONResponse(status_code=404, content={"error": "User not found"})
        
        stmt = select(Patient).where(Patient.id == patient_id)
        result = db.execute(stmt)
        patient = result.scalar_one_or_none()
        
        if not patient:
            return JSONResponse(status_code=404, content={"error": "Patient not found"})

        # Create uploads directory if it doesn't exist
        os.makedirs("uploads/original", exist_ok=True)
            
        # Extract original file extension
        original_filename = file.filename
        file_extension = os.path.splitext(original_filename)[1].lower()
        
        # If no extension found, default to .jpg
        if not file_extension:
            file_extension = '.jpg'
            
        # Generate UUID filename with extension
        filename = f"{os.urandom(16).hex()}{file_extension}"
        file_path = f"uploads/original/{filename}"
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        xray = PatientXray(patient=patient.id, original_image=file_path)
        db.add(xray)
        
        return JSONResponse(status_code=200, content={"message": "X-ray uploaded successfully"})
    except SQLAlchemyError as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@patient_router.get("/xray/{patient_id}",
    response_model=dict,
    status_code=200,
    summary="Get patient X-ray",
    description="""
    Get all X-ray images for a specific patient
    
    Required parameters:
    - patient_id: UUID of the patient
    """,
    responses={
        200: {"description": "X-ray images retrieved successfully"},
        401: {"description": "Unauthorized - Invalid token"},
        404: {"description": "Patient or user not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_xray(request: Request, patient_id: str, db: Session = Depends(get_db)):
    try:
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Invalid token"})
        
        stmt = select(PatientXray).where(PatientXray.patient == patient_id).order_by(PatientXray.created_at.desc())
        result = db.execute(stmt)
        xrays = result.scalars().all()

        return JSONResponse(status_code=200, content={"xrays": [
            {
                "id": x.id, 
                "original_image": f"{request.base_url}{x.original_image}",
                "annotated_image": f"{request.base_url}{x.annotated_image}" if x.annotated_image else None,
                "prediction_id": x.prediction_id if x.prediction_id else None
            } for x in xrays
        ]})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})