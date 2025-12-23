# Smart Waste Monitoring - Backend Dockerfile
# ============================================
# Multi-stage build for optimized production image

FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ai/ ai/
COPY backend/ backend/
COPY scripts/ scripts/

# Create data directories
RUN mkdir -p data/videos data/frames data/results

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')"

# Run application
CMD ["python", "backend/main.py"]

# ============================================
# Build Instructions:
# ============================================
#
# Build image:
#   docker build -t smart-waste-backend .
#
# Run container:
#   docker run -p 8000:8000 -v $(pwd)/data:/app/data smart-waste-backend
#
# Run with GPU (NVIDIA):
#   docker run --gpus all -p 8000:8000 smart-waste-backend
#
# ============================================
# TODO: Production optimizations
# ============================================
#
# - Multi-stage build to reduce image size
# - Use gunicorn with multiple workers
# - Add non-root user for security
# - Optimize layer caching
# - Add environment-based configuration
#
