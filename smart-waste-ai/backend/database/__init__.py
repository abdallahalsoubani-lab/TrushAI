"""
Database package for Smart Waste AI
===================================
Provides database models, session management, and utilities.
"""

from .models import Analysis, BinDetection, Artifact, BatchAnalysis, BatchItem, Area, Bin, Capture, BinEvent
from .session import SessionLocal, engine, get_db, init_db

__all__ = [
    "Analysis",
    "BinDetection",
    "Artifact",
    "BatchAnalysis",
    "BatchItem",
    "Area",
    "Bin",
    "Capture",
    "BinEvent",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
]
