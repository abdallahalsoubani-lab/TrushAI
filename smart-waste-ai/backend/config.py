"""
Backend Configuration
=====================
Centralized configuration for FastAPI backend.

Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional


class BackendConfig:
    """Backend configuration settings"""

    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    RESULTS_DIR = DATA_DIR / "results"
    UPLOADS_DIR = DATA_DIR / "uploads"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{DATA_DIR}/smart_waste.db"
    )

    # Server settings
    HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    RELOAD: bool = os.getenv("BACKEND_RELOAD", "True").lower() == "true"

    # CORS settings
    CORS_ORIGINS: list = [
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        os.getenv("FRONTEND_URL", ""),
    ]

    # File upload settings
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))
    ALLOWED_VIDEO_EXTENSIONS: set = {".mp4", ".avi", ".mov", ".mkv"}
    ALLOWED_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png"}
    TEMP_UPLOAD_DIR: Path = UPLOADS_DIR / "temp"

    # Storage settings
    STORE_UPLOADED_FILES: bool = os.getenv("STORE_UPLOADED_FILES", "True").lower() == "true"
    ANALYSIS_STORAGE_DIR: Path = RESULTS_DIR / "analyses"

    # Debug settings
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    DEBUG_OUTPUT_DIR: Path = RESULTS_DIR / "debug"

    # Cache settings (for backward compatibility with in-memory cache)
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "100"))

    # Authentication (optional, for future use)
    ADMIN_PASSWORD: Optional[str] = os.getenv("ADMIN_PASSWORD", None)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Notification settings (optional, for future use)
    WEBHOOK_URL: Optional[str] = os.getenv("WEBHOOK_URL", None)
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST", None)
    SMTP_PORT: Optional[int] = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER", None)
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD", None)
    ALERT_EMAIL: Optional[str] = os.getenv("ALERT_EMAIL", None)

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        directories = [
            cls.DATA_DIR,
            cls.RESULTS_DIR,
            cls.UPLOADS_DIR,
            cls.TEMP_UPLOAD_DIR,
            cls.ANALYSIS_STORAGE_DIR,
            cls.DEBUG_OUTPUT_DIR,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


# Global config instance
config = BackendConfig()

# Ensure directories exist on import
config.ensure_directories()
