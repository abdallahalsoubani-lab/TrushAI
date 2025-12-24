"""
FastAPI Routes
==============
API endpoints for the smart waste monitoring system.

Endpoints:
- GET  /health              - Health check
- GET  /bins-status         - Get all bin statuses
- GET  /bins-status/{id}    - Get specific bin status
- POST /analyze-video       - Analyze a video file
- GET  /service-info        - Get service information
- POST /clear-cache         - Clear bin status cache
"""

import logging
import re
import tempfile
import shutil
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends, Query, Form, Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from pathlib import Path
from sqlalchemy.orm import Session

from backend.schemas.bin_status import (
    BinStatusResponse,
    BinsStatusListResponse,
    VideoAnalysisRequest,
    VideoAnalysisResponse,
    ErrorResponse,
    HealthCheckResponse,
    UploadAnalysisResponse
)
from backend.services.inference_service import get_inference_service
from backend.services import training_service
from backend.database.session import get_db, check_db_connection
from backend.services.analysis_service import AnalysisService
from backend.config import config as backend_config
from ai.config import config
from pydantic import BaseModel

# Set up logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class AnnotationRequest(BaseModel):
    filename: str
    bbox: Dict[str, float]


class PrepareDatasetRequest(BaseModel):
    train_ratio: float = 0.8


class TrainStartRequest(BaseModel):
    model_size: str = "n"
    epochs: int = 50
    imgsz: int = 640
    batch: int = 8
    device: str = "auto"
    project_name: str = "trashbin-train"


class UseModelRequest(BaseModel):
    weights_path: str


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check if the API is running, models are loaded, and database is connected"
)
async def health_check():
    """
    Health check endpoint.

    Returns service status, model availability, and database connectivity.
    """
    service = get_inference_service()
    db_connected = check_db_connection()

    return HealthCheckResponse(
        status="healthy" if (service.models_loaded and db_connected) else "degraded",
        version="1.0.0",
        models_loaded=service.models_loaded,
        database_connected=db_connected
    )


@router.get(
    "/bins-status",
    response_model=BinsStatusListResponse,
    summary="Get All Bin Statuses",
    description="Retrieve status of all detected bins from the most recent analysis"
)
async def get_bins_status(db: Session = Depends(get_db)):
    """
    Get status of all detected bins from the latest analysis.

    Returns data from the most recent analysis in the database.
    If no analyses exist, returns in-memory cache for backward compatibility.
    """
    try:
        # Try to get latest analysis from database
        latest_analysis = AnalysisService.get_latest_analysis(db)

        if latest_analysis and latest_analysis.bin_detections:
            # Build response from database
            bins = []
            for bin_detection in latest_analysis.bin_detections:
                bins.append(BinStatusResponse(
                    bin_id=f"bin_{bin_detection.bin_index:03d}",
                    fill_level=bin_detection.fill_level,
                    confidence=bin_detection.confidence,
                    location={
                        "x1": bin_detection.bbox_x1,
                        "y1": bin_detection.bbox_y1,
                        "x2": bin_detection.bbox_x2,
                        "y2": bin_detection.bbox_y2
                    },
                    last_updated=bin_detection.created_at,
                    detection_count=1  # For database records, count is 1 per detection
                ))

            return BinsStatusListResponse(
                bins=bins,
                total_bins=len(bins),
                timestamp=latest_analysis.completed_at or latest_analysis.started_at
            )

        # Fallback to in-memory cache for backward compatibility
        service = get_inference_service()
        return service.get_bins_status()

    except Exception as e:
        logger.error(f"Error getting bin status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bin status: {str(e)}"
        )


@router.get(
    "/bins-status/{bin_id}",
    response_model=BinStatusResponse,
    summary="Get Specific Bin Status",
    description="Retrieve status of a specific bin by ID",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Bin not found"
        }
    }
)
async def get_bin_status(bin_id: str):
    """
    Get status of a specific bin.

    Args:
        bin_id: Bin identifier (e.g., 'bin_001')

    Returns:
        BinStatusResponse for the specified bin

    Raises:
        404: If bin ID is not found
    """
    try:
        service = get_inference_service()
        bin_status = service.get_bin_by_id(bin_id)

        if bin_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bin not found: {bin_id}"
            )

        return bin_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bin {bin_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bin status: {str(e)}"
        )


@router.post(
    "/analyze-video",
    response_model=VideoAnalysisResponse,
    summary="Analyze Video",
    description="Analyze a video file to detect trash bins and estimate fill levels",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Video file not found"
        },
        500: {
            "model": ErrorResponse,
            "description": "Analysis failed"
        }
    }
)
async def analyze_video(request: VideoAnalysisRequest):
    """
    Analyze a video file for trash bin detection and classification.

    This endpoint:
    1. Validates the video path
    2. Extracts frames from the video
    3. Detects trash bins in each frame
    4. Classifies fill level for each bin
    5. Aggregates results across frames
    6. Returns comprehensive analysis results

    Args:
        request: VideoAnalysisRequest with video path and parameters

    Returns:
        VideoAnalysisResponse with detected bins and their fill levels

    Raises:
        404: If video file doesn't exist
        500: If analysis fails
    """
    try:
        service = get_inference_service()

        # Validate models are loaded
        if not service.models_loaded:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI models not loaded. Service initializing..."
            )

        # Validate video file exists
        video_path = Path(request.video_path)
        if not video_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Video file not found: {request.video_path}"
            )

        # Validate video file extension
        valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        if video_path.suffix.lower() not in valid_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid video format. Supported: {valid_extensions}"
            )

        logger.info(f"API: Analyzing video: {request.video_path}")

        # Run video analysis
        result = service.analyze_video(
            video_path=request.video_path,
            frame_skip=request.frame_skip,
            max_frames=request.max_frames,
            save_visualizations=request.save_visualizations,
            debug=request.debug
        )

        logger.info(
            f"API: Analysis complete - {result.bins_detected} bins detected"
        )

        return result

    except HTTPException:
        raise

    except FileNotFoundError as e:
        logger.error(f"Video not found: {request.video_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video file not found: {request.video_path}"
        )

    except Exception as e:
        logger.error(f"Video analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video analysis failed: {str(e)}"
        )


