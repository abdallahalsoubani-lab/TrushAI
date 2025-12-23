"""
FastAPI Backend Application
============================
Main entry point for the smart waste monitoring API.

This application provides REST endpoints for:
- Video analysis (trash bin detection + fill level classification)
- Bin status retrieval
- Service health checks

Run with:
    python backend/main.py
    or
    uvicorn backend.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import router
from backend.services.inference_service import get_inference_service
from ai.config import config

# Set up logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Load AI models
    - Shutdown: Cleanup resources
    """
    # Startup
    logger.info("=" * 50)
    logger.info("Smart Waste Monitoring API - Starting Up")
    logger.info("=" * 50)

    try:
        # Initialize inference service
        service = get_inference_service()
        service.initialize_models()

        logger.info("✓ Application startup complete")
        logger.info(f"  API running on: http://{config.API_HOST}:{config.API_PORT}")
        logger.info(f"  Docs available at: http://{config.API_HOST}:{config.API_PORT}/docs")

    except Exception as e:
        logger.error(f"✗ Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")
    logger.info("✓ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Smart Waste Monitoring API",
    description="""
    AI-powered trash bin monitoring system using computer vision.

    ## Features

    * **Video Analysis**: Detect trash bins and estimate fill levels from video
    * **Real-time Status**: Get current status of all detected bins
    * **Mock Classifier**: Uses heuristic-based classification (brightness/edge density)
    * **Clean Architecture**: Modular design ready for production ML models

    ## Workflow

    1. Upload/specify a video file path
    2. System extracts frames and detects bins using YOLOv8
    3. Each bin is classified as EMPTY, HALF, or FULL
    4. Results are aggregated across frames using voting
    5. Query bin status via API or view in dashboard

    ## TODO for Production

    * Train custom CNN classifier on real trash bin data
    * Fine-tune YOLO on custom trash bin dataset
    * Add real-time video stream support
    * Add database for persistent storage
    * Add authentication and authorization
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["bins"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Smart Waste Monitoring API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler.

    Catches unhandled exceptions and returns a proper error response.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        }
    )


if __name__ == "__main__":
    """
    Run the application directly.

    For development, use:
        python backend/main.py

    For production, use:
        uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
    """
    import uvicorn

    logger.info("Starting FastAPI server...")

    uvicorn.run(
        "backend.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=config.API_RELOAD,
        log_level=config.LOG_LEVEL.lower()
    )


# TODO: Add API versioning strategy
# TODO: Add request/response logging middleware
# TODO: Add performance monitoring (timing, memory)
# TODO: Add OpenTelemetry instrumentation
# TODO: Add Prometheus metrics endpoint
# TODO: Add graceful shutdown handling
# TODO: Add background task processing (Celery/RQ)
# TODO: Add database integration (PostgreSQL + SQLAlchemy)
# TODO: Add caching layer (Redis)
# TODO: Add API key authentication
