"""
Pydantic Schemas for Bin Status API
====================================
Type-safe data models for API requests and responses.

These schemas ensure:
- Input validation
- Output serialization
- API documentation (OpenAPI/Swagger)
- Type safety throughout the application
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime


class FillLevelEnum(str, Enum):
    """
    Fill level enumeration for API responses.

    Using string enum for better JSON serialization.

    Values:
    - EMPTY: Bin is empty
    - HALF: Bin is half full
    - FULL: Bin is full
    - NO_BIN_DETECTED: No bin was detected in the image/video
    - BIN_DETECTED: Bin detected but not tracked/classified
    """
    EMPTY = "EMPTY"
    HALF = "HALF"
    FULL = "FULL"
    NO_BIN_DETECTED = "NO_BIN_DETECTED"
    BIN_DETECTED = "BIN_DETECTED"


class BinStatusResponse(BaseModel):
    """
    Individual bin status information.

    Returned by GET /bins-status endpoint.
    """
    bin_id: str = Field(..., description="Unique bin identifier")
    fill_level: FillLevelEnum = Field(..., description="Current fill level")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Prediction confidence (0-1)"
    )
    location: Optional[Dict[str, int]] = Field(
        None,
        description="Bin location as bounding box {x1, y1, x2, y2}"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="Last update timestamp"
    )
    detection_count: int = Field(
        ...,
        ge=1,
        description="Number of times detected across frames"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "bin_id": "bin_001",
                "fill_level": "HALF",
                "confidence": 0.85,
                "location": {"x1": 100, "y1": 150, "x2": 300, "y2": 500},
                "last_updated": "2025-12-23T10:30:00",
                "detection_count": 5
            }
        }


class BinsStatusListResponse(BaseModel):
    """
    List of all bin statuses.

    Response for GET /bins-status endpoint.
    """
    bins: List[BinStatusResponse] = Field(..., description="List of all bins")
    total_bins: int = Field(..., description="Total number of bins detected")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response generation time"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "bins": [
                    {
                        "bin_id": "bin_001",
                        "fill_level": "HALF",
                        "confidence": 0.85,
                        "location": {"x1": 100, "y1": 150, "x2": 300, "y2": 500},
                        "last_updated": "2025-12-23T10:30:00",
                        "detection_count": 5
                    }
                ],
                "total_bins": 1,
                "timestamp": "2025-12-23T10:30:00"
            }
        }


class VideoAnalysisRequest(BaseModel):
    """
    Request to analyze a video file.

    Body for POST /analyze-video endpoint.
    """
    video_path: str = Field(
        ...,
        description="Path to video file (must exist on server)"
    )
    frame_skip: Optional[int] = Field(
        None,
        ge=1,
        le=30,
        description="Process every Nth second of video"
    )
    max_frames: Optional[int] = Field(
        None,
        ge=1,
        le=1000,
        description="Maximum number of frames to process"
    )
    save_visualizations: Optional[bool] = Field(
        None,
        description="Whether to save result visualizations"
    )
    debug: Optional[bool] = Field(
        None,
        description="Enable debug artifacts and extra logging for this request"
    )

    @validator('video_path')
    def validate_video_path(cls, v):
        """Validate video path format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Video path cannot be empty")
        return v.strip()

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "video_path": "/path/to/video.mp4",
                "frame_skip": 2,
                "max_frames": 50,
                "save_visualizations": True,
                "debug": False
            }
        }


class VideoAnalysisResponse(BaseModel):
    """
    Response from video analysis.

    Returned by POST /analyze-video endpoint.
    """
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status (completed/failed)")
    video_path: str = Field(..., description="Analyzed video path")
    total_frames: int = Field(..., description="Total frames in video")
    processed_frames: int = Field(..., description="Frames actually processed")
    bins_detected: int = Field(..., description="Number of bins detected")
    bins: List[BinStatusResponse] = Field(..., description="Detected bins with status")
    processing_time: float = Field(..., description="Processing time in seconds")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processing metadata"
    )
    frames_analyzed: int = Field(..., description="Number of frames analyzed")
    frame_indices: list[int] = Field(default_factory=list, description="Frame indices analyzed")
    sampling_strategy: str = Field(..., description="Frame sampling strategy used")
    debug_artifacts: Optional[Dict[str, Any]] = Field(
        None,
        description="Debug artifacts (only when debug enabled): frames, annotated, metadata"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "job_id": "job_20251223_103000",
                "status": "completed",
                "video_path": "/path/to/video.mp4",
                "total_frames": 300,
                "processed_frames": 50,
                "bins_detected": 3,
                "bins": [
                    {
                        "bin_id": "bin_001",
                        "fill_level": "HALF",
                        "confidence": 0.85,
                        "location": {"x1": 100, "y1": 150, "x2": 300, "y2": 500},
                        "last_updated": "2025-12-23T10:30:00",
                        "detection_count": 5
                    }
                ],
                "processing_time": 15.3,
                "metadata": {
                    "detector": "YOLOv8n",
                    "classifier": "brightness"
                }
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response.

    Returned when an error occurs.
    """
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Error occurrence time"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "error": "Video not found",
                "detail": "The specified video file does not exist",
                "timestamp": "2025-12-23T10:30:00"
            }
        }


class HealthCheckResponse(BaseModel):
    """
    Health check response.

    Returned by GET /health endpoint.
    """
    status: str = Field(..., description="Service status (healthy/degraded)")
    version: str = Field(..., description="API version")
    models_loaded: bool = Field(..., description="Whether AI models are loaded")
    database_connected: bool = Field(default=False, description="Whether database is connected")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Health check time"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "models_loaded": True,
                "timestamp": "2025-12-23T10:30:00"
            }
        }


class UploadAnalysisResponse(BaseModel):
    """
    Response from file upload analysis.

    Returned by POST /analyze-upload endpoint.
    Simple, summarized result for uploaded videos or images.
    """
    input_type: str = Field(..., description="Type of input (video/image)")
    status: FillLevelEnum = Field(..., description="Overall fill level status")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Prediction confidence (0-1)"
    )
    bins_detected: int = Field(
        default=0,
        description="Number of bins detected (0 if none found)"
    )
    message: Optional[str] = Field(
        None,
        description="Additional information or warnings"
    )
    debug_artifacts: Optional[Dict[str, Any]] = Field(
        None,
        description="Debug artifacts (only when DEBUG_MODE enabled): overlay image, cropped bins, metadata"
    )
    frames_analyzed: Optional[int] = Field(
        None,
        description="Number of frames analyzed (video only)"
    )
    frame_indices: Optional[list[int]] = Field(
        None,
        description="Frame indices analyzed (video only)"
    )
    sampling_strategy: Optional[str] = Field(
        None,
        description="Sampling strategy used (video only)"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "input_type": "video",
                "status": "FULL",
                "confidence": 0.89,
                "bins_detected": 3,
                "message": "Analysis complete",
                "debug_artifacts": {
                    "overlay_image": "data/results/debug/overlay_12345.jpg",
                    "cropped_bins": ["data/results/debug/bin_0_12345.jpg"],
                    "metadata": "data/results/debug/metadata_12345.json"
                }
            }
        }


# TODO: Add pagination for bins list (when dealing with many bins)
# TODO: Add filtering options (by fill level, confidence, etc.)
# TODO: Add sorting options (by confidence, detection count, etc.)
# TODO: Add WebSocket schema for real-time updates
# TODO: Add batch video analysis schema
# TODO: Add historical data schema (fill level over time)
# TODO: Add alert/notification schema (when bin is full)
