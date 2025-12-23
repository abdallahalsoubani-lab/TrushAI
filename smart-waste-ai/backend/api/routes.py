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
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pathlib import Path

from backend.schemas.bin_status import (
    BinStatusResponse,
    BinsStatusListResponse,
    VideoAnalysisRequest,
    VideoAnalysisResponse,
    ErrorResponse,
    HealthCheckResponse
)
from backend.services.inference_service import get_inference_service
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
    description="Check if the API is running and models are loaded"
)
async def health_check():
    """
    Health check endpoint.

    Returns service status and model availability.
    """
    service = get_inference_service()

    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        models_loaded=service.models_loaded
    )


@router.get(
    "/bins-status",
    response_model=BinsStatusListResponse,
    summary="Get All Bin Statuses",
    description="Retrieve status of all detected bins from the most recent analysis"
)
async def get_bins_status():
    """
    Get status of all detected bins.

    Returns data from the most recent video analysis.
    """
    try:
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


# TODO: Add async video processing with job queue
# TODO: Add WebSocket endpoint for real-time progress updates
# TODO: Add pagination for bins list
# TODO: Add filtering (by fill level, confidence threshold)
# TODO: Add sorting (by confidence, detection count)
# TODO: Add batch video analysis endpoint
# TODO: Add video upload endpoint (currently only accepts file paths)
# TODO: Add authentication/authorization
# TODO: Add rate limiting
# TODO: Add metrics endpoint (Prometheus format)
