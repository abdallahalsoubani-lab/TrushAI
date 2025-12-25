"""SAM2 stub integration.

This module provides a placeholder for future segmentation-based refinement.
"""

import logging
from typing import List

import numpy as np

from ai.detection.detector_interface import Detection

logger = logging.getLogger(__name__)


def refine_detections(image: np.ndarray, detections: List[Detection]) -> List[Detection]:
    """Return detections unchanged (stub).

    Args:
        image: Input image (unused)
        detections: List of detections to refine

    Returns:
        Same detections list
    """
    logger.debug("Segmentation enabled (stub). No refinement applied.")
    return detections
