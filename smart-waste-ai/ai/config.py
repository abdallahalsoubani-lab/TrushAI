"""
AI Pipeline Configuration
==========================
Centralized configuration for all AI components including detection,
classification, and inference parameters.

This module provides a single source of truth for all configurable
parameters across the AI pipeline.
"""

import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """
    Configuration class for the AI pipeline.

    All paths are relative to the project root unless specified as absolute.
    Default values are optimized for MVP development and local execution.
    """

    # ====================================================================
    # PROJECT PATHS
    # ====================================================================
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    VIDEOS_DIR = DATA_DIR / "videos"
    FRAMES_DIR = DATA_DIR / "frames"
    RESULTS_DIR = DATA_DIR / "results"

    # ====================================================================
    # YOLO DETECTION CONFIGURATION
    # ====================================================================

    # YOLOv8 model size: n(ano), s(mall), m(edium), l(arge), x(large)
    # Smaller models are faster but less accurate
    YOLO_MODEL_SIZE: str = "n"  # Using nano for fast MVP inference

    # Custom weights path (default: yolov8n.pt)
    # If not provided and bins.pt exists in project root, use it automatically.
    YOLO_WEIGHTS_PATH: str = os.getenv("YOLO_WEIGHTS_PATH", "").strip()

    # Confidence threshold for detections (0.0 - 1.0)
    # Lower = more detections (higher recall, lower precision)
    # Higher = fewer detections (lower recall, higher precision)
    YOLO_CONFIDENCE_THRESHOLD: float = 0.25

    # IoU (Intersection over Union) threshold for NMS
    # Used to filter overlapping bounding boxes
    YOLO_IOU_THRESHOLD: float = 0.45

    # Maximum number of detections per image
    YOLO_MAX_DETECTIONS: int = 100

    # Device configuration
    # Options: 'cpu', 'cuda', 'mps' (for Mac M1/M2)
    # TODO: Add automatic GPU detection and fallback logic
    YOLO_DEVICE: str = "cpu"

    # Image size for YOLO inference (must be multiple of 32)
    # Larger = slower but more accurate
    # Standard sizes: 320, 416, 512, 640
    YOLO_IMAGE_SIZE: int = 640

    # Classes to detect from COCO dataset
    # Relevant COCO classes for trash/waste:
    # - 39: 'bottle'
    # - 41: 'cup'
    # - 73: 'book' (sometimes used for bins in training)
    # - For demo purposes, we'll also consider 'suitcase' (28) as bins
    # TODO: Fine-tune YOLO on custom trash bin dataset
    # TODO: Add custom trash bin class
    # For custom training: use class name "trash_container"
    TRASH_BIN_CLASSES: list = ["trash_container"]

    # Alternative: Use all objects and filter by aspect ratio/size
    DETECT_ALL_OBJECTS: bool = True  # If True, ignore TRASH_BIN_CLASSES

    # Filtering criteria when DETECT_ALL_OBJECTS is True
    MIN_BOX_AREA: int = 5000  # Minimum pixels for a valid bin detection
    MIN_ASPECT_RATIO: float = 0.3  # Height/Width ratio
    MAX_ASPECT_RATIO: float = 3.0

    # ====================================================================
    # FILL LEVEL CLASSIFICATION CONFIGURATION
    # ====================================================================

    # Fill level categories
    FILL_LEVELS: list = ["EMPTY", "HALF", "FULL"]

    # Mock classifier mode
    # Options: 'random', 'brightness', 'edge_density'
    MOCK_CLASSIFIER_MODE: str = "brightness"

    # Brightness-based thresholds (0-255)
    # Logic: Darker images = more filled (shadows from trash)
    BRIGHTNESS_EMPTY_THRESHOLD: int = 150  # Above this = EMPTY
    BRIGHTNESS_HALF_THRESHOLD: int = 100   # Between this and above = HALF
    # Below BRIGHTNESS_HALF_THRESHOLD = FULL

    # Edge density thresholds (ratio of edge pixels to total pixels)
    # Logic: More edges = more trash items = fuller bin
    EDGE_EMPTY_THRESHOLD: float = 0.05   # Below this = EMPTY
    EDGE_HALF_THRESHOLD: float = 0.15    # Between thresholds = HALF
    # Above EDGE_HALF_THRESHOLD = FULL

    # TODO: Replace with trained CNN model
    # TODO: Add model path configuration
    # CNN_MODEL_PATH: str = "models/fill_classifier_v1.pth"
    # TODO: Add input size for CNN: CNN_INPUT_SIZE: tuple = (224, 224)

    # ====================================================================
    # VIDEO PROCESSING CONFIGURATION
    # ====================================================================

    # Frame extraction rate (extract 1 frame every N seconds)
    FRAME_EXTRACTION_RATE: int = 2  # seconds

    # Maximum frames to process per video (for MVP performance)
    MAX_FRAMES_PER_VIDEO: int = 12

    # Sampling strategy: "fixed_percentages" or "every_n"
    VIDEO_SAMPLING_STRATEGY: str = os.getenv("VIDEO_SAMPLING_STRATEGY", "fixed_percentages")

    # Minimum frames to process before allowing early stop
    EARLY_STOP_MIN_FRAMES: int = int(os.getenv("EARLY_STOP_MIN_FRAMES", "3"))

    # Frame format for saving
    FRAME_FORMAT: str = "jpg"
    FRAME_QUALITY: int = 95  # JPEG quality (0-100)

    # ====================================================================
    # INFERENCE PIPELINE CONFIGURATION
    # ====================================================================

    # Minimum detections of the same bin across frames to consider it valid
    # This helps filter out false positives
    MIN_DETECTIONS_FOR_VALID_BIN: int = 3

    # Voting strategy for aggregating fill levels across frames
    # Options: 'majority', 'conservative', 'latest'
    # - majority: Most common prediction wins
    # - conservative: Choose fullest level among predictions (safety-first)
    # - latest: Use prediction from most recent frame
    VOTING_STRATEGY: str = "majority"

    # IoU threshold for matching bins across frames
    # Bins with IoU > threshold are considered the same bin
    BIN_TRACKING_IOU_THRESHOLD: float = 0.5

    # TODO: Add temporal smoothing with Kalman filter
    # TODO: Add confidence weighting in voting

    # ====================================================================
    # LOGGING CONFIGURATION
    # ====================================================================

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Save detection visualizations for debugging
    SAVE_VISUALIZATIONS: bool = True
    VISUALIZATIONS_DIR = RESULTS_DIR / "visualizations"

    # ====================================================================
    # DEBUG MODE CONFIGURATION
    # ====================================================================

    # Enable debug mode to save detailed artifacts for analysis
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"

    # Debug logging for raw detections (pre-filter)
    DEBUG_LOG_DETECTIONS: bool = os.getenv("DEBUG_LOG_DETECTIONS", "False").lower() == "true"
    DEBUG_DETECTIONS_LIMIT: int = int(os.getenv("DEBUG_DETECTIONS_LIMIT", "10"))

    # Optional confidence override for debug runs (e.g., 0.15)
    DEBUG_CONFIDENCE_OVERRIDE = None
    _debug_conf_raw = os.getenv("DEBUG_CONFIDENCE_OVERRIDE", "").strip()
    if _debug_conf_raw:
        try:
            DEBUG_CONFIDENCE_OVERRIDE = float(_debug_conf_raw)
        except ValueError:
            DEBUG_CONFIDENCE_OVERRIDE = None

    # Number of random frames to save for debug artifacts
    DEBUG_SAVE_FRAME_COUNT: int = int(os.getenv("DEBUG_SAVE_FRAME_COUNT", "3"))

    # Directory for debug artifacts
    DEBUG_OUTPUT_DIR = RESULTS_DIR / "debug"

    # Debug artifacts to save when DEBUG_MODE is enabled:
    # - Overlay images with bounding boxes and labels
    # - Cropped bin images used for classification
    # - JSON metadata with classifier scores and thresholds

    # ====================================================================
    # API CONFIGURATION
    # ====================================================================

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True  # Auto-reload on code changes (dev only)

    # CORS settings for dashboard
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    @classmethod
    def ensure_directories(cls) -> None:
        """
        Create all required directories if they don't exist.
        Should be called during application startup.
        """
        for dir_path in [
            cls.DATA_DIR,
            cls.VIDEOS_DIR,
            cls.FRAMES_DIR,
            cls.RESULTS_DIR,
            cls.VISUALIZATIONS_DIR,
            cls.DEBUG_OUTPUT_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_yolo_model_name(cls) -> str:
        """
        Get the full YOLOv8 model name for loading.

        Returns:
            str: Model name like 'yolov8n.pt'
        """
        return f"yolov8{cls.YOLO_MODEL_SIZE}.pt"

    @classmethod
    def get_yolo_weights_path(cls) -> str:
        """
        Resolve YOLO weights path.

        Priority:
        1) YOLO_WEIGHTS_PATH env override
        2) bins.pt in project root (post-training)
        3) default Ultralytics model name (e.g., yolov8n.pt)
        """
        if cls.YOLO_WEIGHTS_PATH:
            return cls.YOLO_WEIGHTS_PATH

        backend_bins = cls.PROJECT_ROOT / "backend" / "weights" / "bins.pt"
        if backend_bins.exists():
            return str(backend_bins)

        bins_path = cls.PROJECT_ROOT / "bins.pt"
        if bins_path.exists():
            return str(bins_path)

        return cls.get_yolo_model_name()

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        Useful for logging and API responses.

        Returns:
            Dict containing all configuration values
        """
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_") and key.isupper()
        }


# Create a singleton instance
config = Config()


if __name__ == "__main__":
    # Test configuration
    print("AI Pipeline Configuration")
    print("=" * 50)

    config.ensure_directories()
    print(f"✓ Directories created")

    print(f"\nYOLO Model: {config.get_yolo_model_name()}")
    print(f"Device: {config.YOLO_DEVICE}")
    print(f"Confidence Threshold: {config.YOLO_CONFIDENCE_THRESHOLD}")

    print(f"\nClassifier Mode: {config.MOCK_CLASSIFIER_MODE}")
    print(f"Fill Levels: {config.FILL_LEVELS}")

    print(f"\nFrame Extraction Rate: {config.FRAME_EXTRACTION_RATE}s")
    print(f"Voting Strategy: {config.VOTING_STRATEGY}")
