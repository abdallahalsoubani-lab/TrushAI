"""
Detector Interface
==================
Abstract base class defining the contract for all object detection models.

This interface ensures consistent behavior across different detector
implementations (YOLO, Faster R-CNN, SSD, etc.) and makes it easy to
swap detection models without changing the pipeline.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class Detection:
    """
    Represents a single object detection.

    Attributes:
        bbox: Bounding box as (x1, y1, x2, y2) in pixels
        confidence: Detection confidence score (0.0 - 1.0)
        class_id: Detected class ID
        class_name: Human-readable class name
        image_shape: Original image shape as (height, width, channels)
    """
    bbox: Tuple[int, int, int, int]
    confidence: float
    class_id: int
    class_name: str
    image_shape: Tuple[int, int, int]

    def get_bbox_area(self) -> int:
        """Calculate bounding box area in pixels."""
        x1, y1, x2, y2 = self.bbox
        return (x2 - x1) * (y2 - y1)

    def get_aspect_ratio(self) -> float:
        """Calculate bounding box aspect ratio (height/width)."""
        x1, y1, x2, y2 = self.bbox
        width = x2 - x1
        height = y2 - y1
        return height / width if width > 0 else 0.0

    def get_center(self) -> Tuple[int, int]:
        """Get bounding box center point."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def iou(self, other: 'Detection') -> float:
        """
        Calculate Intersection over Union with another detection.

        Args:
            other: Another Detection object

        Returns:
            float: IoU score (0.0 - 1.0)
        """
        x1_1, y1_1, x2_1, y2_1 = self.bbox
        x1_2, y1_2, x2_2, y2_2 = other.bbox

        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)

        if x2_i < x1_i or y2_i < y1_i:
            return 0.0

        intersection = (x2_i - x1_i) * (y2_i - y1_i)

        # Calculate union
        area_1 = self.get_bbox_area()
        area_2 = other.get_bbox_area()
        union = area_1 + area_2 - intersection

        return intersection / union if union > 0 else 0.0

    def crop_from_image(self, image: np.ndarray) -> np.ndarray:
        """
        Crop this detection from the given image.

        Args:
            image: Input image as numpy array

        Returns:
            Cropped image region
        """
        x1, y1, x2, y2 = self.bbox
        return image[y1:y2, x1:x2]


class DetectorInterface(ABC):
    """
    Abstract base class for object detectors.

    All detector implementations must inherit from this class and
    implement the required methods.
    """

    @abstractmethod
    def load_model(self) -> None:
        """
        Load the detection model.

        This method should initialize the model, load weights, and
        prepare it for inference. Should be called once during initialization.

        Raises:
            Exception: If model loading fails
        """
        pass

    @abstractmethod
    def detect(
        self,
        image: np.ndarray,
        confidence_threshold: Optional[float] = None
    ) -> List[Detection]:
        """
        Detect objects in an image.

        Args:
            image: Input image as numpy array (H, W, C) in BGR format
            confidence_threshold: Optional confidence threshold override

        Returns:
            List of Detection objects, sorted by confidence (descending)

        Raises:
            Exception: If detection fails
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.

        Returns:
            Dictionary containing model metadata:
            - name: Model name
            - version: Model version
            - classes: List of detectable class names
            - input_size: Expected input size
        """
        pass

    def is_loaded(self) -> bool:
        """
        Check if model is loaded and ready for inference.

        Returns:
            bool: True if model is loaded
        """
        return hasattr(self, 'model') and self.model is not None

    def visualize_detections(
        self,
        image: np.ndarray,
        detections: List[Detection],
        show_labels: bool = True,
        show_confidence: bool = True
    ) -> np.ndarray:
        """
        Draw bounding boxes on image.

        Args:
            image: Input image
            detections: List of detections to visualize
            show_labels: Whether to show class labels
            show_confidence: Whether to show confidence scores

        Returns:
            Image with drawn bounding boxes
        """
        import cv2

        vis_image = image.copy()

        for det in detections:
            x1, y1, x2, y2 = det.bbox

            # Draw bounding box
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Prepare label
            if show_labels or show_confidence:
                label_parts = []
                if show_labels:
                    label_parts.append(det.class_name)
                if show_confidence:
                    label_parts.append(f"{det.confidence:.2f}")
                label = " ".join(label_parts)

                # Draw label background
                (label_w, label_h), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
                )
                cv2.rectangle(
                    vis_image,
                    (x1, y1 - label_h - 10),
                    (x1 + label_w, y1),
                    (0, 255, 0),
                    -1
                )

                # Draw label text
                cv2.putText(
                    vis_image,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    2
                )

        return vis_image


# TODO: Add support for batch detection
# TODO: Add support for video stream detection
# TODO: Add performance profiling (FPS, latency)
# TODO: Add model warm-up method
# TODO: Add automatic model benchmarking
