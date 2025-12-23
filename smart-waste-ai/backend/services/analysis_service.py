"""
Analysis Service
================
Business logic for managing Analysis, BinDetection, and Artifact records.

Provides CRUD operations and queries for analysis history.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from database.models import Analysis, BinDetection, Artifact, FillLevelEnum, InputTypeEnum, ArtifactTypeEnum

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service for managing analysis records"""

    @staticmethod
    def create_analysis(
        db: Session,
        input_type: str,
        original_filename: str,
        stored_path: Optional[str] = None,
        debug_enabled: bool = False
    ) -> Analysis:
        """
        Create a new analysis record.

        Args:
            db: Database session
            input_type: "image" or "video"
            original_filename: Original uploaded filename
            stored_path: Path where file is stored (optional)
            debug_enabled: Whether debug mode is enabled

        Returns:
            Created Analysis instance
        """
        analysis = Analysis(
            input_type=input_type,
            original_filename=original_filename,
            stored_path=stored_path,
            status=FillLevelEnum.EMPTY,  # Default, will be updated
            confidence=0.0,  # Default, will be updated
            bins_detected=0,  # Default, will be updated
            started_at=datetime.utcnow(),
            debug_enabled=debug_enabled
        )

        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        logger.info(f"Created analysis {analysis.id} for {original_filename}")
        return analysis

    @staticmethod
    def update_analysis_result(
        db: Session,
        analysis_id: int,
        status: str,
        confidence: float,
        bins_detected: int,
        error_message: Optional[str] = None
    ) -> Analysis:
        """
        Update analysis with results.

        Args:
            db: Database session
            analysis_id: ID of analysis to update
            status: Fill level status (EMPTY/HALF/FULL/NO_BIN_DETECTED)
            confidence: Confidence score (0.0-1.0)
            bins_detected: Number of bins detected
            error_message: Error message if analysis failed

        Returns:
            Updated Analysis instance
        """
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        analysis.status = status
        analysis.confidence = confidence
        analysis.bins_detected = bins_detected
        analysis.completed_at = datetime.utcnow()
        analysis.error_message = error_message

        db.commit()
        db.refresh(analysis)

        logger.info(f"Updated analysis {analysis_id} with status {status}")
        return analysis

    @staticmethod
    def add_bin_detection(
        db: Session,
        analysis_id: int,
        bin_index: int,
        bbox: List[int],
        fill_level: str,
        confidence: float,
        detection_confidence: Optional[float] = None,
        frame_index: Optional[int] = None,
        classifier_metadata: Optional[Dict[str, Any]] = None
    ) -> BinDetection:
        """
        Add a bin detection to an analysis.

        Args:
            db: Database session
            analysis_id: ID of parent analysis
            bin_index: Index of bin within this analysis
            bbox: Bounding box [x1, y1, x2, y2]
            fill_level: Fill level (EMPTY/HALF/FULL)
            confidence: Classification confidence
            detection_confidence: YOLO detection confidence
            frame_index: Frame index (for videos)
            classifier_metadata: Raw scores and metadata

        Returns:
            Created BinDetection instance
        """
        bin_detection = BinDetection(
            analysis_id=analysis_id,
            bin_index=bin_index,
            bbox_x1=bbox[0],
            bbox_y1=bbox[1],
            bbox_x2=bbox[2],
            bbox_y2=bbox[3],
            fill_level=fill_level,
            confidence=confidence,
            detection_confidence=detection_confidence,
            frame_index=frame_index,
            classifier_metadata=json.dumps(classifier_metadata) if classifier_metadata else None
        )

        db.add(bin_detection)
        db.commit()
        db.refresh(bin_detection)

        logger.debug(f"Added bin detection {bin_detection.id} for analysis {analysis_id}")
        return bin_detection

    @staticmethod
    def add_artifact(
        db: Session,
        analysis_id: int,
        artifact_type: str,
        path: str,
        bin_index: Optional[int] = None,
        frame_index: Optional[int] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None
    ) -> Artifact:
        """
        Add an artifact to an analysis.

        Args:
            db: Database session
            analysis_id: ID of parent analysis
            artifact_type: Type of artifact (overlay_image, cropped_bin, metadata_json, original_file)
            path: Relative path to artifact file
            bin_index: Bin index (for cropped bins)
            frame_index: Frame index (for videos)
            file_size: File size in bytes
            mime_type: MIME type of file

        Returns:
            Created Artifact instance
        """
        artifact = Artifact(
            analysis_id=analysis_id,
            type=artifact_type,
            path=path,
            bin_index=bin_index,
            frame_index=frame_index,
            file_size=file_size,
            mime_type=mime_type
        )

        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        logger.debug(f"Added artifact {artifact.id} for analysis {analysis_id}")
        return artifact

    @staticmethod
    def get_analysis(db: Session, analysis_id: int) -> Optional[Analysis]:
        """
        Get analysis by ID.

        Args:
            db: Database session
            analysis_id: ID of analysis

        Returns:
            Analysis instance or None
        """
        return db.query(Analysis).filter(Analysis.id == analysis_id).first()

    @staticmethod
    def get_analyses(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None,
        input_type_filter: Optional[str] = None,
        sort_by: str = "started_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Analysis], int]:
        """
        Get list of analyses with pagination and filtering.

        Args:
            db: Database session
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            status_filter: Filter by status (optional)
            input_type_filter: Filter by input type (optional)
            sort_by: Field to sort by
            sort_order: "asc" or "desc"

        Returns:
            Tuple of (list of analyses, total count)
        """
        query = db.query(Analysis)

        # Apply filters
        if status_filter:
            query = query.filter(Analysis.status == status_filter)
        if input_type_filter:
            query = query.filter(Analysis.input_type == input_type_filter)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_column = getattr(Analysis, sort_by, Analysis.started_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Apply pagination
        analyses = query.offset(skip).limit(limit).all()

        return analyses, total

    @staticmethod
    def get_latest_analysis(db: Session) -> Optional[Analysis]:
        """
        Get the most recent analysis.

        Args:
            db: Database session

        Returns:
            Latest Analysis instance or None
        """
        return db.query(Analysis).order_by(desc(Analysis.started_at)).first()

    @staticmethod
    def get_analysis_summary(db: Session) -> Dict[str, Any]:
        """
        Get summary statistics for all analyses.

        Args:
            db: Database session

        Returns:
            Dictionary with summary statistics
        """
        total_analyses = db.query(func.count(Analysis.id)).scalar() or 0

        # Count by status
        status_counts = {}
        for status in FillLevelEnum:
            count = db.query(func.count(Analysis.id)).filter(
                Analysis.status == status.value
            ).scalar() or 0
            status_counts[status.value] = count

        # Count by input type
        input_type_counts = {}
        for input_type in InputTypeEnum:
            count = db.query(func.count(Analysis.id)).filter(
                Analysis.input_type == input_type.value
            ).scalar() or 0
            input_type_counts[input_type.value] = count

        # Get latest analysis
        latest = db.query(Analysis).order_by(desc(Analysis.started_at)).first()

        return {
            "total_analyses": total_analyses,
            "status_counts": status_counts,
            "input_type_counts": input_type_counts,
            "latest_analysis": {
                "id": latest.id,
                "status": latest.status,
                "started_at": latest.started_at.isoformat(),
                "input_type": latest.input_type
            } if latest else None
        }

    @staticmethod
    def delete_analysis(db: Session, analysis_id: int) -> bool:
        """
        Delete analysis and all related records.

        Args:
            db: Database session
            analysis_id: ID of analysis to delete

        Returns:
            True if deleted, False if not found
        """
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()

        if not analysis:
            return False

        # Delete analysis (cascade will delete bin_detections and artifacts)
        db.delete(analysis)
        db.commit()

        logger.info(f"Deleted analysis {analysis_id}")
        return True

    @staticmethod
    def get_artifact(db: Session, artifact_id: int) -> Optional[Artifact]:
        """
        Get artifact by ID.

        Args:
            db: Database session
            artifact_id: ID of artifact

        Returns:
            Artifact instance or None
        """
        return db.query(Artifact).filter(Artifact.id == artifact_id).first()

    @staticmethod
    def get_analysis_artifacts(
        db: Session,
        analysis_id: int,
        artifact_type: Optional[str] = None
    ) -> List[Artifact]:
        """
        Get all artifacts for an analysis.

        Args:
            db: Database session
            analysis_id: ID of analysis
            artifact_type: Filter by type (optional)

        Returns:
            List of Artifact instances
        """
        query = db.query(Artifact).filter(Artifact.analysis_id == analysis_id)

        if artifact_type:
            query = query.filter(Artifact.type == artifact_type)

        return query.all()
