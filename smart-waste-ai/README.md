# Smart Waste Monitoring System 🗑️

AI-powered trash bin monitoring system using computer vision to detect bins and estimate fill levels from video footage.

## 📋 Overview

This MVP demonstrates a clean, modular architecture for smart city waste monitoring. The system analyzes street videos, detects trash bins using YOLOv8, estimates their fill level (Empty/Half/Full), and exposes results via REST API and web dashboard.

### Key Features

- **Object Detection**: YOLOv8-based trash bin detection
- **Fill Level Classification**: Mock classifier using brightness/edge density heuristics
- **Database Persistence**: PostgreSQL/SQLite support with Alembic migrations
- **Analysis History**: Track all analyses with full audit trail
- **REST API**: FastAPI backend with comprehensive endpoints for CRUD operations
- **File Upload**: Upload and analyze videos/images via web interface
- **Batch Upload**: Process multiple images simultaneously with aggregated results
- **Web Dashboard**: React/Next.js UI for real-time monitoring and history
- **Docker Deployment**: Production-ready docker-compose setup
- **Clean Architecture**: Modular, interface-based design
- **Debug Mode**: Save overlay images, cropped bins, and metadata for analysis
- **Evaluation Tools**: Built-in accuracy testing and confusion matrix generation
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

### Option 1: Using Run Script (Recommended)

The easiest way to get started:

```bash
# Navigate to project
cd smart-waste-ai

# Start with Docker (includes PostgreSQL)
./run.sh start

# OR start in local development mode (uses SQLite)
./run.sh start local

# OR start local walkscan mode (runs migrations first)
./run.sh start walkscan
```

**Access points:**
- Dashboard: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432 (Docker mode only)

**Useful commands:**
```bash
./run.sh status    # Check service status
./run.sh logs      # View logs (Docker mode)
./run.sh stop      # Stop all services
./run.sh migrate   # Run database migrations
./run.sh help      # Show all commands
```

### Option 2: Manual Setup

#### Prerequisites

- **Docker & Docker Compose**: For production deployment (recommended)
- **Python**: 3.10 or higher (for local development)
- **Node.js**: 18+ (for dashboard)
- **PostgreSQL**: 15+ (optional, SQLite used by default)

#### Docker Deployment

```bash
# Copy environment file
cp .env.example .env

# Start all services (PostgreSQL + Backend + Dashboard)
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# View logs
docker-compose logs -f
```

#### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
cd backend
alembic upgrade head
cd ..

# Start backend
python backend/main.py

# In another terminal, start dashboard
cd dashboard
npm install
npm run dev
```

**Access points:**
- Dashboard: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

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

---

## 🧠 Custom Model Training (Recommended)

The default `yolov8n.pt` is COCO and does **not** include a trash container class.

For production, train a custom single-class model named `trash_container` and place
the weights as `bins.pt` in the project root (auto-loaded), or set:

```bash
export YOLO_WEIGHTS_PATH=/absolute/path/to/best.pt
```

See `TRAINING.md` for the full dataset prep, training, and evaluation workflow.

### 6. Upload & Analyze Files (NEW!)

You can now upload video or image files directly for analysis!

#### Option A: Using the Dashboard (Easiest)

1. Open http://localhost:3000
2. Click **"Upload File"** button in the header
3. Select a video (.mp4, .avi, .mov) or image (.jpg, .png)
4. Click **"Analyze"**
5. View the result with color-coded status:
   - 🟢 **GREEN** = EMPTY
   - 🟠 **ORANGE** = HALF
   - 🔴 **RED** = FULL

---

## 🧪 Train a Custom Model (UI)

Open `http://localhost:3000/train` to:
- Upload images
- Draw one bounding box per image
- Auto split train/val
- Start YOLOv8 training and monitor progress
- Download `best.pt` and activate it for inference

For full details, see `TRAINING.md`.

## 🍎 Apple Silicon (MPS)

If you are on macOS with Apple Silicon:

```bash
pip install ultralytics torch torchvision
```

Use `device=mps` or `device=auto` during training.

---

## 📷 Live Camera Walk Scan

Open `http://localhost:3000/walk-scan` to run live bin detection from your webcam.

Controls:
- Start/Stop camera
- Clear captured bins
- Export JSON of captured bins
- Quality selector (Fast/Balanced/Accurate)
- Target FPS + confidence tuning

### Areas (Required)

