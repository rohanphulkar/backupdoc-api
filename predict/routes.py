from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import JSONResponse
from db.db import get_db
from .model import Prediction, Label
from sqlalchemy.orm import Session
from .schema import PredictionResponse, LabelResponse
from typing import List
from utils.auth import verify_token
from utils.prediction import calculate_class_percentage
from auth.model import User
from patients.model import Patient
from roboflow import Roboflow
import supervision as sv
from PIL import Image
import cv2
import random, os
import datetime
from decouple import config
from patients.model import PatientXray
from utils.report import report_generate, create_dental_radiology_report, send_email_with_attachment
from dateutil.utils import today

prediction_router = APIRouter()

@prediction_router.get("/get-predictions/{patient_id}",
    response_model=List[PredictionResponse],
    status_code=200,
    summary="Get patient predictions",
    description="""
    Get all predictions for a specific patient
    
    Required parameters:
    - patient_id: UUID of the patient
    
    Returns list of predictions with:
    - id: Prediction UUID
    - patient: Patient UUID
    - original_image: Path to original X-ray
    - predicted_image: Path to annotated prediction image
    - is_annotated: Whether prediction has been annotated
    - created_at: Creation timestamp
    - updated_at: Last update timestamp
    """,
    responses={
        200: {"description": "List of predictions retrieved successfully"},
        500: {"description": "Internal server error"}
    }
)
async def get_predictions(patient_id: str, db: Session = Depends(get_db)):
    try:        
        predictions = db.query(Prediction).filter(Prediction.patient == patient_id).all()
        return predictions
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@prediction_router.get("/get-prediction/{prediction_id}",
    response_model=dict,
    status_code=200,
    summary="Get prediction details",
    description="""
    Get detailed information about a specific prediction    
    
    Required parameters:
    - prediction_id: UUID of the prediction
    
    Required headers:
    - Authorization: Bearer token from login
    
    Returns prediction details with:
    - prediction: Full prediction object
    - labels: List of detected labels with confidence scores
    """,
    responses={
        200: {"description": "Prediction details retrieved successfully"},
        404: {"description": "Prediction not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_prediction(request: Request, prediction_id: str, db: Session = Depends(get_db)):
    try:
        decoded_token = verify_token(request)

        user_id = decoded_token.get("user_id") if decoded_token else None
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user or str(user.user_type) != "doctor":
            return JSONResponse(status_code=401, content={"error": "Unauthorized - must be a doctor"})
        
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if not prediction:
            return JSONResponse(status_code=404, content={"error": "Prediction not found"})
        
        prediction.original_image = f"{request.base_url}{prediction.original_image}"
        prediction.predicted_image = f"{request.base_url}{prediction.predicted_image}"
        
        labels = db.query(Label).filter(Label.prediction_id == prediction_id).all()
        
        prediction_data = {
            "prediction": PredictionResponse.from_orm(prediction),
            "labels": [LabelResponse.from_orm(label) for label in labels]
        }
        
        return prediction_data
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@prediction_router.get("/create-prediction/{xray_id}",
    response_model=dict,
    status_code=200,
    summary="Create new prediction",
    description="""
    Create a new prediction for an X-ray image
    
    Required parameters:
    - xray_id: UUID of the X-ray image
    
    Required headers:
    - Authorization: Bearer token from login
    
    Process:
    1. Validates user authorization
    2. Loads X-ray image
    3. Runs prediction model
    4. Generates annotated image
    5. Saves prediction results
    """,
    responses={
        200: {"description": "Prediction created successfully"},
        400: {"description": "Invalid X-ray ID or image"},
        401: {"description": "Unauthorized - Invalid token or not a doctor"},
        500: {"description": "Internal server error"}
    }
)
async def create_prediction(request: Request, xray_id: str, db: Session = Depends(get_db)):
    try:
        decoded_token = verify_token(request)

        user_id = decoded_token.get("user_id") if decoded_token else None
        
        user = db.query(User).filter(User.id == user_id).first()

        if not user or str(user.user_type) != "doctor" :
            return JSONResponse(status_code=401, content={"error": "Unauthorized - must be a doctor"})
        
        # Validate and get X-ray
        if not xray_id:
            return JSONResponse(status_code=400, content={"error": "X-ray ID is required"})
        
        xray = db.query(PatientXray).filter(PatientXray.id == xray_id).first()
        if not xray:
            return JSONResponse(status_code=400, content={"error": "X-ray not found"})
        
        # Validate image exists
        if not os.path.exists(str(xray.original_image)):
            return JSONResponse(status_code=400, content={"error": "X-ray image file not found"})
            
        # Run prediction model
        try:
            rf = Roboflow(api_key=config("ROBOFLOW_API_KEY"))
            project = rf.workspace().project("stage-1-launch")
            model = project.version(1).model
            
            prediction_result = model.predict(str(xray.original_image), confidence=1)
            if not prediction_result:
                return JSONResponse(status_code=500, content={"error": "Prediction failed"})
                
            prediction_json = prediction_result.json()
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Model prediction failed: {str(e)}"})

        # Generate annotated image
        try:
            image = cv2.imread(str(xray.original_image))
            if image is None:
                return JSONResponse(status_code=400, content={"error": "Failed to load image"})

            labels = [item["class"] for item in prediction_json["predictions"]]
            detections = sv.Detections.from_inference(prediction_json)
            
            label_annotator = sv.LabelAnnotator()
            mask_annotator = sv.MaskAnnotator()
            
            annotated_image = mask_annotator.annotate(scene=image, detections=detections)
            annotated_image = label_annotator.annotate(scene=annotated_image, detections=detections, labels=labels)

            # Save annotated image
            annotated_image_pil = Image.fromarray(annotated_image)
            current_datetime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            random_number = random.randint(1000, 9999)
            random_filename = f"{current_datetime}-{random_number}.jpeg"

            output_dir = os.path.join("uploads", "analyzed")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, random_filename)
            
            annotated_image_pil.save(output_path, optimize=True, quality=85)
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Image annotation failed: {str(e)}"})

        # Save prediction results
        try:
            class_percentages = calculate_class_percentage(prediction_json)
            
            prediction = Prediction(
                patient=xray.patient,
                original_image=xray.original_image,
                predicted_image=output_path,
                is_annotated=True
            )
            db.add(prediction)
            db.commit()

            # Bulk insert labels for better performance
            labels = [
                Label(
                    prediction_id=prediction.id,
                    name=class_name,
                    percentage=percentage
                )
                for class_name, percentage in class_percentages.items()
            ]
            db.bulk_save_objects(labels)
            db.commit()

            # Update patient xray with annotated image
            xray.annotated_image = output_path
            xray.prediction_id = str(prediction.id)
            db.commit()

            user.credits -= 1
            db.commit()
            
            return JSONResponse(status_code=200, content={
                "message": "Prediction created successfully",
                "prediction_id": prediction.id
            })
            
        except Exception as e:
            db.rollback()
            return JSONResponse(status_code=500, content={"error": f"Database operation failed: {str(e)}"})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    

@prediction_router.delete("/delete-prediction/{prediction_id}",
    status_code=200,
    summary="Delete a prediction",
    description="""
    Delete a prediction by its ID
    """,
    responses={
        200: {"description": "Prediction deleted successfully"},
        404: {"description": "Prediction not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_prediction(prediction_id: str, db: Session = Depends(get_db)):
    try:
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if not prediction:
            return JSONResponse(status_code=404, content={"error": "Prediction not found"})
        
        db.delete(prediction)
        db.commit()
        
        return JSONResponse(status_code=200, content={"message": "Prediction deleted successfully"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@prediction_router.get("/make-report/{prediction_id}",
    status_code=200,
    summary="Generate dental radiology report",
    description="""
    Generate a detailed dental radiology report for a prediction, including analysis and recommendations.
    The report will be emailed to the doctor.
    
    Required:
    - prediction_id: UUID of the prediction
    - Authorization header with doctor's token
    """,
    responses={
        200: {"description": "Report generated and emailed successfully"},
        401: {"description": "Unauthorized - must be a doctor"},
        404: {"description": "Prediction or patient not found"},
        500: {"description": "Internal server error"}
    }
)
async def make_report(request: Request, prediction_id: str, db: Session = Depends(get_db)):
    try:
        # Verify doctor authorization
        decoded_token = verify_token(request)
        if not decoded_token:
            return JSONResponse(status_code=401, content={"error": "Invalid or missing token"})
            
        user = db.query(User).filter(
            User.id == decoded_token.get("user_id"),
            User.user_type == "doctor"
        ).first()
        
        if not user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized - must be a doctor"})

        # Get prediction with labels
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if not prediction:
            return JSONResponse(status_code=404, content={"error": "Prediction not found"})

        # Get patient details
        patient = db.query(Patient).filter(Patient.id == prediction.patient).first()
        if not patient:
            return JSONResponse(status_code=404, content={"error": "Patient not found"})

        # Get prediction labels and format findings
        labels = db.query(Label).filter(Label.prediction_id == prediction_id).all()
        if not labels:
            return JSONResponse(status_code=404, content={"error": "No findings available for this prediction"})

        findings = "\n".join([
            f"{label.name}: {label.percentage:.1f}% confidence" 
            for label in labels
        ])

        # Generate report content
        try:
            report_content = report_generate(
                prediction_str=findings,
                doctor_name=user.name,
                doctor_email=user.email,
                doctor_phone=user.phone,
                patient_name=f"{patient.first_name} {patient.last_name}",
                patient_age=patient.age,
                patient_gender=patient.gender,
                patient_phone=patient.phone,
                date=today().strftime("%Y-%m-%d")
            )
            
            if isinstance(report_content, JSONResponse):
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to generate report content"}
                )

            # Create PDF report
            report_pdf = create_dental_radiology_report(
                patient_name=f"{patient.first_name} {patient.last_name}",
                report_content=report_content
            )
            
            if not report_pdf:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to create PDF report"}
                )

            # Send email with report
            email_sent = send_email_with_attachment(
                to_email=user.email,
                patient_name=f"{patient.first_name} {patient.last_name}",
                pdf_file_path=report_pdf
            )

            if not email_sent:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to send email with report"}
                )

            return JSONResponse(
                status_code=200,
                content={
                    "message": "Report generated and sent successfully",
                    "email": user.email
                }
            )

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"Report generation failed: {str(e)}"}
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Unexpected error: {str(e)}"}
        )