# Smart Waste Monitoring System 🗑️

AI-powered trash bin monitoring system using computer vision to detect bins and estimate fill levels from video footage.

## 📋 Overview

This MVP demonstrates a clean, modular architecture for smart city waste monitoring. The system analyzes street videos, detects trash bins using YOLOv8, estimates their fill level (Empty/Half/Full), and exposes results via REST API and web dashboard.

### Key Features

- **Object Detection**: YOLOv8-based trash bin detection
- **Fill Level Classification**: Mock classifier using brightness/edge density heuristics
- **REST API**: FastAPI backend with comprehensive endpoints
- **Web Dashboard**: React/Next.js UI for real-time monitoring
- **Clean Architecture**: Modular, interface-based design
- **Future-Ready**: Extensive TODOs for production ML models

## 🏗️ Architecture

```
┌─────────────────┐
│  Video Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Frame Extraction│ (Extract frames every N seconds)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ YOLO Detection  │ (Detect trash bins)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Bin Cropping    │ (Extract bin regions)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Classification  │ (EMPTY/HALF/FULL)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Aggregation     │ (Voting across frames)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   API + UI      │ (FastAPI + React)
└─────────────────┘
```

## 📁 Project Structure

```
smart-waste-ai/
├── backend/                    # FastAPI backend
│   ├── main.py                # Application entry point
│   ├── api/
│   │   └── routes.py          # API endpoints
│   ├── schemas/
│   │   └── bin_status.py      # Pydantic models
│   └── services/
│       └── inference_service.py # Business logic
│
├── ai/                         # AI/ML components
│   ├── config.py              # Configuration
│   ├── detection/
│   │   ├── detector_interface.py    # Detector contract
│   │   └── yolo_detector.py         # YOLOv8 implementation
│   ├── classification/
│   │   ├── classifier_interface.py  # Classifier contract
│   │   └── fill_level_classifier.py # Mock classifiers
│   └── inference/
│       └── pipeline.py        # Orchestration pipeline
│
├── dashboard/                  # React/Next.js dashboard
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx       # Main page
│   │       └── layout.tsx     # Layout
│   ├── package.json
│   └── README.md
│
├── data/                       # Data directories
│   ├── videos/                # Input videos
│   ├── frames/                # Extracted frames
│   └── results/               # Analysis results
│
├── scripts/
│   └── extract_frames.py      # Frame extraction utility
│
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18+ (for dashboard)
- **pip**: Python package manager
- **npm**: Node package manager

### 1. Clone & Setup

```bash
# Navigate to project
cd smart-waste-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Start Backend API

```bash
# From project root
python backend/main.py
```

The API will start on `http://localhost:8000`
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

### 3. Start Dashboard (Optional)

```bash
# Navigate to dashboard
cd dashboard

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Dashboard will be available at `http://localhost:3000`

### 4. Analyze a Video

#### Option A: Using Python API

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/analyze-video",
    json={
        "video_path": "/path/to/your/video.mp4",
        "frame_skip": 2,
        "max_frames": 50,
        "save_visualizations": True
    }
)

result = response.json()
print(f"Detected {result['bins_detected']} bins")
```

#### Option B: Using cURL

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-video" \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/path/to/video.mp4",
    "frame_skip": 2,
    "max_frames": 50
  }'
```

#### Option C: Using the Interactive API Docs

1. Open http://localhost:8000/docs
2. Click on `POST /api/v1/analyze-video`
3. Click "Try it out"
4. Enter video path and parameters
5. Click "Execute"

### 5. View Results

```bash
# Get all bin statuses
curl http://localhost:8000/api/v1/bins-status

# Get specific bin
curl http://localhost:8000/api/v1/bins-status/bin_001
```

Or view in the dashboard at http://localhost:3000

## 📊 API Endpoints

### Health & Status

- `GET /health` - Health check
- `GET /api/v1/service-info` - Service information

### Bin Status

- `GET /api/v1/bins-status` - Get all bin statuses
- `GET /api/v1/bins-status/{bin_id}` - Get specific bin status

### Video Analysis

- `POST /api/v1/analyze-video` - Analyze a video file

### Utilities

- `POST /api/v1/clear-cache` - Clear bin status cache

## 🔧 Configuration

Edit `ai/config.py` to customize:

### Detection Parameters

```python
YOLO_MODEL_SIZE = "n"              # n/s/m/l/x (nano to xlarge)
YOLO_CONFIDENCE_THRESHOLD = 0.25   # Detection confidence
YOLO_DEVICE = "cpu"                # cpu/cuda/mps
```

### Classification Parameters

```python
MOCK_CLASSIFIER_MODE = "brightness"  # brightness/edge_density/hybrid
BRIGHTNESS_EMPTY_THRESHOLD = 150     # Brightness-based thresholds
EDGE_EMPTY_THRESHOLD = 0.05          # Edge density thresholds
```

### Video Processing

```python
FRAME_EXTRACTION_RATE = 2      # Extract 1 frame every N seconds
MAX_FRAMES_PER_VIDEO = 50      # Maximum frames to process
```