1) Enter an **Area name** and click **Set Area**.
2) Start the camera. All captures are grouped under the active area.
3) Use **+ New Area** to switch to a new area (clears captures + starts a new session).
4) Areas can be deleted from the dashboard (this removes all bins/captures under the area).

### Admin Workflow (Dashboard)

The main dashboard shows **Areas** (one row per area). Open an area to browse bins and update operational status:

- Dashboard → Areas → Open → `/areas/<id>`
- Area cards include counts by last fill status and ops status.

- `NEW` → default when first captured
- `ON_PROCESS` → admin acknowledged
- `TRUCK_DISPATCHED` → truck assigned
- `EMPTIED` → cleared
- `FALSE_POSITIVE` → false positive / ignored

### Priority Scoring

Priority is computed automatically when captures or status change:

- `FULL` = 100, `HALF` = 60, `EMPTY` = 20
- + `round(fill_conf * 20)`
- + `min(capture_count * 2, 20)`
- `ON_PROCESS` = -10, `TRUCK_DISPATCHED` = -20
- `EMPTIED`/`FALSE_POSITIVE` = 0

### Export per Area

Use the dashboard **Export Area** button or call the API:

```
GET /api/v1/areas/{area_id}/export?format=json|csv
```

### Delete a Bin

```
DELETE /api/v1/bins/{bin_id}
```

### Delete an Area

```
DELETE /api/v1/areas/{area_id}
```

### Hard Negatives (False Positives)

When a bin is marked false positive, the latest capture is saved to:

```
data/training/hard_negatives/<area>/<timestamp>_<bin_id>.jpg
```

### Backend API (single frame)

```bash
curl -sS -X POST "http://localhost:8000/api/v1/analyze-frame" \
  -F "file=@/path/to/frame.jpg" \
  -F "area_id=1" \
  -F "conf=0.25" \
  -F "iou=0.7" \
  -F "imgsz=640" | python3 -m json.tool
```

### Backend API (capture)

```bash
./scripts/test_capture.sh /path/to/frame.jpg [area_id]
```

### Curl Examples (Areas + Admin)

```bash
# 1) Create/get area
curl -sS -X POST "http://localhost:8000/api/v1/areas" \
  -H "Content-Type: application/json" \
  -d '{"name":"Downtown"}' | python3 -m json.tool

# 1b) Create/get area (form-data)
curl -sS -X POST "http://localhost:8000/api/v1/areas" \
  -F "name=Downtown" | python3 -m json.tool

# 2) List areas with aggregates
curl -sS "http://localhost:8000/api/v1/areas" | python3 -m json.tool

# 3) Analyze frame with area_id
curl -sS -X POST "http://localhost:8000/api/v1/analyze-frame" \
  -F "file=@/path/to/frame.jpg" \
  -F "area_id=1" | python3 -m json.tool

# 4) List dashboard bins sorted by priority
curl -sS "http://localhost:8000/api/v1/dashboard/bins" | python3 -m json.tool

# 5) Patch bin status
curl -sS -X PATCH "http://localhost:8000/api/v1/bins/1" \
  -H "Content-Type: application/json" \
  -d '{"ops_status":"ON_PROCESS"}' | python3 -m json.tool

# 6) Mark false positive
curl -sS -X POST "http://localhost:8000/api/v1/bins/1/false-positive" \
  -H "Content-Type: application/json" \
  -d '{"note":"Not a real bin"}' | python3 -m json.tool

# 7) Export area JSON/CSV
curl -sS "http://localhost:8000/api/v1/areas/1/export?format=json" | python3 -m json.tool
curl -sS "http://localhost:8000/api/v1/areas/1/export?format=csv" -o area_1_bins.csv

# 8) Delete bin / area
curl -sS -X DELETE "http://localhost:8000/api/v1/bins/1"
curl -sS -X DELETE "http://localhost:8000/api/v1/areas/1"
```

### Optional Performance Hooks

Segmentation (stub):

```
ENABLE_SEGMENTATION=true
SEGMENTATION_BACKEND=sam2
```

TensorRT (Linux + NVIDIA only):

```
ENABLE_TENSORRT=true
TENSORRT_ENGINE_PATH=/path/to/model.engine
```

If the engine is missing or fails to load, the service falls back to normal YOLO weights.

#### Option B: Using cURL