@router.get(
    "/service-info",
    summary="Get Service Information",
    description="Get information about the inference service and loaded models"
)
async def get_service_info():
    """
    Get service information.

    Returns metadata about the service, loaded models, and cache status.
    """
    try:
        service = get_inference_service()
        return service.get_service_info()

    except Exception as e:
        logger.error(f"Error getting service info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve service info: {str(e)}"
        )


@router.post(
    "/clear-cache",
    summary="Clear Cache",
    description="Clear the bin status cache"
)
async def clear_cache():
    """
    Clear the bin status cache.

    Useful for testing or when starting fresh analysis.
    """
    try:
        service = get_inference_service()
        service.clear_cache()
        return {"message": "Cache cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.post(
    "/analyze-upload",
    response_model=UploadAnalysisResponse,
    summary="Analyze Uploaded File",
    description="Upload and analyze a video or image file to detect bins and estimate fill levels",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid file format or no bins detected"
        },
        500: {
            "model": ErrorResponse,
            "description": "Analysis failed"
        }
    }
)
async def analyze_upload(
    request: Request,
    file: UploadFile = File(...),
    debug: bool = Form(False)
):
    """
    Upload and analyze a video or image file.

    This endpoint:
    1. Accepts multipart/form-data file upload
    2. Validates file type (video: mp4/avi/mov, image: jpg/png)
    3. Saves file to temporary directory
    4. For VIDEO: Runs full inference pipeline and returns summarized result
    5. For IMAGE: Runs detection + classification on single frame
    6. Returns simple status (EMPTY/HALF/FULL) with confidence

    Args:
        file: Uploaded video or image file

    Returns:
        UploadAnalysisResponse with overall status and confidence

    Raises:
        400: If file format is invalid or no bins detected
        500: If analysis fails
    """
    temp_file_path = None

    try:
        service = get_inference_service()

        # Validate models are loaded
        if not service.models_loaded:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI models not loaded. Service initializing..."
            )

        # Validate file format
        filename = file.filename or "upload"
        file_ext = Path(filename).suffix.lower()

        # Supported formats
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        image_extensions = ['.jpg', '.jpeg', '.png']
        all_extensions = video_extensions + image_extensions

        if file_ext not in all_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format. Supported: {all_extensions}"
            )

        # Determine input type
        input_type = "video" if file_ext in video_extensions else "image"

        logger.info(f"API: Analyzing uploaded {input_type}: {filename}")

        # Save uploaded file to temporary directory
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_ext,
            dir=tempfile.gettempdir()
        ) as temp_file:
            # Copy uploaded file content to temp file
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        logger.info(f"API: Saved upload to: {temp_file_path}")

        debug_query = request.query_params.get("debug")
        debug_from_query = False
        if isinstance(debug_query, str):
            debug_from_query = debug_query.strip().lower() in {"1", "true", "yes", "on"}

        debug_enabled = (debug or debug_from_query) or config.DEBUG_MODE
        logger.info(
            f"API: debug_enabled={debug_enabled} debug_form={debug} debug_query={debug_from_query}"
        )

        # Process based on file type
        if input_type == "video":
            # Use existing video analysis pipeline
            # Process with reduced frames for faster upload analysis
            result = service.analyze_video(
                video_path=temp_file_path,
                frame_skip=3,  # Process every 3 seconds for faster results
                max_frames=30,  # Limit frames for quick analysis
                save_visualizations=False,  # Don't save visualizations for uploads
                debug=debug_enabled,
                min_detections=1
            )

            metadata = result.metadata or {}
            detections = metadata.get("detections", [])
            detections_total = 0
            frames_with_detections = 0

            if isinstance(detections, list):
                for d in detections:
                    if isinstance(d, dict):
                        c = int(d.get("count", 0) or 0)
                        detections_total += c
                        if c > 0:
                            frames_with_detections += 1

            unique_bins = int(result.bins_detected or 0)
            effective_bins_detected = unique_bins or (1 if detections_total > 0 else 0)

            metadata["detections_total"] = detections_total
            metadata["frames_with_detections"] = frames_with_detections

            print(
                f"[analyze-upload] unique_bins={unique_bins} detections_total={detections_total} "
                f"frames_with_detections={frames_with_detections} frame_indices={metadata.get('frame_indices')}"
            )

            # Case 1: tracking removed it but we did see detections
            if unique_bins == 0 and detections_total > 0:
                max_conf = 0.5
                if isinstance(detections, list):
                    for frame in detections:
                        items = frame.get("items", []) if isinstance(frame, dict) else []
                        for item in items:
                            if isinstance(item, dict):
                                max_conf = max(max_conf, float(item.get("confidence", 0.0)))
                return UploadAnalysisResponse(
                    input_type=input_type,
                    status="BIN_DETECTED",
                    confidence=round(min(1.0, max_conf), 2),
                    bins_detected=1,
                    message="Bin detected in frames but tracking/filter removed it (min_detections).",
                    debug_artifacts=result.debug_artifacts if debug_enabled else None,
                    frames_analyzed=metadata.get("frames_analyzed"),
                    frame_indices=metadata.get("frame_indices"),
                    sampling_strategy=metadata.get("sampling_strategy"),
                )

            # Case 2: no detections at all
            if unique_bins == 0:
                return UploadAnalysisResponse(
                    input_type=input_type,
                    status="NO_BIN_DETECTED",
                    confidence=0.0,
                    bins_detected=0,
                    message="No bins detected in video",
                    debug_artifacts=result.debug_artifacts if debug_enabled else None,
                    frames_analyzed=result.metadata.get("frames_analyzed"),
                    frame_indices=result.metadata.get("frame_indices"),
                    sampling_strategy=result.metadata.get("sampling_strategy"),
                )

            # Aggregate results to get overall status
            # Use the most conservative (fullest) status found
            from ai.classification.classifier_interface import FillLevel
            level_order = {"EMPTY": 0, "HALF": 1, "FULL": 2}

            bins_by_level = {}
            total_confidence = 0.0

            for bin_response in result.bins:
                level = bin_response.fill_level.value
                if level not in bins_by_level:
                    bins_by_level[level] = []
                bins_by_level[level].append(bin_response.confidence)
                total_confidence += bin_response.confidence

            # Get the fullest level detected (conservative approach)
            if not bins_by_level:
                return UploadAnalysisResponse(
                    input_type=input_type,
                    status="BIN_DETECTED",
                    confidence=0.0,
                    bins_detected=unique_bins,
                    message="Bin detected but no valid classifications to aggregate.",
                    debug_artifacts=result.debug_artifacts if debug_enabled else None,
                    frames_analyzed=result.metadata.get("frames_analyzed"),
                    frame_indices=result.metadata.get("frame_indices"),
                    sampling_strategy=result.metadata.get("sampling_strategy"),
                )

            overall_status = max(bins_by_level.keys(), key=lambda x: level_order[x])

            # Average confidence for that level
            avg_confidence = sum(bins_by_level[overall_status]) / len(bins_by_level[overall_status])

            logger.info(
                f"API: Video analysis complete - {result.bins_detected} bins, "
                f"status: {overall_status}, confidence: {avg_confidence:.2f}"
            )

            return UploadAnalysisResponse(
                input_type=input_type,
                status=overall_status,
                confidence=round(avg_confidence, 2),
                bins_detected=unique_bins,
                message="Video analysis complete",
                debug_artifacts=result.debug_artifacts if debug_enabled else None,
                frames_analyzed=result.metadata.get("frames_analyzed"),
                frame_indices=result.metadata.get("frame_indices"),
                sampling_strategy=result.metadata.get("sampling_strategy"),
            )

        else:  # image
            # For single image: run detection + classification directly
            import cv2
            import numpy as np

            # Read image
            image = cv2.imread(temp_file_path)
            if image is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to read image file"
                )

            # Run detection
            detections = service.pipeline.detector.detect(image)

            if not detections:
                return UploadAnalysisResponse(
                    input_type=input_type,
                    status="NO_BIN_DETECTED",
                    confidence=0.0,
                    bins_detected=0,
                    message="No bins detected in image"
                )

            # Classify each detected bin
            classifications = []
            for detection in detections:
                cropped = detection.crop_from_image(image)
                classification = service.pipeline.classifier.classify(cropped)
                classifications.append(classification)

            # Get overall status (most conservative/fullest)
            from ai.classification.classifier_interface import FillLevel
            level_order = {FillLevel.EMPTY: 0, FillLevel.HALF: 1, FillLevel.FULL: 2}

            fullest = max(classifications, key=lambda c: level_order[c.fill_level])

            logger.info(
                f"API: Image analysis complete - {len(detections)} bins, "
                f"status: {fullest.fill_level.value}, confidence: {fullest.confidence:.2f}"
            )

            # Generate debug artifacts if debug is enabled
            debug_artifacts = None
            if debug_enabled:
                import json
                import uuid
                from datetime import datetime

                # Generate unique ID for this analysis
                analysis_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

                debug_paths = {
                    "overlay_image": None,
                    "cropped_bins": [],
                    "metadata": None
                }

                # Save overlay image with bounding boxes
                overlay_image = image.copy()
                for i, (detection, classification) in enumerate(zip(detections, classifications)):
                    x1, y1, x2, y2 = detection.bbox

                    # Color based on fill level
                    color_map = {
                        FillLevel.EMPTY: (0, 255, 0),    # Green
                        FillLevel.HALF: (0, 165, 255),   # Orange
                        FillLevel.FULL: (0, 0, 255),     # Red
                    }
                    color = color_map.get(classification.fill_level, (255, 255, 255))

                    # Draw bounding box
                    cv2.rectangle(overlay_image, (x1, y1), (x2, y2), color, 2)

                    # Draw label with fill level and confidence
                    label = f"{classification.fill_level.value} ({classification.confidence:.2f})"
                    cv2.putText(
                        overlay_image,
                        label,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        color,
                        2
                    )

                # Save overlay image
                overlay_path = config.DEBUG_OUTPUT_DIR / f"overlay_{analysis_id}.jpg"
                cv2.imwrite(str(overlay_path), overlay_image)
                debug_paths["overlay_image"] = str(overlay_path)

                # Save cropped bin images
                for i, (detection, classification) in enumerate(zip(detections, classifications)):
                    cropped = detection.crop_from_image(image)
                    cropped_path = config.DEBUG_OUTPUT_DIR / f"bin_{i}_{analysis_id}.jpg"
                    cv2.imwrite(str(cropped_path), cropped)
                    debug_paths["cropped_bins"].append(str(cropped_path))

                # Save metadata JSON
                metadata = {
                    "analysis_id": analysis_id,
                    "timestamp": datetime.now().isoformat(),
                    "input_type": input_type,
                    "bins_detected": len(detections),
                    "overall_status": fullest.fill_level.value,
                    "overall_confidence": float(fullest.confidence),
                    "bins": []
                }

                for i, (detection, classification) in enumerate(zip(detections, classifications)):
                    bin_metadata = {
                        "bin_index": i,
                        "bbox": detection.bbox,
                        "detection_confidence": float(detection.confidence),
                        "fill_level": classification.fill_level.value,
                        "classification_confidence": float(classification.confidence),
                        "classifier_metadata": classification.metadata
                    }
                    metadata["bins"].append(bin_metadata)

                metadata_path = config.DEBUG_OUTPUT_DIR / f"metadata_{analysis_id}.json"
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                debug_paths["metadata"] = str(metadata_path)

                debug_artifacts = debug_paths

                logger.info(
                    f"API: Debug artifacts saved - "
                    f"overlay: {overlay_path}, "
                    f"cropped: {len(debug_paths['cropped_bins'])}, "
                    f"metadata: {metadata_path}"
                )

            return UploadAnalysisResponse(
                input_type=input_type,
                status=fullest.fill_level.value,
                confidence=round(fullest.confidence, 2),
                bins_detected=len(detections),
                message="Image analysis complete",
                debug_artifacts=debug_artifacts
            )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Upload analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload analysis failed: {str(e)}"
        )

    finally:
        # Clean up temporary file
        if temp_file_path and Path(temp_file_path).exists():
            try:
                Path(temp_file_path).unlink()
                logger.info(f"API: Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")


