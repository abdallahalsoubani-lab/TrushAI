"""
Inference Pipeline
==================
Orchestrates the complete video analysis workflow:
1. Extract frames from video
2. Detect trash bins in each frame
3. Classify fill level for each detected bin
4. Track bins across frames
5. Aggregate predictions using voting
6. Generate final results

This is the main entry point for the AI system.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import cv2
import numpy as np

from ai.detection.yolo_detector import YOLOv8Detector
from ai.detection.detector_interface import Detection
from ai.classification.fill_level_classifier import get_classifier
from ai.classification.classifier_interface import FillLevel, ClassificationResult
from ai.config import config
from ai.inference.filters import filter_detections_stage_a

# Set up logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


@dataclass
class BinInstance:
    """
    Represents a tracked bin across multiple frames.

    Attributes:
        bin_id: Unique identifier for this bin
        detections: List of detections across frames
        classifications: List of classification results
        frame_indices: Frame numbers where this bin was detected
        final_bbox: Representative bounding box (average position)
        final_fill_level: Aggregated fill level prediction
        confidence: Aggregated confidence score
    """
    bin_id: str
    detections: List[Detection] = field(default_factory=list)
    classifications: List[ClassificationResult] = field(default_factory=list)
    frame_indices: List[int] = field(default_factory=list)
    final_bbox: Optional[Tuple[int, int, int, int]] = None
    final_fill_level: Optional[FillLevel] = None
    confidence: Optional[float] = None


@dataclass
class PipelineResult:
    """
    Complete pipeline output for a video.

    Attributes:
        video_path: Path to analyzed video
        total_frames: Total frames in video
        processed_frames: Number of frames actually processed
        bins: List of detected and classified bins
        processing_time: Total processing time in seconds
        metadata: Additional information
    """
    video_path: str
    total_frames: int
    processed_frames: int
    bins: List[BinInstance]
    processing_time: float
    metadata: Dict = field(default_factory=dict)
    debug_artifacts: Optional[Dict] = None


class InferencePipeline:
    """
    Main pipeline for video analysis.

    Coordinates detection, classification, tracking, and aggregation.
    """

    def __init__(
        self,
        detector: Optional[YOLOv8Detector] = None,
        classifier_mode: Optional[str] = None
    ):
        """
        Initialize inference pipeline.

        Args:
            detector: Object detector (creates default if None)
            classifier_mode: Classifier mode (uses config default if None)
        """
        self.detector = detector or YOLOv8Detector()
        self.classifier = get_classifier(classifier_mode)

        # Ensure models are loaded
        if not self.detector.is_loaded():
            logger.info("Loading detector...")
            self.detector.load_model()

        if not self.classifier.is_loaded():
            logger.info("Loading classifier...")
            self.classifier.load_model()

        logger.info("Inference pipeline initialized")

    def process_video(
        self,
        video_path: str,
        frame_skip: Optional[int] = None,
        max_frames: Optional[int] = None,
        save_visualizations: bool = None,
        debug: Optional[bool] = None,
        debug_confidence_override: Optional[float] = None,
        sampling_strategy: Optional[str] = None,
        min_detections: Optional[int] = None
    ) -> PipelineResult:
        """
        Process entire video and return bin status.

        Args:
            video_path: Path to input video file
            frame_skip: Process every Nth frame (uses config default if None)
            max_frames: Maximum frames to process (uses config default if None)
            save_visualizations: Whether to save visualizations

        Returns:
            PipelineResult with all detected bins and their status

        Raises:
            FileNotFoundError: If video file doesn't exist
            Exception: If video processing fails
        """
        import time

        start_time = time.time()

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        logger.info(f"Processing video: {video_path.name}")

        debug_enabled = debug if debug is not None else config.DEBUG_MODE
        if debug_enabled:
            logger.info("Debug mode enabled for this analysis")

        confidence_override = debug_confidence_override
        if confidence_override is None and config.DEBUG_CONFIDENCE_OVERRIDE is not None:
            confidence_override = config.DEBUG_CONFIDENCE_OVERRIDE
        if confidence_override is None and debug_enabled:
            confidence_override = 0.15
        effective_conf = max(
            confidence_override if confidence_override is not None else config.YOLO_CONFIDENCE_THRESHOLD,
            config.YOLO_CONFIDENCE_THRESHOLD
        )

        sampling_strategy = sampling_strategy or config.VIDEO_SAMPLING_STRATEGY
        min_detections = min_detections or config.MIN_DETECTIONS_FOR_VALID_BIN
        # Extract and process frames
        frames, frame_info, frame_indices = self._extract_frames(
            video_path,
            frame_skip=frame_skip,
            max_frames=max_frames,
            sampling_strategy=sampling_strategy
        )

        logger.info(
            "Extracted %s frames for processing (fps=%s, total_frames=%s, first_frame=%s)",
            len(frames),
            frame_info.get("fps"),
            frame_info.get("total_frames"),
            frame_info.get("first_frame_size")
        )

        # Process each frame
        all_detections = []
        frame_stats_list = []
        analyzed_indices = []
        stopped_early = False
        for i, frame in enumerate(frames):
            frame_idx = frame_indices[i]
            frame_detections, frame_stats = self._process_frame(
                frame,
                frame_idx,
                confidence_override=effective_conf,
                log_detections=debug_enabled
            )
            all_detections.append(frame_detections)
            frame_stats_list.append(frame_stats)
            analyzed_indices.append(frame_idx)

            logger.debug(
                f"Frame {frame_idx}: {len(frame_detections)} bins detected"
            )
            if (
                min_detections <= 1
                and len(frame_detections) > 0
                and len(analyzed_indices) >= config.EARLY_STOP_MIN_FRAMES
            ):
                logger.info("Early stop: bin detected, stopping frame processing")
                stopped_early = True
                break

        # Track bins across frames
        tracked_bins = self._track_bins_across_frames(all_detections, min_detections)

        logger.info(f"Tracked {len(tracked_bins)} unique bins")

        # Aggregate predictions for each bin
        for bin_instance in tracked_bins:
            self._aggregate_bin_predictions(bin_instance)

        # Save visualizations if requested
        if save_visualizations or (save_visualizations is None and config.SAVE_VISUALIZATIONS):
            self._save_visualizations(frames, tracked_bins, video_path.stem)

        debug_artifacts = None
        if debug_enabled:
            debug_artifacts = self._save_debug_frames(
                frames[:len(analyzed_indices)],
                analyzed_indices,
                video_path.stem,
                confidence_override=effective_conf
            )

        processing_time = time.time() - start_time

        logger.info(
            f"Video processing complete in {processing_time:.2f}s "
            f"({len(tracked_bins)} bins detected)"
        )

        detections = frame_stats_list
        if debug_artifacts and debug_artifacts.get("metadata"):
            try:
                with open(debug_artifacts["metadata"], "r") as f:
                    debug_metadata = json.load(f)
                detections = debug_metadata.get("detections", frame_stats_list)
            except Exception:
                detections = frame_stats_list

        result = PipelineResult(
            video_path=str(video_path),
            total_frames=frame_info.get("total_frames") or len(frames),
            processed_frames=len(analyzed_indices),
            bins=tracked_bins,
            processing_time=processing_time,
            metadata={
                "detector": self.detector.get_model_info(),
                "classifier": self.classifier.get_model_info(),
                "frame_skip": frame_skip or "default",
                "frame_info": frame_info,
                "debug_confidence_override": confidence_override if debug_enabled else None,
                "effective_conf": effective_conf,
                "effective_imgsz": config.YOLO_IMAGE_SIZE,
                "sampling_strategy": sampling_strategy,
                "frame_indices": analyzed_indices,
                "frames_analyzed": len(analyzed_indices),
                "detections": detections,
            }
            ,
            debug_artifacts=debug_artifacts
        )
        print(
            f"[pipeline] debug={debug_enabled} "
            f"detections_in_metadata={len(result.metadata.get('detections', []))}"
        )
        print(
            f"[pipeline] early_stop_min_frames={config.EARLY_STOP_MIN_FRAMES} "
            f"processed={len(analyzed_indices)} stopped_early={stopped_early}"
        )
        return result

    def _extract_frames(
        self,
        video_path: Path,
        frame_skip: Optional[int] = None,
        max_frames: Optional[int] = None,
        sampling_strategy: Optional[str] = None
    ) -> Tuple[List[np.ndarray], Dict[str, Optional[object]], List[int]]:
        """
        Extract frames from video.

        Args:
            video_path: Path to video
            frame_skip: Extract every Nth frame
            max_frames: Maximum frames to extract

        Returns:
            List of frame images
        """
        frame_skip = frame_skip or config.FRAME_EXTRACTION_RATE
        max_frames = max_frames or config.MAX_FRAMES_PER_VIDEO
        sampling_strategy = sampling_strategy or config.VIDEO_SAMPLING_STRATEGY

        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frames = []
        frame_count = 0
        first_frame_size = None
        indices: List[int] = []

        if total_frames > 0 and sampling_strategy == "fixed_percentages":
            percentages = [0.0, 0.2, 0.4, 0.6, 0.8, 0.95]
            raw_indices = [int(p * (total_frames - 1)) for p in percentages]
            indices = sorted(set(max(0, min(total_frames - 1, idx)) for idx in raw_indices))
        elif total_frames > 0:
            step = max(1, total_frames // max_frames)
            indices = list(range(0, total_frames, step))[:max_frames]

        if indices:
            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue
                frames.append(frame)
                if first_frame_size is None:
                    first_frame_size = (frame.shape[1], frame.shape[0])
            frame_count = len(indices)
        else:
            skip_frames = int(fps * frame_skip)
            while cap.isOpened() and len(frames) < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_count % skip_frames == 0:
                    frames.append(frame)
                    indices.append(frame_count)
                    if first_frame_size is None:
                        first_frame_size = (frame.shape[1], frame.shape[0])
                frame_count += 1

        cap.release()
        return frames, {
            "fps": int(fps),
            "total_frames": total_frames,
            "frames_read": frame_count,
            "first_frame_size": first_frame_size
        }, indices

    def _process_frame(
        self,
        frame: np.ndarray,
        frame_idx: int,
        confidence_override: Optional[float] = None,
        log_detections: bool = False
    ) -> Tuple[List[Tuple[Detection, ClassificationResult]], Dict[str, object]]:
        """
        Process a single frame: detect and classify bins.

        Args:
            frame: Input frame image
            frame_idx: Frame index

        Returns:
            List of (Detection, ClassificationResult) tuples
        """
        # Detect raw objects in frame
        effective_conf = max(
            confidence_override if confidence_override is not None else config.YOLO_CONFIDENCE_THRESHOLD,
            config.YOLO_CONFIDENCE_THRESHOLD
        )
        raw_detections = self.detector.detect_raw(
            frame,
            confidence_threshold=effective_conf,
            log_detections=log_detections
        )

        detections, kept_info, rejected_info, filter_stats = filter_detections_stage_a(
            raw_detections,
            frame.shape,
            effective_conf
        )

        results = []
        for detection in detections:
            # Crop bin from frame
            cropped_bin = detection.crop_from_image(frame)

            # Classify fill level
            try:
                classification = self.classifier.classify(cropped_bin)
                results.append((detection, classification))
            except Exception as e:
                logger.warning(
                    f"Classification failed for bin in frame {frame_idx}: {e}"
                )

        top_detections = sorted(
            raw_detections,
            key=lambda d: d.confidence,
            reverse=True
        )[: config.DEBUG_DETECTIONS_LIMIT]

        stats = {
            "frame_index": frame_idx,
            "raw_count": filter_stats["raw_count"],
            "kept_count": filter_stats["kept_count"],
            "filtered_out_count": filter_stats["filtered_out_count"],
            "kept_class_names": filter_stats["kept_class_names"],
            "kept": kept_info,
            "rejected": rejected_info,
            "top_detections": [
                {
                    "class_name": det.class_name,
                    "confidence": float(det.confidence),
                    "bbox": det.bbox,
                }
                for det in top_detections
            ],
        }

        return results, stats

    def _save_debug_frames(
        self,
        frames: List[np.ndarray],
        frame_indices: List[int],
        video_name: str,
        confidence_override: Optional[float] = None
    ) -> Optional[Dict]:
        if not frames:
            return None

        debug_dir = config.DEBUG_OUTPUT_DIR
        debug_dir.mkdir(parents=True, exist_ok=True)

        indices = list(range(len(frames)))

        artifacts = {
            "frames": [],
            "annotated": [],
            "metadata": None
        }

        effective_conf = max(
            confidence_override if confidence_override is not None else config.YOLO_CONFIDENCE_THRESHOLD,
            config.YOLO_CONFIDENCE_THRESHOLD
        )
        metadata = {
            "video_name": video_name,
            "frame_indices": frame_indices,
            "confidence_override": confidence_override,
            "effective_conf": effective_conf,
            "effective_imgsz": config.YOLO_IMAGE_SIZE,
            "detections": []
        }

        for i, frame in enumerate(frames):
            frame_number = frame_indices[i] if i < len(frame_indices) else i
            frame_path = debug_dir / f"{video_name}_frame_{frame_number}.jpg"
            cv2.imwrite(str(frame_path), frame)
            artifacts["frames"].append(str(frame_path))

            if hasattr(self.detector, "detect_raw"):
                raw_detections = self.detector.detect_raw(
                    frame,
                    confidence_threshold=effective_conf
                )
            else:
                raw_detections = self.detector.detect(
                    frame,
                    confidence_threshold=effective_conf
                )

            filtered, kept_info, rejected_info, filter_stats = filter_detections_stage_a(
                raw_detections,
                frame.shape,
                effective_conf
            )

            annotated = self.detector.visualize_detections(frame, raw_detections)
            annotated_path = debug_dir / f"{video_name}_frame_{frame_number}_annotated.jpg"
            cv2.imwrite(str(annotated_path), annotated)
            artifacts["annotated"].append(str(annotated_path))

            top_detections = sorted(
                raw_detections,
                key=lambda d: d.confidence,
                reverse=True
            )[: config.DEBUG_DETECTIONS_LIMIT]

            metadata["detections"].append({
                "frame_index": frame_number,
                "count": filter_stats["kept_count"],
                "raw_count": filter_stats["raw_count"],
                "kept_count": filter_stats["kept_count"],
                "filtered_out_count": filter_stats["filtered_out_count"],
                "kept_class_names": filter_stats["kept_class_names"],
                "kept": kept_info,
                "rejected": rejected_info,
                "top_detections": [
                    {
                        "class_name": det.class_name,
                        "confidence": float(det.confidence),
                        "bbox": det.bbox,
                    }
                    for det in top_detections
                ],
                "items": [
                    {
                        "class_id": det.class_id,
                        "class_name": det.class_name,
                        "confidence": float(det.confidence),
                        "bbox": det.bbox
                    }
                    for det in filtered
                ]
            })

        metadata_path = debug_dir / f"{video_name}_debug_metadata.json"
        with open(metadata_path, "w") as metadata_file:
            json.dump(metadata, metadata_file, indent=2)
        artifacts["metadata"] = str(metadata_path)

        logger.info(
            "Debug artifacts saved: frames=%s annotated=%s metadata=%s",
            len(artifacts["frames"]),
            len(artifacts["annotated"]),
            metadata_path
        )

        return artifacts

    def _track_bins_across_frames(
        self,
        all_detections: List[List[Tuple[Detection, ClassificationResult]]],
        min_detections: int
    ) -> List[BinInstance]:
        """
        Track same bins across multiple frames using IoU matching.

        Args:
            all_detections: Detections for each frame

        Returns:
            List of tracked bin instances
        """
        tracked_bins: List[BinInstance] = []
        next_bin_id = 0

        for frame_idx, frame_detections in enumerate(all_detections):
            for detection, classification in frame_detections:
                # Find matching bin in tracked bins
                matched_bin = None
                max_iou = 0.0

                for bin_instance in tracked_bins:
                    if not bin_instance.detections:
                        continue

                    # Compare with last detection of this bin
                    last_detection = bin_instance.detections[-1]
                    iou = detection.iou(last_detection)

                    if iou > config.BIN_TRACKING_IOU_THRESHOLD and iou > max_iou:
                        matched_bin = bin_instance
                        max_iou = iou

                if matched_bin:
                    # Add to existing bin
                    matched_bin.detections.append(detection)
                    matched_bin.classifications.append(classification)
                    matched_bin.frame_indices.append(frame_idx)
                else:
                    # Create new bin
                    new_bin = BinInstance(
                        bin_id=f"bin_{next_bin_id:03d}",
                        detections=[detection],
                        classifications=[classification],
                        frame_indices=[frame_idx]
                    )
                    tracked_bins.append(new_bin)
                    next_bin_id += 1

        # Filter out bins with too few detections (likely false positives)
        valid_bins = [
            b for b in tracked_bins
            if len(b.detections) >= min_detections
        ]

        logger.info(
            f"Filtered bins: {len(tracked_bins)} → {len(valid_bins)} "
            f"(min detections: {min_detections})"
        )

        return valid_bins

    def _aggregate_bin_predictions(self, bin_instance: BinInstance) -> None:
        """
        Aggregate predictions across frames using voting strategy.

        Args:
            bin_instance: Bin instance to aggregate
        """
        if not bin_instance.classifications:
            return

        strategy = config.VOTING_STRATEGY

        if strategy == "majority":
            # Most common prediction
            fill_levels = [c.fill_level for c in bin_instance.classifications]
            bin_instance.final_fill_level = max(
                set(fill_levels),
                key=fill_levels.count
            )
            # Average confidence for the predicted level
            confidences = [
                c.confidence for c in bin_instance.classifications
                if c.fill_level == bin_instance.final_fill_level
            ]
            bin_instance.confidence = np.mean(confidences)

        elif strategy == "conservative":
            # Choose fullest level (safety-first approach)
            level_order = {FillLevel.EMPTY: 0, FillLevel.HALF: 1, FillLevel.FULL: 2}
            fill_levels = [c.fill_level for c in bin_instance.classifications]
            bin_instance.final_fill_level = max(fill_levels, key=lambda x: level_order[x])
            confidences = [
                c.confidence for c in bin_instance.classifications
                if c.fill_level == bin_instance.final_fill_level
            ]
            bin_instance.confidence = np.mean(confidences) if confidences else 0.5

        elif strategy == "latest":
            # Use most recent prediction
            latest = bin_instance.classifications[-1]
            bin_instance.final_fill_level = latest.fill_level
            bin_instance.confidence = latest.confidence

        else:
            raise ValueError(f"Unknown voting strategy: {strategy}")

        # Calculate average bounding box
        all_bboxes = np.array([d.bbox for d in bin_instance.detections])
        avg_bbox = np.mean(all_bboxes, axis=0).astype(int)
        bin_instance.final_bbox = tuple(avg_bbox)

    def _save_visualizations(
        self,
        frames: List[np.ndarray],
        bins: List[BinInstance],
        video_name: str
    ) -> None:
        """
        Save visualization images with detections and classifications.

        Args:
            frames: All frames
            bins: Tracked bins
            video_name: Video name for file naming
        """
        vis_dir = config.VISUALIZATIONS_DIR
        vis_dir.mkdir(parents=True, exist_ok=True)

        # Create visualization for a representative frame (middle frame)
        if not frames:
            return

        mid_frame_idx = len(frames) // 2
        vis_frame = frames[mid_frame_idx].copy()

        # Draw all bins detected in this frame
        for bin_instance in bins:
            if mid_frame_idx not in bin_instance.frame_indices:
                continue

            # Find detection for this frame
            frame_pos = bin_instance.frame_indices.index(mid_frame_idx)
            detection = bin_instance.detections[frame_pos]
            x1, y1, x2, y2 = detection.bbox

            # Color based on fill level
            color_map = {
                FillLevel.EMPTY: (0, 255, 0),    # Green
                FillLevel.HALF: (0, 165, 255),   # Orange
                FillLevel.FULL: (0, 0, 255),     # Red
            }
            color = color_map.get(bin_instance.final_fill_level, (255, 255, 255))

            # Draw bounding box
            cv2.rectangle(vis_frame, (x1, y1), (x2, y2), color, 3)

            # Draw label
            label = f"{bin_instance.bin_id}: {bin_instance.final_fill_level.value}"
            cv2.putText(
                vis_frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

        # Save visualization
        vis_path = vis_dir / f"{video_name}_result.jpg"
        cv2.imwrite(str(vis_path), vis_frame)
        logger.info(f"Visualization saved: {vis_path}")


# TODO: Add support for real-time video streams
# TODO: Implement Kalman filter for smoother tracking
# TODO: Add re-identification for bins that disappear and reappear
# TODO: Add multi-camera support and view fusion
# TODO: Add anomaly detection (unusual fill patterns)
# TODO: Add time-series analysis for fill rate prediction
# TODO: Add geographic clustering (bins in same area)
# TODO: Optimize with multi-threading/multi-processing
# TODO: Add support for GPU batch processing


if __name__ == "__main__":
    """
    Test script for inference pipeline.

    Usage:
        python -m ai.inference.pipeline
    """
    print("Inference Pipeline Test")
    print("=" * 50)

    # Initialize pipeline
    pipeline = InferencePipeline()

    print("\n✓ Pipeline initialized successfully")
    print(f"  Detector: {pipeline.detector.get_model_info()['name']}")
    print(f"  Classifier: {pipeline.classifier.get_model_info()['name']}")
    print("\nReady to process videos!")