```bash
# Upload and analyze a video file
curl -X POST "http://localhost:8000/api/v1/analyze-upload" \
  -F "file=@/path/to/your/video.mp4"

# Upload and analyze an image file
curl -X POST "http://localhost:8000/api/v1/analyze-upload" \
  -F "file=@/path/to/your/image.jpg"
```

#### Option C: Using Python

```python
import requests

# Upload video
with open('/path/to/video.mp4', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/analyze-upload',
        files={'file': f}
    )

result = response.json()
print(f"Status: {result['status']}")
print(f"Confidence: {result['confidence']}")
print(f"Bins detected: {result['bins_detected']}")
```

**Response Example:**
```json
{
  "input_type": "video",
  "status": "FULL",
  "confidence": 0.89,
  "bins_detected": 3,
  "message": "Video analysis complete"
}
```

**What happens:**
- **Videos**: Analyzes frames, detects bins, returns overall status
- **Images**: Detects bins in single frame, returns status
- **Result**: Simple summary with EMPTY/HALF/FULL + confidence score

### 7. Batch Upload (NEW!)

Upload and analyze multiple images at once for bulk processing!

#### Option A: Using the Dashboard (Easiest)

1. Open http://localhost:3000
2. Navigate to **Upload** page
3. Select **"Batch Upload"** mode
4. Choose **multiple images** (Ctrl/Cmd+Click to select multiple)
5. Review thumbnail previews
6. Click **"Analyze Batch"**
7. View summary with status counts
8. Click **"View Batch Details"** to see individual results

#### Option B: Using cURL

```bash
# Upload multiple images at once
curl -X POST "http://localhost:8000/api/v1/analyze-batch-upload" \
  -F "files=@/path/to/image1.jpg" \
  -F "files=@/path/to/image2.jpg" \
  -F "files=@/path/to/image3.jpg"
```

#### Option C: Using Python

```python
import requests

# Prepare files
files = [
    ('files', open('/path/to/image1.jpg', 'rb')),
    ('files', open('/path/to/image2.jpg', 'rb')),
    ('files', open('/path/to/image3.jpg', 'rb'))
]

# Upload batch
response = requests.post(
    'http://localhost:8000/api/v1/analyze-batch-upload',
    files=files
)

# Close handles
for _, f in files:
    f.close()

result = response.json()
print(f"Batch ID: {result['batch_id']}")
print(f"Status Counts: {result['status_counts']}")
```

**Response Example:**
```json
{
  "batch_id": "batch_20250101_123045_a1b2c3d4",
  "total_files": 3,
  "status_counts": {
    "EMPTY": 1,
    "HALF": 1,
    "FULL": 1,
    "NO_BIN_DETECTED": 0
  },
  "items": [
    {
      "id": 1,
      "filename": "image1.jpg",
      "status": "EMPTY",
      "confidence": 0.85,
      "bins_detected": 2
    }
  ]
}
```

**What you can do:**
- Process 10-100+ images simultaneously
- View aggregated status counts
- Browse individual item results
- Download artifacts (overlays, cropped bins)
- Track batch history

**See full documentation:** [BATCH_UPLOAD_GUIDE.md](BATCH_UPLOAD_GUIDE.md)

## 📊 API Endpoints

### Health & Status

- `GET /api/v1/health` - Health check (includes database connectivity)
- `GET /api/v1/service-info` - Service information

### Bin Status (Real-time)

- `GET /api/v1/bins-status` - Get all bin statuses from latest analysis
- `GET /api/v1/bins-status/{bin_id}` - Get specific bin status

### Analysis Operations

- `POST /api/v1/analyze-video` - Analyze a video file from server path
- `POST /api/v1/analyze-upload` - Upload and analyze video/image file
- `POST /api/v1/analyze-batch-upload` - Upload and analyze multiple images (NEW!)

### Batch Operations (NEW!)

- `GET /api/v1/batches` - List all batch uploads with pagination
- `GET /api/v1/batches/{batch_id}` - Get batch details with summary
- `GET /api/v1/batches/{batch_id}/items` - Get all items in a batch
- `GET /api/v1/batch-items/{item_id}` - Get item details with artifacts

### Analysis History

- `GET /api/v1/analyses` - List all analyses with pagination and filtering
  - Query params: `skip`, `limit`, `status_filter`, `input_type_filter`, `sort_by`, `sort_order`
- `GET /api/v1/analyses/{id}` - Get detailed analysis with bins and artifacts
- `GET /api/v1/analyses/summary` - Get summary statistics for all analyses

