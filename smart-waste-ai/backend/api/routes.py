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
import tempfile
import shutil
import json
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Depends, Query
from fastapi.responses import FileResponse
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
from backend.database.session import get_db, check_db_connection
from backend.services.analysis_service import AnalysisService
from backend.config import config as backend_config
from ai.config import config

# Set up logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


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
            save_visualizations=request.save_visualizations
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
async def analyze_upload(file: UploadFile = File(...)):
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

        # Process based on file type
        if input_type == "video":
            # Use existing video analysis pipeline
            # Process with reduced frames for faster upload analysis
            result = service.analyze_video(
                video_path=temp_file_path,
                frame_skip=3,  # Process every 3 seconds for faster results
                max_frames=30,  # Limit frames for quick analysis
                save_visualizations=False  # Don't save visualizations for uploads
            )

            # Check if any bins were detected
            if result.bins_detected == 0:
                return UploadAnalysisResponse(
                    input_type=input_type,
                    status="NO_BIN_DETECTED",
                    confidence=0.0,
                    bins_detected=0,
                    message="No bins detected in video"
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
                bins_detected=result.bins_detected,
                message="Video analysis complete"
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

            # Generate debug artifacts if DEBUG_MODE is enabled
            debug_artifacts = None
            if config.DEBUG_MODE:
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
# TODO: Add support for multiple file uploads
