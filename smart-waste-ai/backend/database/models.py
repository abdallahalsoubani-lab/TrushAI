"""
Database Models for Smart Waste AI
==================================
SQLAlchemy 2.0 models for Analysis, BinDetection, and Artifact tables.

Tables:
- Analysis: Stores analysis metadata (video/image processing results)
- BinDetection: Stores individual bin detections per analysis
- Artifact: Stores file artifacts (overlay images, cropped bins, metadata)
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class FillLevelEnum(str, enum.Enum):
    """Fill level status enum"""
    EMPTY = "EMPTY"
    HALF = "HALF"
    FULL = "FULL"
    NO_BIN_DETECTED = "NO_BIN_DETECTED"


class InputTypeEnum(str, enum.Enum):
    """Input type enum"""
    IMAGE = "image"
    VIDEO = "video"


class ArtifactTypeEnum(str, enum.Enum):
    """Artifact type enum"""
    OVERLAY_IMAGE = "overlay_image"
    CROPPED_BIN = "cropped_bin"
    METADATA_JSON = "metadata_json"
    ORIGINAL_FILE = "original_file"


class Analysis(Base):
    """
    Analysis table - stores metadata for each video/image analysis.

    Represents a single analysis run (either image or video).
    Contains overall results and links to detected bins and artifacts.
    """
    __tablename__ = "analyses"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Input metadata
    input_type: Mapped[str] = mapped_column(SQLEnum(InputTypeEnum), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # Path to stored file

    # Analysis results
    status: Mapped[str] = mapped_column(SQLEnum(FillLevelEnum), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bins_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Debug mode flag
    debug_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    bin_detections: Mapped[List["BinDetection"]] = relationship(
        "BinDetection",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Analysis(id={self.id}, input_type={self.input_type}, "
            f"status={self.status}, bins_detected={self.bins_detected})>"
        )


class BinDetection(Base):
    """
    BinDetection table - stores individual bin detections.

    Each analysis can have multiple bin detections.
    For videos, bins may be detected across multiple frames.
    """
    __tablename__ = "bin_detections"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to Analysis
    analysis_id: Mapped[int] = mapped_column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)

    # Detection metadata
    bin_index: Mapped[int] = mapped_column(Integer, nullable=False)  # Index within this analysis
    frame_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # For videos, which frame

    # Bounding box (x1, y1, x2, y2)
    bbox_x1: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y1: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_x2: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_y2: Mapped[int] = mapped_column(Integer, nullable=False)

    # Classification results
    fill_level: Mapped[str] = mapped_column(SQLEnum(FillLevelEnum), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Detection confidence (from YOLO)
    detection_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Classifier metadata (JSON string for raw scores, thresholds, etc.)
    classifier_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="bin_detections")

    def __repr__(self) -> str:
        return (
            f"<BinDetection(id={self.id}, analysis_id={self.analysis_id}, "
            f"bin_index={self.bin_index}, fill_level={self.fill_level})>"
        )


class Artifact(Base):
    """
    Artifact table - stores file artifacts generated during analysis.

    Artifacts include:
    - Overlay images (with bounding boxes)
    - Cropped bin images
    - Metadata JSON files
    - Original uploaded files
    """
    __tablename__ = "artifacts"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to Analysis
    analysis_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=True, index=True)

    # Foreign key to BatchItem (for batch uploads)
    batch_item_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("batch_items.id", ondelete="CASCADE"), nullable=True, index=True)

    # Artifact metadata
    type: Mapped[str] = mapped_column(SQLEnum(ArtifactTypeEnum), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(512), nullable=False)  # Relative path from data/results/

    # Optional metadata
    bin_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # For cropped bins
    frame_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # For video frames

    # File metadata
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Size in bytes
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    analysis: Mapped[Optional["Analysis"]] = relationship("Analysis", back_populates="artifacts")
    batch_item: Mapped[Optional["BatchItem"]] = relationship("BatchItem", back_populates="artifacts")

    def __repr__(self) -> str:
        return (
            f"<Artifact(id={self.id}, analysis_id={self.analysis_id}, "
            f"batch_item_id={self.batch_item_id}, type={self.type}, path={self.path})>"
        )


class BatchAnalysis(Base):
    """
    BatchAnalysis table - stores metadata for batch image uploads.

    Represents a batch of multiple images analyzed together.
    Contains summary statistics for the entire batch.
    """
    __tablename__ = "batch_analyses"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Batch metadata
    batch_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)  # UUID-like identifier
    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Summary counts (stored as JSON string for flexibility)
    status_counts: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: {"EMPTY": 5, "HALF": 3, "FULL": 2}

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Processing status
    processing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="processing")  # processing, completed, failed

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    items: Mapped[List["BatchItem"]] = relationship(
        "BatchItem",
        back_populates="batch",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<BatchAnalysis(id={self.id}, batch_id={self.batch_id}, "
            f"total_files={self.total_files}, status={self.processing_status})>"
        )


class BatchItem(Base):
    """
    BatchItem table - stores individual image results within a batch.

    Each item represents one image from a batch upload.
    Contains detection and classification results for that image.
    """
    __tablename__ = "batch_items"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to BatchAnalysis
    batch_id: Mapped[int] = mapped_column(Integer, ForeignKey("batch_analyses.id", ondelete="CASCADE"), nullable=False, index=True)

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)  # Path to stored file

    # Analysis results
    status: Mapped[str] = mapped_column(SQLEnum(FillLevelEnum), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    bins_detected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing status for this item
    processing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed

    # Relationships
    batch: Mapped["BatchAnalysis"] = relationship("BatchAnalysis", back_populates="items")
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact",
        back_populates="batch_item",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<BatchItem(id={self.id}, batch_id={self.batch_id}, "
            f"filename={self.original_filename}, status={self.status})>"
        )
