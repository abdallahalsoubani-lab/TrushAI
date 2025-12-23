"""
Batch Service
=============
Business logic for managing batch image uploads and processing.

Provides CRUD operations and queries for batch analyses and items.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.database.models import BatchAnalysis, BatchItem, Artifact, FillLevelEnum, ArtifactTypeEnum

logger = logging.getLogger(__name__)


class BatchService:
    """Service for managing batch analyses and items"""

    @staticmethod
    def create_batch(
        db: Session,
        batch_id: str,
        total_files: int
    ) -> BatchAnalysis:
        """
        Create a new batch analysis record.

        Args:
            db: Database session
            batch_id: Unique batch identifier
            total_files: Total number of files in batch

        Returns:
            Created BatchAnalysis instance
        """
        batch = BatchAnalysis(
            batch_id=batch_id,
            total_files=total_files,
            created_at=datetime.utcnow(),
            processing_status="processing",
            failed_count=0
        )

        db.add(batch)
        db.commit()
        db.refresh(batch)

        logger.info(f"Created batch {batch_id} with {total_files} files")
        return batch

    @staticmethod
    def update_batch_status(
        db: Session,
        batch_id: int,
        processing_status: str,
        status_counts: Optional[Dict[str, int]] = None,
        error_message: Optional[str] = None,
        failed_count: int = 0
    ) -> BatchAnalysis:
        """
        Update batch processing status.

        Args:
            db: Database session
            batch_id: ID of batch to update
            processing_status: New status (processing/completed/failed)
            status_counts: Summary of statuses {"EMPTY": 5, "HALF": 3, ...}
            error_message: Error message if failed
            failed_count: Number of failed items

        Returns:
            Updated BatchAnalysis instance
        """
        batch = db.query(BatchAnalysis).filter(BatchAnalysis.id == batch_id).first()

        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        batch.processing_status = processing_status
        batch.failed_count = failed_count
        batch.error_message = error_message

        if status_counts:
            batch.status_counts = json.dumps(status_counts)

        if processing_status == "completed":
            batch.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(batch)

        logger.info(f"Updated batch {batch_id} status to {processing_status}")
        return batch

    @staticmethod
    def create_batch_item(
        db: Session,
        batch_id: int,
        original_filename: str,
        stored_path: str
    ) -> BatchItem:
        """
        Create a new batch item record.

        Args:
            db: Database session
            batch_id: ID of parent batch
            original_filename: Original filename
            stored_path: Path to stored file

        Returns:
            Created BatchItem instance
        """
        item = BatchItem(
            batch_id=batch_id,
            original_filename=original_filename,
            stored_path=stored_path,
            status=FillLevelEnum.NO_BIN_DETECTED,  # Default
            confidence=0.0,  # Default
            bins_detected=0,  # Default
            created_at=datetime.utcnow(),
            processing_status="pending"
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        logger.debug(f"Created batch item {item.id} for file {original_filename}")
        return item

    @staticmethod
    def update_batch_item_result(
        db: Session,
        item_id: int,
        status: str,
        confidence: float,
        bins_detected: int,
        error_message: Optional[str] = None
    ) -> BatchItem:
        """
        Update batch item with analysis results.

        Args:
            db: Database session
            item_id: ID of item to update
            status: Fill level status
            confidence: Confidence score
            bins_detected: Number of bins detected
            error_message: Error message if failed

        Returns:
            Updated BatchItem instance
        """
        item = db.query(BatchItem).filter(BatchItem.id == item_id).first()

        if not item:
            raise ValueError(f"Batch item {item_id} not found")

        item.status = status
        item.confidence = confidence
        item.bins_detected = bins_detected
        item.completed_at = datetime.utcnow()
        item.error_message = error_message
        item.processing_status = "completed" if not error_message else "failed"

        db.commit()
        db.refresh(item)

        logger.debug(f"Updated batch item {item_id} with status {status}")
        return item

    @staticmethod
    def add_batch_item_artifact(
        db: Session,
        batch_item_id: int,
        artifact_type: str,
        path: str,
        bin_index: Optional[int] = None,
        file_size: Optional[int] = None,
        mime_type: Optional[str] = None
    ) -> Artifact:
        """
        Add an artifact to a batch item.

        Args:
            db: Database session
            batch_item_id: ID of parent batch item
            artifact_type: Type of artifact
            path: Relative path to artifact file
            bin_index: Bin index (for cropped bins)
            file_size: File size in bytes
            mime_type: MIME type

        Returns:
            Created Artifact instance
        """
        artifact = Artifact(
            batch_item_id=batch_item_id,
            type=artifact_type,
            path=path,
            bin_index=bin_index,
            file_size=file_size,
            mime_type=mime_type
        )

        db.add(artifact)
        db.commit()
        db.refresh(artifact)

        logger.debug(f"Added artifact {artifact.id} for batch item {batch_item_id}")
        return artifact

    @staticmethod
    def get_batch(db: Session, batch_id: int) -> Optional[BatchAnalysis]:
        """
        Get batch by ID.

        Args:
            db: Database session
            batch_id: ID of batch

        Returns:
            BatchAnalysis instance or None
        """
        return db.query(BatchAnalysis).filter(BatchAnalysis.id == batch_id).first()

    @staticmethod
    def get_batch_by_batch_id(db: Session, batch_id_str: str) -> Optional[BatchAnalysis]:
        """
        Get batch by batch_id string.

        Args:
            db: Database session
            batch_id_str: Batch ID string

        Returns:
            BatchAnalysis instance or None
        """
        return db.query(BatchAnalysis).filter(BatchAnalysis.batch_id == batch_id_str).first()

    @staticmethod
    def get_batches(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        processing_status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[BatchAnalysis], int]:
        """
        Get list of batches with pagination and filtering.

        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records
            processing_status_filter: Filter by processing status
            sort_by: Field to sort by
            sort_order: "asc" or "desc"

        Returns:
            Tuple of (list of batches, total count)
        """
        query = db.query(BatchAnalysis)

        # Apply filters
        if processing_status_filter:
            query = query.filter(BatchAnalysis.processing_status == processing_status_filter)

        # Get total count
        total = query.count()

        # Apply sorting
        sort_column = getattr(BatchAnalysis, sort_by, BatchAnalysis.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # Apply pagination
        batches = query.offset(skip).limit(limit).all()

        return batches, total

    @staticmethod
    def get_batch_items(
        db: Session,
        batch_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[BatchItem], int]:
        """
        Get items for a specific batch.

        Args:
            db: Database session
            batch_id: ID of batch
            skip: Number of records to skip
            limit: Maximum number of records

        Returns:
            Tuple of (list of items, total count)
        """
        query = db.query(BatchItem).filter(BatchItem.batch_id == batch_id)

        total = query.count()

        items = query.offset(skip).limit(limit).all()

        return items, total

    @staticmethod
    def get_batch_item(db: Session, item_id: int) -> Optional[BatchItem]:
        """
        Get batch item by ID.

        Args:
            db: Database session
            item_id: ID of item

        Returns:
            BatchItem instance or None
        """
        return db.query(BatchItem).filter(BatchItem.id == item_id).first()

    @staticmethod
    def delete_batch(db: Session, batch_id: int) -> bool:
        """
        Delete batch and all related records.

        Args:
            db: Database session
            batch_id: ID of batch to delete

        Returns:
            True if deleted, False if not found
        """
        batch = db.query(BatchAnalysis).filter(BatchAnalysis.id == batch_id).first()

        if not batch:
            return False

        # Delete batch (cascade will delete items and artifacts)
        db.delete(batch)
        db.commit()

        logger.info(f"Deleted batch {batch_id}")
        return True

    @staticmethod
    def get_batch_summary_counts(items: List[BatchItem]) -> Dict[str, int]:
        """
        Calculate summary counts from batch items.

        Args:
            items: List of BatchItem instances

        Returns:
            Dictionary with status counts
        """
        counts = {
            "EMPTY": 0,
            "HALF": 0,
            "FULL": 0,
            "NO_BIN_DETECTED": 0
        }

        for item in items:
            if item.status in counts:
                counts[item.status] += 1

        return counts
