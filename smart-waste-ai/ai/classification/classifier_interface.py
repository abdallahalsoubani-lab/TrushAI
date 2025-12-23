"""
Classifier Interface
====================
Abstract base class defining the contract for fill level classification models.

This interface ensures consistent behavior whether using:
- Mock heuristic-based classifiers (MVP)
- Trained CNN models (production)
- Pre-trained models with fine-tuning
- Ensemble models
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np


class FillLevel(Enum):
    """
    Enumeration of possible fill levels for waste bins.

    Using an Enum ensures type safety and prevents invalid values.
    """
    EMPTY = "EMPTY"
    HALF = "HALF"
    FULL = "FULL"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> 'FillLevel':
        """
        Create FillLevel from string value.

        Args:
            value: String representation (case-insensitive)

        Returns:
            FillLevel enum member

        Raises:
            ValueError: If value is not a valid fill level
        """
        value = value.upper()
        for level in cls:
            if level.value == value:
                return level
        raise ValueError(f"Invalid fill level: {value}")


@dataclass
class ClassificationResult:
    """
    Result of fill level classification.

    Attributes:
        fill_level: Predicted fill level
        confidence: Confidence score (0.0 - 1.0)
        probabilities: Probability distribution over all classes
        metadata: Additional metadata (processing time, features, etc.)
    """
    fill_level: FillLevel
    confidence: float
    probabilities: Dict[FillLevel, float]
    metadata: Optional[Dict] = None

    def __post_init__(self):
        """Validate confidence and probabilities."""
        assert 0.0 <= self.confidence <= 1.0, "Confidence must be in [0, 1]"
        assert all(0.0 <= p <= 1.0 for p in self.probabilities.values()), \
            "All probabilities must be in [0, 1]"
        prob_sum = sum(self.probabilities.values())
        assert 0.99 <= prob_sum <= 1.01, \
            f"Probabilities must sum to 1.0, got {prob_sum}"


class ClassifierInterface(ABC):
    """
    Abstract base class for fill level classifiers.

    All classifier implementations must inherit from this class and
    implement the required methods.
    """

    @abstractmethod
    def load_model(self) -> None:
        """
        Load or initialize the classification model.

        For mock classifiers: Initialize heuristic parameters
        For CNN classifiers: Load model weights from disk
        For pre-trained models: Download and load if not cached

        Raises:
            Exception: If model loading/initialization fails
        """
        pass

    @abstractmethod
    def classify(
        self,
        image: np.ndarray,
        return_probabilities: bool = True
    ) -> ClassificationResult:
        """
        Classify fill level of a trash bin image.

        Args:
            image: Cropped bin image as numpy array (H, W, C) in BGR format
            return_probabilities: Whether to compute full probability distribution

        Returns:
            ClassificationResult with prediction and confidence

        Raises:
            Exception: If classification fails
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict:
        """
        Get information about the classifier.

        Returns:
            Dictionary containing:
            - type: Classifier type (mock/cnn/ensemble)
            - name: Model name
            - input_size: Expected input size
            - classes: List of output classes
        """
        pass

    def is_loaded(self) -> bool:
        """
        Check if classifier is loaded and ready.

        Returns:
            bool: True if classifier is ready
        """
        return hasattr(self, '_loaded') and self._loaded

    def preprocess_image(
        self,
        image: np.ndarray,
        target_size: Optional[Tuple[int, int]] = None
    ) -> np.ndarray:
        """
        Preprocess image for classification.

        Common preprocessing steps:
        - Resize to target size
        - Normalize pixel values
        - Convert color space if needed

        Args:
            image: Input image
            target_size: Target size as (width, height), None to skip resize

        Returns:
            Preprocessed image
        """
        import cv2

        processed = image.copy()

        # Resize if target size specified
        if target_size is not None:
            processed = cv2.resize(processed, target_size)

        return processed

    def validate_input(self, image: np.ndarray) -> None:
        """
        Validate input image format.

        Args:
            image: Input image to validate

        Raises:
            ValueError: If image format is invalid
        """
        if not isinstance(image, np.ndarray):
            raise ValueError("Image must be a numpy array")

        if image.ndim != 3:
            raise ValueError(f"Image must be 3D (H,W,C), got shape {image.shape}")

        if image.shape[2] != 3:
            raise ValueError(f"Image must have 3 channels, got {image.shape[2]}")

        if image.size == 0:
            raise ValueError("Image is empty")


class MockClassifier(ClassifierInterface):
    """
    Base class for mock/heuristic-based classifiers.

    Mock classifiers use simple image analysis techniques to estimate
    fill level without requiring a trained model. Useful for:
    - MVP development
    - Testing pipeline without ML dependencies
    - Baseline comparisons
    """

    def __init__(self):
        """Initialize mock classifier."""
        self._loaded = False

    def load_model(self) -> None:
        """Mock classifiers don't need to load anything."""
        self._loaded = True

    def get_model_info(self) -> dict:
        """Return mock classifier info."""
        return {
            "type": "mock",
            "name": self.__class__.__name__,
            "classes": [level.value for level in FillLevel],
            "description": "Heuristic-based classifier for MVP"
        }


# TODO: Implement CNN-based classifier
# TODO: Add data augmentation for training
# TODO: Add transfer learning from ImageNet models
# TODO: Add model quantization for faster inference
# TODO: Add uncertainty estimation (e.g., Monte Carlo Dropout)
# TODO: Add explainability (Grad-CAM, LIME)
# TODO: Add online learning capability
# TODO: Add A/B testing framework for model comparison
