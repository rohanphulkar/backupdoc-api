from fastapi import APIRouter, Depends, Request, UploadFile, File
from fastapi.responses import JSONResponse
from db.db import get_db
from .model import Prediction, Label
from sqlalchemy.orm import Session
from .schema import PredictionResponse, LabelResponse
from typing import List
from utils.auth import get_current_user
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
async def get_prediction(prediction_id: str, db: Session = Depends(get_db)):
    try:
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if not prediction:
            return JSONResponse(status_code=404, content={"error": "Prediction not found"})
        
        labels = db.query(Label).filter(Label.prediction_id == prediction_id).all()
        
        prediction_data = {
            "prediction": PredictionResponse.from_orm(prediction),
            "labels": [LabelResponse.from_orm(label) for label in labels]
        }
        
        return prediction_data
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@prediction_router.post("/create-prediction/{xray_id}",
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
        # Validate user authorization
        current_user = get_current_user(request)
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        
        user = db.query(User).filter(User.id == current_user.id).first()
        if not user or str(user.user_type) != "doctor":
            return JSONResponse(status_code=401, content={"error": "Unauthorized - must be a doctor"})
        
        # Validate and get X-ray
        if not xray_id:
            return JSONResponse(status_code=400, content={"error": "X-ray ID is required"})
        
        xray = db.query(PatientXray).filter(PatientXray.id == xray_id).first()
        if not xray:
            return JSONResponse(status_code=400, content={"error": "X-ray not found"})
        
        # Validate image exists
        if not os.path.exists(xray.original_image):
            return JSONResponse(status_code=400, content={"error": "X-ray image file not found"})
            
        # Run prediction model
        try:
            rf = Roboflow(api_key=config("ROBOFLOW_API_KEY"))
            project = rf.workspace().project("stage-1-launch")
            model = project.version(1).model
            
            prediction_result = model.predict(xray.original_image, confidence=40)
            if not prediction_result:
                return JSONResponse(status_code=500, content={"error": "Prediction failed"})
                
            prediction_json = prediction_result.json()
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Model prediction failed: {str(e)}"})

        # Generate annotated image
        try:
            image = cv2.imread(xray.original_image)
            if image is None:
                return JSONResponse(status_code=400, content={"error": "Failed to load image"})

            labels = [item["class"] for item in prediction_json["predictions"]]
            detections = sv.Detections.from_roboflow(prediction_json)
            annotator = sv.BoxAnnotator()
            annotated_image = annotator.annotate(scene=image, detections=detections, labels=labels)

            # Save annotated image
            output_dir = "analyzed"
            os.makedirs(output_dir, exist_ok=True)
            
            filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}.jpeg"
            output_path = os.path.join(output_dir, filename)
            
            annotated_image_pil = Image.fromarray(annotated_image)
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
    summary="Make a report for a prediction",
    description="""
    Make a report for a prediction by its ID
    """,
    responses={
        200: {"description": "Report created successfully"},
        404: {"description": "Prediction not found"},
        500: {"description": "Internal server error"}
    }
)
async def make_report(prediction_id: str, db: Session = Depends(get_db)):
    pass