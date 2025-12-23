"""
Inference Service
=================
Service layer that bridges the API and AI pipeline.

Responsibilities:
- Initialize and manage AI models
- Process video analysis requests
- Store and retrieve bin status
- Handle errors gracefully
- Provide model information

This service maintains application state and coordinates
between the API layer and AI components.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import uuid

from ai.inference.pipeline import InferencePipeline, BinInstance
from ai.config import config
from backend.schemas.bin_status import (
    BinStatusResponse,
    BinsStatusListResponse,
    VideoAnalysisResponse,
    FillLevelEnum
)

# Set up logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


class InferenceService:
    """
    Service for managing video analysis and bin status.

    This is a singleton service that maintains:
    - Loaded AI models (detector + classifier)
    - Current bin status cache
    - Analysis history
    """

    def __init__(self):
        """Initialize the inference service."""
        self.pipeline: Optional[InferencePipeline] = None
        self.bin_status_cache: Dict[str, BinStatusResponse] = {}
        self.last_analysis_time: Optional[datetime] = None
        self.models_loaded: bool = False

        logger.info("Inference service initialized")

    def initialize_models(self) -> None:
        """
        Load and initialize AI models.

        Should be called during application startup.

        Raises:
            Exception: If model loading fails
        """
        try:
            logger.info("Loading AI models...")
            self.pipeline = InferencePipeline()

            # Ensure directories exist
            config.ensure_directories()

            self.models_loaded = True
            logger.info("✓ AI models loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            self.models_loaded = False
            raise

    def analyze_video(
        self,
        video_path: str,
        frame_skip: Optional[int] = None,
        max_frames: Optional[int] = None,
        save_visualizations: Optional[bool] = None
    ) -> VideoAnalysisResponse:
        """
        Analyze a video and detect trash bins with fill levels.

        Args:
            video_path: Path to video file
            frame_skip: Process every Nth second
            max_frames: Maximum frames to process
            save_visualizations: Whether to save visualizations

        Returns:
            VideoAnalysisResponse with analysis results

        Raises:
            RuntimeError: If models are not loaded
            FileNotFoundError: If video doesn't exist
            Exception: If analysis fails
        """
        if not self.models_loaded or self.pipeline is None:
            raise RuntimeError(
                "Models not loaded. Call initialize_models() first."
            )

        # Generate unique job ID
        job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        logger.info(f"Starting video analysis: {job_id}")
        logger.info(f"  Video: {video_path}")
        logger.info(f"  Frame skip: {frame_skip or 'default'}")
        logger.info(f"  Max frames: {max_frames or 'default'}")

        try:
            # Run inference pipeline
            result = self.pipeline.process_video(
                video_path=video_path,
                frame_skip=frame_skip,
                max_frames=max_frames,
                save_visualizations=save_visualizations
            )

            # Convert bin instances to API response format
            bin_responses = []
            for bin_instance in result.bins:
                bin_response = self._bin_instance_to_response(bin_instance)
                bin_responses.append(bin_response)

                # Update cache
                self.bin_status_cache[bin_response.bin_id] = bin_response

            # Update last analysis time
            self.last_analysis_time = datetime.now()

            logger.info(
                f"✓ Analysis complete: {len(bin_responses)} bins detected "
                f"in {result.processing_time:.2f}s"
            )

            # Build response
            response = VideoAnalysisResponse(
                job_id=job_id,
                status="completed",
                video_path=result.video_path,
                total_frames=result.total_frames,
                processed_frames=result.processed_frames,
                bins_detected=len(bin_responses),
                bins=bin_responses,
                processing_time=result.processing_time,
                metadata=result.metadata
            )

            return response

        except FileNotFoundError as e:
            logger.error(f"Video not found: {video_path}")
            raise

        except Exception as e:
            logger.error(f"Video analysis failed: {e}", exc_info=True)
            raise

    def get_bins_status(self) -> BinsStatusListResponse:
        """
        Get current status of all detected bins.

        Returns data from the most recent analysis.

        Returns:
            BinsStatusListResponse with all bins
        """
        bins = list(self.bin_status_cache.values())

        logger.debug(f"Retrieving bin status: {len(bins)} bins")

        return BinsStatusListResponse(
            bins=bins,
            total_bins=len(bins),
            timestamp=datetime.now()
        )

    def get_bin_by_id(self, bin_id: str) -> Optional[BinStatusResponse]:
        """
        Get status of a specific bin.

        Args:
            bin_id: Bin identifier

        Returns:
            BinStatusResponse if found, None otherwise
        """
        return self.bin_status_cache.get(bin_id)

    def clear_cache(self) -> None:
        """Clear the bin status cache."""
        self.bin_status_cache.clear()
        self.last_analysis_time = None
        logger.info("Bin status cache cleared")

    def get_service_info(self) -> dict:
        """
        Get service information and status.

        Returns:
            Dictionary with service metadata
        """
        return {
            "models_loaded": self.models_loaded,
            "cached_bins": len(self.bin_status_cache),
            "last_analysis": self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            "detector_info": self.pipeline.detector.get_model_info() if self.pipeline else None,
            "classifier_info": self.pipeline.classifier.get_model_info() if self.pipeline else None,
        }

    def _bin_instance_to_response(
        self,
        bin_instance: BinInstance
    ) -> BinStatusResponse:
        """
        Convert BinInstance to API response format.

        Args:
            bin_instance: Bin instance from pipeline

        Returns:
            BinStatusResponse for API
        """
        # Convert fill level to enum
        fill_level = FillLevelEnum(bin_instance.final_fill_level.value)

        # Format bounding box
        location = None
        if bin_instance.final_bbox:
            x1, y1, x2, y2 = bin_instance.final_bbox
            location = {
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2)
            }

        return BinStatusResponse(
            bin_id=bin_instance.bin_id,
            fill_level=fill_level,
            confidence=bin_instance.confidence or 0.0,
            location=location,
            last_updated=datetime.now(),
            detection_count=len(bin_instance.detections)
        )


# Global service instance (singleton pattern)
inference_service = InferenceService()


def get_inference_service() -> InferenceService:
    """
    Get the global inference service instance.

    Returns:
        InferenceService singleton
    """
    return inference_service


# TODO: Add async support for long-running video analysis
# TODO: Add job queue for multiple concurrent requests
# TODO: Add progress tracking for video analysis
# TODO: Add websocket support for real-time updates
# TODO: Add caching strategy with TTL
# TODO: Add database integration for persistent storage
# TODO: Add analytics (bins by status, historical trends)
# TODO: Add export functionality (CSV, JSON)
# TODO: Add notification system (alerts when bins are full)


if __name__ == "__main__":
    """
    Test script for inference service.

    Usage:
        python -m backend.services.inference_service
    """
    print("Inference Service Test")
    print("=" * 50)

    # Initialize service
    service = get_inference_service()

    try:
        service.initialize_models()
        print("\n✓ Models loaded successfully")

        # Print service info
        info = service.get_service_info()
        print(f"\nService Info:")
        print(f"  Models loaded: {info['models_loaded']}")
        print(f"  Cached bins: {info['cached_bins']}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