### Artifacts (NEW!)

- `GET /api/v1/artifacts/{id}` - Download or view artifact file (overlay images, cropped bins, metadata)

### Utilities

- `POST /api/v1/clear-cache` - Clear bin status cache

**See full API documentation at:** http://localhost:8000/docs

## 🔧 Configuration

Configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

### Database Configuration

```bash
# PostgreSQL (production - Docker)
DATABASE_URL=postgresql://smart_waste_user:password@localhost:5432/smart_waste

# SQLite (development - local)
DATABASE_URL=sqlite:///./data/smart_waste.db
```

### Backend Settings

```bash
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
MAX_UPLOAD_SIZE_MB=100
STORE_UPLOADED_FILES=true
DEBUG_MODE=false
```

### AI Configuration (ai/config.py)

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

## 🐛 DEBUG MODE

Enable debug mode to save detailed artifacts for analysis and debugging.

### Enable Debug Mode

```bash
# Set environment variable
export DEBUG_MODE=true

# Or add to .env file
echo "DEBUG_MODE=true" >> .env

# Start backend
python backend/main.py
```

### What Debug Mode Does

When enabled, the `/analyze-upload` endpoint will save:

1. **Overlay Image** (`data/results/debug/overlay_*.jpg`)
   - Original image with bounding boxes
   - Color-coded by fill level (Green=EMPTY, Orange=HALF, Red=FULL)
   - Labels showing fill level and confidence

2. **Cropped Bins** (`data/results/debug/bin_*_*.jpg`)
   - Individual cropped images for each detected bin
   - Exact images used for classification

3. **Metadata JSON** (`data/results/debug/metadata_*.json`)
   - Classifier name and mode
   - Raw scores (brightness, edge density, etc.)
   - Thresholds used for classification
   - Bounding box coordinates
   - Detection and classification confidence

### Example Debug Artifacts

```json
{
  "analysis_id": "20251223_143000_a1b2c3",
  "timestamp": "2025-12-23T14:30:00",
  "input_type": "image",
  "bins_detected": 2,
  "overall_status": "HALF",
  "overall_confidence": 0.72,
  "bins": [
    {
      "bin_index": 0,
      "bbox": [100, 150, 300, 500],
      "detection_confidence": 0.89,
      "fill_level": "HALF",
      "classification_confidence": 0.72,
      "classifier_metadata": {
        "method": "brightness",
        "avg_brightness": 120.5,
        "threshold_empty": 150,
        "threshold_half": 100
      }
    }
  ]
}
```

## 📊 Evaluate Classifier Accuracy

Test your classifier on a labeled dataset to measure accuracy.

### Prepare Evaluation Dataset

Create a folder with subfolders for each class:

```
data/evaluation_set/
├── empty/          # Images of empty bins
├── half/           # Images of half-full bins
├── full/           # Images of full bins
└── no_bin/         # Images with no bins detected
```

### Run Evaluation

```bash
python scripts/evaluate_images.py \
  --input data/evaluation_set \
  --output data/results/eval_report.json \
  --mistakes data/results/mistakes \
  --classifier brightness \
  --max-mistakes 5
```

### Output

**Evaluation Report** (`data/results/eval_report.json`):
- Overall accuracy
- Per-class precision, recall, F1-score
- Confusion matrix
- Configuration used

**Mistake Examples** (`data/results/mistakes/`):
- Images of misclassified bins
- Filename shows: `{ground_truth}_predicted_{prediction}_{n}.jpg`
- Text overlay with GT, prediction, and confidence

### Example Output

```
EVALUATION SUMMARY
============================================================
Total images: 100
Correct: 75
Accuracy: 75.00%

Per-class metrics:

  EMPTY:
    Precision: 80.00%
    Recall:    85.00%
    F1-score:  0.8235
    Support:   25

  HALF:
    Precision: 70.00%
    Recall:    65.00%
    F1-score:  0.6744
    Support:   25

  FULL:
    Precision: 75.00%
    Recall:    80.00%
    F1-score:  0.7742
    Support:   25

  NO_BIN_DETECTED:
    Precision: 100.00%
    Recall:    100.00%
    F1-score:  1.0000
    Support:   25
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
- ✅ File upload (single and batch)
- ✅ Batch processing with aggregated results
- ✅ Analysis history and artifacts

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