@router.post(
    "/analyze-frame",
    summary="Analyze Single Frame",
    description="Analyze a single video frame for bin detections"
)
async def analyze_frame(
    file: UploadFile = File(...),
    save: bool = Query(False),
    session_id: Optional[str] = Query(None)
):
    try:
        service = get_inference_service()
        if not service.models_loaded:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI models not loaded. Service initializing..."
            )

        import cv2
        import numpy as np

        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to decode image"
            )

        detections = service.pipeline.detector.detect(image)
        if not detections:
            return {
                "detections": [],
                "bins_detected": 0,
                "status": "NO_BIN_DETECTED",
                "confidence": 0.0,
                "frame_ts": datetime.now().isoformat(),
            }

        h, w = image.shape[:2]
        results = []
        classifications = []
        for det in detections:
            cropped = det.crop_from_image(image)
            classification = service.pipeline.classifier.classify(cropped)
            classifications.append(classification)
            x1, y1, x2, y2 = det.bbox
            results.append({
                "bbox": [
                    round(x1 / w, 6),
                    round(y1 / h, 6),
                    round(x2 / w, 6),
                    round(y2 / h, 6),
                ],
                "conf": float(det.confidence),
                "label": "trash_container",
                "fill_status": classification.fill_level.value,
                "fill_conf": float(classification.confidence),
                "track_id": None,
            })

        level_order = {"EMPTY": 0, "HALF": 1, "FULL": 2}
        fullest = max(classifications, key=lambda c: level_order[c.fill_level.value])

        response = {
            "detections": results,
            "bins_detected": len(results),
            "status": fullest.fill_level.value,
            "confidence": float(fullest.confidence),
            "frame_ts": datetime.now().isoformat(),
        }

        if save:
            session_id = session_id or datetime.now().strftime("session_%Y%m%d")
            session_dir = backend_config.CAPTURES_DIR / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            capture_id = uuid.uuid4().hex[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            image_name = f"{timestamp}_{capture_id}.jpg"
            metadata_name = f"{timestamp}_{capture_id}.json"
            image_path = session_dir / image_name
            metadata_path = session_dir / metadata_name

            cv2.imwrite(str(image_path), image)
            with open(metadata_path, "w") as f:
                json.dump(response, f, indent=2)

            response["saved"] = {
                "session_id": session_id,
                "capture_id": capture_id,
                "image_file": image_name,
                "metadata_file": metadata_name,
            }

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analyze frame failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analyze frame failed: {str(e)}"
        )


