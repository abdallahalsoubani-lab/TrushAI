"""Detection filtering utilities for inference."""

from dataclasses import replace
from typing import List, Tuple, Dict, Any

from ai.config import config
from ai.detection.detector_interface import Detection


def clamp_bbox(
    bbox: Tuple[int, int, int, int],
    width: int,
    height: int
) -> Tuple[Tuple[int, int, int, int], List[str]]:
    x1, y1, x2, y2 = bbox
    reasons: List[str] = []
    if x1 < 0 or y1 < 0 or x2 >= width or y2 >= height:
        reasons.append("bbox_oob")

    x1c = max(0, min(int(x1), width - 1))
    y1c = max(0, min(int(y1), height - 1))
    x2c = max(0, min(int(x2), width - 1))
    y2c = max(0, min(int(y2), height - 1))

    if x2c <= x1c or y2c <= y1c:
        reasons.append("invalid_bbox_after_clamp")

    return (x1c, y1c, x2c, y2c), reasons


def filter_detections_stage_a(
    detections: List[Detection],
    frame_shape: Tuple[int, int, int],
    effective_conf: float
) -> Tuple[List[Detection], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Stage A filter: class + confidence only (with bbox clamp + validity)."""
    allowed_classes = {name.lower() for name in config.TRASH_BIN_CLASSES}
    h, w = frame_shape[:2]

    kept: List[Detection] = []
    kept_info: List[Dict[str, Any]] = []
    rejected_info: List[Dict[str, Any]] = []

    for det in detections:
        reasons: List[str] = []
        raw_bbox = det.bbox
        clamped_bbox, clamp_reasons = clamp_bbox(raw_bbox, w, h)
        reasons.extend(clamp_reasons)

        class_name = str(det.class_name)
        if class_name.lower() not in allowed_classes:
            reasons.append("wrong_class")

        if det.confidence < effective_conf:
            reasons.append("low_conf")

        info = {
            "class_name": class_name,
            "confidence": float(det.confidence),
            "bbox_raw": list(raw_bbox),
            "bbox_clamped": list(clamped_bbox),
            "reasons": reasons,
        }

        if "invalid_bbox_after_clamp" in reasons:
            rejected_info.append(info)
            continue

        if any(r for r in reasons if r in {"wrong_class", "low_conf"}):
            rejected_info.append(info)
            continue

        clamped_det = replace(det, bbox=clamped_bbox)
        kept.append(clamped_det)
        kept_info.append({**info, "reasons": []})

    kept_class_names = sorted({det.class_name for det in kept})
    stats = {
        "raw_count": len(detections),
        "kept_count": len(kept),
        "filtered_out_count": len(detections) - len(kept),
        "kept_class_names": kept_class_names,
    }

    return kept, kept_info, rejected_info, stats