### Aggregation

```python
VOTING_STRATEGY = "majority"           # majority/conservative/latest
MIN_DETECTIONS_FOR_VALID_BIN = 3      # Min detections across frames
```

## 🧪 Testing Components

### Test Detector

```bash
python -m ai.detection.yolo_detector
```

### Test Classifier

```bash
python -m ai.classification.fill_level_classifier
```

### Test Pipeline

```bash
python -m ai.inference.pipeline
```

### Extract Frames from Video

```bash
python scripts/extract_frames.py \
  --video data/videos/street.mp4 \
  --rate 2 \
  --max 50 \
  --output data/frames/
```

## 📝 Mock vs Production

### Current MVP (Mock Classifier)

**Brightness Classifier**
- Uses average image brightness
- Darker → Fuller (hypothesis: more trash = more shadows)
- Simple threshold-based logic

**Edge Density Classifier**
- Uses Canny edge detection
- More edges → Fuller (hypothesis: more items = more edges)
- Simple ratio calculation

**Hybrid Classifier**
- Combines brightness + edge density
- Weighted averaging of predictions

### Production Requirements

To make this production-ready:

#### 1. Collect Training Data
```bash
# Collect 1000+ images per class
# Label as EMPTY/HALF/FULL
# Split: 70% train, 15% val, 15% test
```

#### 2. Train CNN Classifier
```python
# See TODOs in ai/classification/fill_level_classifier.py
# Suggested architectures:
#   - ResNet18/34 (transfer learning from ImageNet)
#   - EfficientNet-B0 (mobile-optimized)
#   - MobileNetV3 (edge deployment)
```

#### 3. Fine-tune YOLO on Custom Dataset
```bash
# Label custom trash bin dataset
# Fine-tune YOLOv8 on bins specifically
# See TODOs in ai/detection/yolo_detector.py
```

#### 4. Production Deployment
```bash
# Add database (PostgreSQL)
# Add Redis caching
# Add authentication
# Add monitoring (Prometheus)
# Add CI/CD pipeline
# Deploy with Docker + Kubernetes
```

## 🐛 Troubleshooting

### Models Not Loading

```bash
# Ensure YOLOv8 can download weights
pip install --upgrade ultralytics

# Test YOLO installation
python -c "from ultralytics import YOLO; model = YOLO('yolov8n.pt')"
```

### CUDA/GPU Issues

```bash
# Check PyTorch CUDA support
python -c "import torch; print(torch.cuda.is_available())"

# Install CUDA-enabled PyTorch
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Dashboard Not Connecting to API

1. Ensure backend is running on port 8000
2. Check CORS settings in `backend/main.py`
3. Verify dashboard is using correct API URL in `dashboard/src/app/page.tsx`

### Video Not Found

```bash
# Use absolute paths
# Example: /home/user/videos/street.mp4
# Or relative to project root: data/videos/street.mp4
```

## 📚 Technology Stack

### Backend & AI
- **Python 3.10+**
- **FastAPI** - Web framework
- **Pydantic** - Data validation
- **OpenCV** - Computer vision
- **YOLOv8 (Ultralytics)** - Object detection
- **PyTorch** - Deep learning framework

### Frontend
- **React 18**
- **Next.js 14**
- **TypeScript**
- **Tailwind CSS**

### Development
- **Uvicorn** - ASGI server
- **No authentication** (MVP only)
- **Local storage** (no database)

## 🎯 Roadmap

### Phase 1: MVP (Current)
- ✅ YOLOv8 detection
- ✅ Mock classifier
- ✅ REST API
- ✅ Dashboard
- ✅ Clean architecture

### Phase 2: Production ML
- ⬜ Collect & label training dataset
- ⬜ Train CNN classifier
- ⬜ Fine-tune YOLO on custom bins
- ⬜ Model versioning & experiments tracking

### Phase 3: Production Infrastructure
- ⬜ PostgreSQL database
- ⬜ Redis caching
- ⬜ Authentication & authorization
- ⬜ Background job processing
- ⬜ Monitoring & alerting
- ⬜ Docker deployment

### Phase 4: Advanced Features
- ⬜ Real-time video streams
- ⬜ Multi-camera support
- ⬜ Fill rate prediction
- ⬜ Route optimization for collection
- ⬜ Mobile app
- ⬜ Notification system

## 📄 License

This is an MVP demonstration project. Not licensed for production use.

## 🤝 Contributing

This is a demonstration MVP. For production deployment, significant changes are needed (see TODOs in code).

## 📧 Support

For issues with setup or usage, check:
1. API documentation: http://localhost:8000/docs
2. Component test scripts in each module
3. Configuration in `ai/config.py`

## 🎓 Learning Resources

- **YOLOv8**: https://docs.ultralytics.com/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Computer Vision**: OpenCV documentation
- **React/Next.js**: https://nextjs.org/docs

---

**Built with clean architecture principles for easy extension and production deployment.**

**All TODOs and mock implementations are clearly marked in the code.**