@router.post(
    "/dataset/upload",
    summary="Upload Training Images",
    description="Upload multiple images for training dataset"
)
async def dataset_upload(images: List[UploadFile] = File(...)):
    saved_files = []
    backend_config.TRAINING_IMAGES_RAW.mkdir(parents=True, exist_ok=True)

    for image in images:
        filename = image.filename or "image.jpg"
        suffix = Path(filename).suffix.lower()
        if suffix not in backend_config.ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image format: {suffix}"
            )

        target_path = backend_config.TRAINING_IMAGES_RAW / filename
        if target_path.exists():
            target_path = backend_config.TRAINING_IMAGES_RAW / f"{target_path.stem}_{uuid.uuid4().hex[:6]}{suffix}"

        with open(target_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        saved_files.append({"filename": target_path.name, "path": str(target_path)})

    return {"files": saved_files}


@router.get(
    "/dataset/list",
    summary="List Training Images",
    description="List uploaded images and annotation status"
)
async def dataset_list():
    images = []
    backend_config.TRAINING_IMAGES_RAW.mkdir(parents=True, exist_ok=True)
    backend_config.TRAINING_LABELS_RAW.mkdir(parents=True, exist_ok=True)

    for image_path in sorted(backend_config.TRAINING_IMAGES_RAW.iterdir()):
        if image_path.suffix.lower() not in backend_config.ALLOWED_IMAGE_EXTENSIONS:
            continue
        label_path = backend_config.TRAINING_LABELS_RAW / f"{image_path.stem}.txt"
        annotated = label_path.exists() and label_path.stat().st_size > 0
        images.append({
            "filename": image_path.name,
            "path": str(image_path),
            "annotated": annotated
        })

    return {"images": images}


@router.get(
    "/dataset/image/{filename}",
    summary="Get Training Image",
    description="Serve a training image by filename"
)
async def dataset_image(filename: str):
    image_path = backend_config.TRAINING_IMAGES_RAW / filename
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    return FileResponse(str(image_path))


@router.post(
    "/dataset/annotate",
    summary="Save Annotation",
    description="Save YOLO annotation for a single image"
)
async def dataset_annotate(request: AnnotationRequest):
    image_path = backend_config.TRAINING_IMAGES_RAW / request.filename
    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    bbox = request.bbox
    for key in ["x", "y", "w", "h"]:
        if key not in bbox:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing bbox field: {key}"
            )
        if not (0.0 <= bbox[key] <= 1.0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bbox value for {key}"
            )

    backend_config.TRAINING_LABELS_RAW.mkdir(parents=True, exist_ok=True)
    label_path = backend_config.TRAINING_LABELS_RAW / f"{image_path.stem}.txt"
    with open(label_path, "w") as f:
        f.write(f"0 {bbox['x']} {bbox['y']} {bbox['w']} {bbox['h']}\n")

    return {"status": "saved", "label": str(label_path)}


