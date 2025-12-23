"""
YOLOv8 Detector Implementation
================================
Concrete implementation of the DetectorInterface using YOLOv8.

YOLOv8 (You Only Look Once v8) is a state-of-the-art real-time object
detection model. This implementation uses the Ultralytics package.

For MVP: Uses pretrained COCO weights
For Production: Fine-tune on custom trash bin dataset

TODO: Create custom dataset with labeled trash bins
TODO: Fine-tune YOLOv8 on custom dataset
TODO: Add TensorRT optimization for production deployment
TODO: Add model ensembling (multiple YOLO models)
"""

import logging
from typing import List, Optional
import numpy as np

from ai.detection.detector_interface import DetectorInterface, Detection
from ai.config import config

# Set up logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


class YOLOv8Detector(DetectorInterface):
    """
    YOLOv8-based object detector for trash bins.

    Uses pretrained COCO weights. The model can detect 80 object classes,
    but we filter for bin-like objects or use all detections with size
    filtering.
    """

    def __init__(
        self,
        model_size: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        device: Optional[str] = None
    ):
        """
        Initialize YOLOv8 detector.

        Args:
            model_size: YOLO model size (n/s/m/l/x), uses config default if None
            confidence_threshold: Confidence threshold, uses config default if None
            device: Device for inference (cpu/cuda), uses config default if None
        """
        self.model_size = model_size or config.YOLO_MODEL_SIZE
        self.confidence_threshold = confidence_threshold or config.YOLO_CONFIDENCE_THRESHOLD
        self.device = device or config.YOLO_DEVICE

        self.model = None
        self.class_names = None

        logger.info(f"Initializing YOLOv8 detector (size={self.model_size}, device={self.device})")

    def load_model(self) -> None:
        """
        Load YOLOv8 model from Ultralytics.

        Downloads pretrained COCO weights on first run.
        Subsequent runs load from cache.
        """
        try:
            from ultralytics import YOLO

            model_name = f"yolov8{self.model_size}.pt"
            logger.info(f"Loading YOLO model: {model_name}")

            # Load model (downloads weights if not cached)
            self.model = YOLO(model_name)

            # Move to specified device
            self.model.to(self.device)

            # Get class names from model
            self.class_names = self.model.names

            logger.info(f"✓ YOLO model loaded successfully")
            logger.info(f"  Device: {self.device}")
            logger.info(f"  Classes: {len(self.class_names)}")

        except ImportError:
            logger.error("Ultralytics package not installed. Run: pip install ultralytics")
            raise

        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    def detect(
        self,
        image: np.ndarray,
        confidence_threshold: Optional[float] = None
    ) -> List[Detection]:
        """
        Detect objects in image using YOLOv8.

        Args:
            image: Input image (H, W, C) in BGR format
            confidence_threshold: Optional threshold override

        Returns:
            List of Detection objects, filtered for trash bins
        """
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load_model() first.")

        conf_thresh = confidence_threshold or self.confidence_threshold

        try:
            # Run YOLO inference
            # verbose=False suppresses per-image logging
            results = self.model.predict(
                image,
                conf=conf_thresh,
                iou=config.YOLO_IOU_THRESHOLD,
                max_det=config.YOLO_MAX_DETECTIONS,
                imgsz=config.YOLO_IMAGE_SIZE,
                verbose=False,
                device=self.device
            )

            # Extract detections from results
            detections = []
            result = results[0]  # Single image inference

            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes.xyxy.cpu().numpy()  # Bounding boxes
                confidences = result.boxes.conf.cpu().numpy()  # Confidence scores
                class_ids = result.boxes.cls.cpu().numpy().astype(int)  # Class IDs

                for box, conf, class_id in zip(boxes, confidences, class_ids):
                    x1, y1, x2, y2 = map(int, box)

                    detection = Detection(
                        bbox=(x1, y1, x2, y2),
                        confidence=float(conf),
                        class_id=int(class_id),
                        class_name=self.class_names[class_id],
                        image_shape=image.shape
                    )

                    detections.append(detection)

            # Filter detections for trash bins
            bin_detections = self._filter_for_bins(detections)

            logger.debug(
                f"Detected {len(detections)} objects, "
                f"{len(bin_detections)} identified as bins"
            )

            return bin_detections

        except Exception as e:
            logger.error(f"Detection failed: {e}")
            raise

    def _filter_for_bins(self, detections: List[Detection]) -> List[Detection]:
        """
        Filter detections to identify trash bins.

        Strategy:
        1. If DETECT_ALL_OBJECTS is False: Filter by specific class IDs
        2. If DETECT_ALL_OBJECTS is True: Filter by size and aspect ratio

        Args:
            detections: All detections from YOLO

        Returns:
            Filtered list containing only bin detections
        """
        if not config.DETECT_ALL_OBJECTS:
            # Filter by specific trash bin classes
            return [
                det for det in detections
                if det.class_id in config.TRASH_BIN_CLASSES
            ]
        else:
            # Filter by geometric properties
            filtered = []

            for det in detections:
                # Check minimum area
                if det.get_bbox_area() < config.MIN_BOX_AREA:
                    continue

                # Check aspect ratio (bins are usually vertical)
                aspect_ratio = det.get_aspect_ratio()
                if aspect_ratio < config.MIN_ASPECT_RATIO:
                    continue
                if aspect_ratio > config.MAX_ASPECT_RATIO:
                    continue

                filtered.append(det)

            return filtered

    def get_model_info(self) -> dict:
        """
        Get YOLO model information.

        Returns:
            Dictionary with model metadata
        """
        return {
            "name": f"YOLOv8{self.model_size}",
            "version": "8",
            "framework": "Ultralytics",
            "classes": list(self.class_names.values()) if self.class_names else [],
            "num_classes": len(self.class_names) if self.class_names else 0,
            "input_size": config.YOLO_IMAGE_SIZE,
            "device": self.device,
            "confidence_threshold": self.confidence_threshold,
        }

    def detect_and_crop_bins(
        self,
        image: np.ndarray,
        confidence_threshold: Optional[float] = None
    ) -> List[tuple[Detection, np.ndarray]]:
        """
        Detect bins and return cropped images.

        Convenience method that combines detection and cropping.

        Args:
            image: Input image
            confidence_threshold: Optional threshold override

        Returns:
            List of (Detection, cropped_image) tuples
        """
        detections = self.detect(image, confidence_threshold)

        results = []
        for det in detections:
            cropped = det.crop_from_image(image)
            results.append((det, cropped))

        return results


# TODO: Implement custom training pipeline
# TODO: Add data augmentation for training:
#       - Random crops, flips, rotations
#       - Color jittering
#       - Mosaic augmentation
# TODO: Add model export to ONNX for cross-platform deployment
# TODO: Add TensorRT optimization for NVIDIA GPUs
# TODO: Add quantization (INT8) for edge devices
# TODO: Add multi-scale testing for better accuracy
# TODO: Add tracking across video frames (DeepSORT/ByteTrack)
# TODO: Add confidence calibration
# TODO: Benchmark against other detectors (Faster R-CNN, EfficientDet)


if __name__ == "__main__":
    """
    Test script for YOLOv8 detector.

    Usage:
        python -m ai.detection.yolo_detector
    """
    import cv2

    print("YOLOv8 Detector Test")
    print("=" * 50)

    # Initialize detector
    detector = YOLOv8Detector()
    detector.load_model()

    # Print model info
    info = detector.get_model_info()
    print(f"\nModel: {info['name']}")
    print(f"Device: {info['device']}")
    print(f"Classes: {info['num_classes']}")

    # Test with a simple image (if available)
    print("\n✓ Detector initialized successfully")
    print("To test detection, provide an image path and run detect()")