@router.post(
    "/dataset/prepare",
    summary="Prepare Dataset",
    description="Split train/val and build dataset.yaml"
)
async def dataset_prepare(request: PrepareDatasetRequest):
    import random

    train_ratio = request.train_ratio
    if not (0.5 <= train_ratio <= 0.95):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="train_ratio must be between 0.5 and 0.95"
        )

    images = []
    for p in backend_config.TRAINING_IMAGES_RAW.iterdir():
        if p.suffix.lower() not in backend_config.ALLOWED_IMAGE_EXTENSIONS:
            continue
        label_path = backend_config.TRAINING_LABELS_RAW / f"{p.stem}.txt"
        if not label_path.exists():
            continue
        images.append(p)
    if not images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No annotated images. Annotate first."
        )
    if not images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No images found to prepare dataset"
        )

    random.shuffle(images)
    split_idx = int(len(images) * train_ratio)
    train_images = images[:split_idx]
    val_images = images[split_idx:]

    dataset_dir = backend_config.TRAINING_DATASET_DIR
    if dataset_dir.exists():
        shutil.rmtree(dataset_dir)
    (dataset_dir / "images" / "train").mkdir(parents=True, exist_ok=True)
    (dataset_dir / "images" / "val").mkdir(parents=True, exist_ok=True)
    (dataset_dir / "labels" / "train").mkdir(parents=True, exist_ok=True)
    (dataset_dir / "labels" / "val").mkdir(parents=True, exist_ok=True)

    for image_path in train_images:
        label_path = backend_config.TRAINING_LABELS_RAW / f"{image_path.stem}.txt"
        if not label_path.exists():
            continue
        shutil.copy2(image_path, dataset_dir / "images" / "train" / image_path.name)
        shutil.copy2(label_path, dataset_dir / "labels" / "train" / label_path.name)

    for image_path in val_images:
        label_path = backend_config.TRAINING_LABELS_RAW / f"{image_path.stem}.txt"
        if not label_path.exists():
            continue
        shutil.copy2(image_path, dataset_dir / "images" / "val" / image_path.name)
        shutil.copy2(label_path, dataset_dir / "labels" / "val" / label_path.name)

    dataset_yaml = dataset_dir / "dataset.yaml"
    with open(dataset_yaml, "w") as f:
        f.write(f"path: {dataset_dir}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write("names:\n")
        f.write("  0: trash_container\n")

    return {
        "ok": True,
        "trainCount": len(train_images),
        "valCount": len(val_images),
        "datasetYamlPath": str(dataset_yaml)
    }


@router.post(
    "/train/start",
    summary="Start Training",
    description="Start YOLOv8 training in background"
)
async def train_start(request: TrainStartRequest):
    dataset_yaml = backend_config.TRAINING_DATASET_DIR / "dataset.yaml"
    if not dataset_yaml.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dataset.yaml not found. Run /dataset/prepare first."
        )

    result = training_service.start_training(
        model_size=request.model_size,
        epochs=request.epochs,
        imgsz=request.imgsz,
        batch=request.batch,
        device=request.device,
        project_name=request.project_name,
        dataset_yaml=dataset_yaml,
    )
    if result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    return result


@router.get(
    "/train/status",
    summary="Training Status",
    description="Get current training status and logs"
)
async def train_status():
    return training_service.get_status()


@router.get(
    "/train/artifacts",
    summary="Training Artifacts",
    description="Get paths to training artifacts"
)
async def train_artifacts():
    status = training_service.get_status()
    artifacts = status.get("artifacts", {})
    base_url = "/api/v1/train/download"
    downloads = {
        "best_pt": f"{base_url}/best" if artifacts.get("best_pt") else None,
        "results_png": f"{base_url}/results" if artifacts.get("results_png") else None,
        "confusion_matrix_png": f"{base_url}/confusion" if artifacts.get("confusion_matrix_png") else None,
        "metrics_json": f"{base_url}/metrics" if artifacts.get("metrics_json") else None,
    }
    return {"artifacts": artifacts, "downloads": downloads}


@router.get(
    "/train/download/{artifact}",
    summary="Download Training Artifact",
    description="Download artifacts like best.pt or results.png"
)
async def train_download_artifact(artifact: str):
    status = training_service.get_status()
    artifacts = status.get("artifacts", {})

    mapping = {
        "best": artifacts.get("best_pt"),
        "results": artifacts.get("results_png"),
        "confusion": artifacts.get("confusion_matrix_png"),
        "metrics": artifacts.get("metrics_json"),
    }
    target = mapping.get(artifact)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found"
        )
    return FileResponse(target)


@router.get(
    "/debug-artifacts/{artifact_id}/metadata",
    summary="Get Debug Metadata",
    description="Fetch debug metadata JSON for an artifact id"
)
async def debug_artifacts_metadata(artifact_id: str):
    if not re.match(r"^[A-Za-z0-9_-]+$", artifact_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact id")
    metadata_path = backend_config.DEBUG_OUTPUT_DIR / f"{artifact_id}_debug_metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metadata not found")
    with open(metadata_path, "r") as f:
        data = json.load(f)
    return JSONResponse(content=data)


@router.get(
    "/debug-artifacts/{artifact_id}/frame/{frame_index}",
    summary="Get Debug Frame",
    description="Fetch original debug frame image"
)
async def debug_artifacts_frame(artifact_id: str, frame_index: int):
    if not re.match(r"^[A-Za-z0-9_-]+$", artifact_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact id")
    frame_path = backend_config.DEBUG_OUTPUT_DIR / f"{artifact_id}_frame_{frame_index}.jpg"
    if not frame_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not found")
    return FileResponse(str(frame_path))


@router.get(
    "/debug-artifacts/{artifact_id}/annotated/{frame_index}",
    summary="Get Annotated Debug Frame",
    description="Fetch annotated debug frame image"
)
async def debug_artifacts_annotated(artifact_id: str, frame_index: int):
    if not re.match(r"^[A-Za-z0-9_-]+$", artifact_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid artifact id")
    annotated_path = backend_config.DEBUG_OUTPUT_DIR / f"{artifact_id}_frame_{frame_index}_annotated.jpg"
    if not annotated_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotated frame not found")
    return FileResponse(str(annotated_path))


@router.post(
    "/train/use-model",
    summary="Use Trained Model",
    description="Activate trained weights for inference"
)
async def train_use_model(request: UseModelRequest):
    result = training_service.use_model(request.weights_path)
    if result.get("error"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    return result


@router.get(
    "/analyses",
    summary="Get Analysis History",
    description="Retrieve list of all analyses with pagination and filtering"
)
async def get_analyses(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    status_filter: Optional[str] = Query(None, description="Filter by status (EMPTY/HALF/FULL/NO_BIN_DETECTED)"),
    input_type_filter: Optional[str] = Query(None, description="Filter by input type (image/video)"),
    sort_by: str = Query("started_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db)
):
    """
    Get list of analyses with pagination and filtering.

    Returns:
        List of analyses with metadata
    """
    try:
        analyses, total = AnalysisService.get_analyses(
            db=db,
            skip=skip,
            limit=limit,
            status_filter=status_filter,
            input_type_filter=input_type_filter,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return {
            "analyses": [
                {
                    "id": analysis.id,
                    "input_type": analysis.input_type,
                    "original_filename": analysis.original_filename,
                    "status": analysis.status,
                    "confidence": analysis.confidence,
                    "bins_detected": analysis.bins_detected,
                    "started_at": analysis.started_at.isoformat(),
                    "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
                    "error_message": analysis.error_message,
                    "debug_enabled": analysis.debug_enabled
                }
                for analysis in analyses
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting analyses: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analyses: {str(e)}"
        )


@router.get(
    "/analyses/{analysis_id}",
    summary="Get Analysis Details",
    description="Retrieve detailed information about a specific analysis"
)
async def get_analysis_details(
    analysis_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific analysis.

    Includes bin detections and artifacts.
    """
    try:
        analysis = AnalysisService.get_analysis(db, analysis_id)

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {analysis_id} not found"
            )

        # Build response with all related data
        return {
            "id": analysis.id,
            "input_type": analysis.input_type,
            "original_filename": analysis.original_filename,
            "stored_path": analysis.stored_path,
            "status": analysis.status,
            "confidence": analysis.confidence,
            "bins_detected": analysis.bins_detected,
            "started_at": analysis.started_at.isoformat(),
            "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
            "error_message": analysis.error_message,
            "debug_enabled": analysis.debug_enabled,
            "bin_detections": [
                {
                    "id": det.id,
                    "bin_index": det.bin_index,
                    "frame_index": det.frame_index,
                    "bbox": {
                        "x1": det.bbox_x1,
                        "y1": det.bbox_y1,
                        "x2": det.bbox_x2,
                        "y2": det.bbox_y2
                    },
                    "fill_level": det.fill_level,
                    "confidence": det.confidence,
                    "detection_confidence": det.detection_confidence,
                    "classifier_metadata": json.loads(det.classifier_metadata) if det.classifier_metadata else None
                }
                for det in analysis.bin_detections
            ],
            "artifacts": [
                {
                    "id": art.id,
                    "type": art.type,
                    "path": art.path,
                    "bin_index": art.bin_index,
                    "frame_index": art.frame_index,
                    "file_size": art.file_size,
                    "mime_type": art.mime_type,
                    "created_at": art.created_at.isoformat()
                }
                for art in analysis.artifacts
            ]
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error getting analysis {analysis_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analysis: {str(e)}"
        )


@router.get(
    "/artifacts/{artifact_id}",
    summary="Download Artifact",
    description="Download or serve an artifact file"
)
async def get_artifact(
    artifact_id: int,
    db: Session = Depends(get_db)
):
    """
    Download or serve an artifact file.

    Returns the file for download or display.
    """
    try:
        artifact = AnalysisService.get_artifact(db, artifact_id)

        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found"
            )

        # Construct full path to artifact
        file_path = backend_config.PROJECT_ROOT / artifact.path

        if not file_path.exists():
            logger.error(f"Artifact file not found: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact file not found on disk"
            )

        # Determine media type
        media_type = artifact.mime_type or "application/octet-stream"

        # Return file response
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=file_path.name
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error serving artifact {artifact_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to serve artifact: {str(e)}"
        )


@router.get(
    "/analyses/summary",
    summary="Get Analysis Summary",
    description="Get summary statistics for all analyses"
)
async def get_analysis_summary(db: Session = Depends(get_db)):
    """
    Get summary statistics for all analyses.

    Returns total counts, status breakdown, and latest analysis info.
    """
    try:
        summary = AnalysisService.get_analysis_summary(db)
        return summary

    except Exception as e:
        logger.error(f"Error getting analysis summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analysis summary: {str(e)}"
        )


@router.post(
    "/analyze-batch-upload",
    summary="Batch Image Upload & Analysis",
    description="Upload multiple images at once for batch analysis"
)
async def analyze_batch_upload(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and analyze multiple images in a batch.

    Only accepts image files (jpg, png, webp).
    Processes each image and stores results in database.

    Returns batch summary and individual item results.
    """
    from backend.services.batch_service import BatchService
    import cv2
    import numpy as np

    # Validate file types - only images allowed
    image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    batch_id_str = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # Validate all files first
    for file in files:
        filename = file.filename or "upload"
        file_ext = Path(filename).suffix.lower()

        if file_ext not in image_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format: {filename}. Only images allowed (jpg, png, webp)"
            )

    logger.info(f"Starting batch upload {batch_id_str} with {len(files)} files")

    try:
        service = get_inference_service()

        # Validate models are loaded
        if not service.models_loaded:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI models not loaded. Service initializing..."
            )

        # Create batch record
        batch = BatchService.create_batch(db, batch_id_str, len(files))

        # Create batch directory
        batch_dir = backend_config.ANALYSIS_STORAGE_DIR / batch_id_str
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Process each file
        items_summary = []
        status_counts = {"EMPTY": 0, "HALF": 0, "FULL": 0, "NO_BIN_DETECTED": 0}

        for idx, file in enumerate(files):
            temp_file_path = None

            try:
                filename = file.filename or f"image_{idx}.jpg"
                file_ext = Path(filename).suffix.lower()

                # Save uploaded file to batch directory
                stored_filename = f"{idx:04d}_{filename}"
                stored_path = batch_dir / stored_filename
                relative_path = str(stored_path.relative_to(backend_config.PROJECT_ROOT))

                with open(stored_path, 'wb') as f:
                    shutil.copyfileobj(file.file, f)

                # Create batch item record
                item = BatchService.create_batch_item(
                    db, batch.id, filename, relative_path
                )

                # Read and analyze image
                image = cv2.imread(str(stored_path))
                if image is None:
                    BatchService.update_batch_item_result(
                        db, item.id, "NO_BIN_DETECTED", 0.0, 0,
                        error_message="Failed to read image"
                    )
                    items_summary.append({
                        "id": item.id,
                        "filename": filename,
                        "status": "NO_BIN_DETECTED",
                        "error": "Failed to read image"
                    })
                    continue

                # Run detection
                detections = service.pipeline.detector.detect(image)

                if not detections:
                    BatchService.update_batch_item_result(
                        db, item.id, "NO_BIN_DETECTED", 0.0, 0
                    )
                    status_counts["NO_BIN_DETECTED"] += 1
                    items_summary.append({
                        "id": item.id,
                        "filename": filename,
                        "status": "NO_BIN_DETECTED",
                        "confidence": 0.0,
                        "bins_detected": 0
                    })
                    continue

                # Classify each detected bin
                classifications = []
                for detection in detections:
                    cropped = detection.crop_from_image(image)
                    classification = service.pipeline.classifier.classify(cropped)
                    classifications.append(classification)

                # Get overall status (most conservative/fullest)
                from ai.classification.classifier_interface import FillLevel
                level_order = {FillLevel.EMPTY: 0, FillLevel.HALF: 1, FillLevel.FULL: 2}
                fullest = max(classifications, key=lambda c: level_order[c.fill_level])

                # Update item with results
                BatchService.update_batch_item_result(
                    db, item.id,
                    fullest.fill_level.value,
                    fullest.confidence,
                    len(detections)
                )

                # Update status counts
                status_counts[fullest.fill_level.value] += 1

                # Save debug artifacts if enabled
                if backend_config.DEBUG_MODE:
                    # Save overlay image
                    overlay_image = image.copy()
                    for i, (detection, classification) in enumerate(zip(detections, classifications)):
                        x1, y1, x2, y2 = detection.bbox
                        color_map = {
                            FillLevel.EMPTY: (0, 255, 0),
                            FillLevel.HALF: (0, 165, 255),
                            FillLevel.FULL: (0, 0, 255),
                        }
                        color = color_map.get(classification.fill_level, (255, 255, 255))
                        cv2.rectangle(overlay_image, (x1, y1), (x2, y2), color, 2)
                        label = f"{classification.fill_level.value} ({classification.confidence:.2f})"
                        cv2.putText(overlay_image, label, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                    overlay_filename = f"overlay_{idx:04d}.jpg"
                    overlay_path = batch_dir / overlay_filename
                    cv2.imwrite(str(overlay_path), overlay_image)

                    BatchService.add_batch_item_artifact(
                        db, item.id, "overlay_image",
                        str(overlay_path.relative_to(backend_config.PROJECT_ROOT)),
                        mime_type="image/jpeg"
                    )

                # Add to summary
                items_summary.append({
                    "id": item.id,
                    "filename": filename,
                    "status": fullest.fill_level.value,
                    "confidence": round(fullest.confidence, 2),
                    "bins_detected": len(detections)
                })

                logger.info(f"Processed {filename}: {fullest.fill_level.value} ({len(detections)} bins)")

            except Exception as e:
                logger.error(f"Error processing {filename}: {e}", exc_info=True)
                if 'item' in locals():
                    BatchService.update_batch_item_result(
                        db, item.id, "NO_BIN_DETECTED", 0.0, 0,
                        error_message=str(e)
                    )
                items_summary.append({
                    "id": item.id if 'item' in locals() else None,
                    "filename": filename,
                    "status": "ERROR",
                    "error": str(e)
                })

        # Update batch with final status
        BatchService.update_batch_status(
            db, batch.id, "completed", status_counts
        )

        logger.info(f"Batch {batch_id_str} completed: {status_counts}")

        return {
            "batch_id": batch_id_str,
            "batch_db_id": batch.id,
            "total_files": len(files),
            "status_counts": status_counts,
            "items": items_summary
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Batch upload failed: {e}", exc_info=True)
        if 'batch' in locals():
            BatchService.update_batch_status(
                db, batch.id, "failed",
                error_message=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch upload failed: {str(e)}"
        )


@router.get(
    "/batches",
    summary="Get Batch Upload History",
    description="Retrieve list of all batch uploads with pagination"
)
async def get_batches(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
    status_filter: Optional[str] = Query(None, description="Filter by processing status"),
    db: Session = Depends(get_db)
):
    """Get list of batch uploads with pagination and filtering."""
    from backend.services.batch_service import BatchService

    try:
        batches, total = BatchService.get_batches(
            db=db,
            skip=skip,
            limit=limit,
            processing_status_filter=status_filter
        )

        return {
            "batches": [
                {
                    "id": batch.id,
                    "batch_id": batch.batch_id,
                    "total_files": batch.total_files,
                    "status_counts": json.loads(batch.status_counts) if batch.status_counts else {},
                    "processing_status": batch.processing_status,
                    "created_at": batch.created_at.isoformat(),
                    "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
                    "failed_count": batch.failed_count
                }
                for batch in batches
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting batches: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve batches: {str(e)}"
        )


@router.get(
    "/batches/{batch_id}",
    summary="Get Batch Details",
    description="Retrieve detailed information about a specific batch"
)
async def get_batch_details(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific batch."""
    from backend.services.batch_service import BatchService

    try:
        batch = BatchService.get_batch(db, batch_id)

        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch {batch_id} not found"
            )

        return {
            "id": batch.id,
            "batch_id": batch.batch_id,
            "total_files": batch.total_files,
            "status_counts": json.loads(batch.status_counts) if batch.status_counts else {},
            "processing_status": batch.processing_status,
            "created_at": batch.created_at.isoformat(),
            "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            "failed_count": batch.failed_count,
            "error_message": batch.error_message
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error getting batch {batch_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve batch: {str(e)}"
        )


@router.get(
    "/batches/{batch_id}/items",
    summary="Get Batch Items",
    description="Retrieve all items (images) in a batch"
)
async def get_batch_items(
    batch_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get all items for a specific batch."""
    from backend.services.batch_service import BatchService

    try:
        items, total = BatchService.get_batch_items(db, batch_id, skip, limit)

        return {
            "items": [
                {
                    "id": item.id,
                    "batch_id": item.batch_id,
                    "filename": item.original_filename,
                    "status": item.status,
                    "confidence": item.confidence,
                    "bins_detected": item.bins_detected,
                    "processing_status": item.processing_status,
                    "created_at": item.created_at.isoformat(),
                    "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                    "error_message": item.error_message,
                    "artifact_count": len(item.artifacts)
                }
                for item in items
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error getting batch items for {batch_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve batch items: {str(e)}"
        )


@router.get(
    "/batch-items/{item_id}",
    summary="Get Batch Item Details",
    description="Retrieve detailed information about a specific batch item"
)
async def get_batch_item_details(
    item_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific batch item."""
    from backend.services.batch_service import BatchService

    try:
        item = BatchService.get_batch_item(db, item_id)

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch item {item_id} not found"
            )

        return {
            "id": item.id,
            "batch_id": item.batch_id,
            "filename": item.original_filename,
            "stored_path": item.stored_path,
            "status": item.status,
            "confidence": item.confidence,
            "bins_detected": item.bins_detected,
            "processing_status": item.processing_status,
            "created_at": item.created_at.isoformat(),
            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
            "error_message": item.error_message,
            "artifacts": [
                {
                    "id": art.id,
                    "type": art.type,
                    "path": art.path,
                    "bin_index": art.bin_index,
                    "file_size": art.file_size,
                    "mime_type": art.mime_type,
                    "created_at": art.created_at.isoformat()
                }
                for art in item.artifacts
            ]
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error getting batch item {item_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve batch item: {str(e)}"
        )


# TODO: Add async video processing with job queue
# TODO: Add WebSocket endpoint for real-time progress updates
# TODO: Add pagination for bins list
# TODO: Add filtering (by fill level, confidence threshold)
# TODO: Add sorting (by confidence, detection count)
# TODO: Add batch video analysis endpoint
# TODO: Add authentication/authorization
# TODO: Add rate limiting
# TODO: Add metrics endpoint (Prometheus format)
# TODO: Add file size limits for uploads
# TODO: Add virus scanning for uploaded files
