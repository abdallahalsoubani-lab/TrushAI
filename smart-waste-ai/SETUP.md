# Setup Guide

Detailed installation and configuration instructions for the Smart Waste Monitoring System.

## System Requirements

### Minimum Requirements
- **OS**: Linux, macOS, or Windows 10/11
- **Python**: 3.10 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB free space (for models and dependencies)
- **CPU**: Multi-core processor recommended

### Optional (for better performance)
- **GPU**: NVIDIA GPU with CUDA support
- **CUDA**: 11.8 or higher
- **RAM**: 16GB+ for processing large videos

## Step-by-Step Installation

### 1. Python Environment Setup

#### Option A: Using venv (Recommended)

```bash
# Navigate to project
cd smart-waste-ai

# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.10.x
```

#### Option B: Using conda

```bash
# Create conda environment
conda create -n smart-waste python=3.10

# Activate environment
conda activate smart-waste
```

### 2. Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```

This will install:
- FastAPI & Uvicorn (API)
- OpenCV (Computer Vision)
- YOLOv8 via Ultralytics
- PyTorch (Deep Learning)
- Pydantic (Validation)
- NumPy (Numerical Computing)

### 3. GPU Support (Optional)

#### For NVIDIA GPUs with CUDA

```bash
# Uninstall CPU-only PyTorch
pip uninstall torch torchvision

# Install CUDA-enabled PyTorch (CUDA 11.8)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Verify CUDA is available
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

#### For Apple Silicon (M1/M2)

PyTorch with MPS (Metal Performance Shaders) is included by default.

```bash
# Verify MPS is available
python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

### 4. Verify Installation

```bash
# Run installation test script
python test_installation.py
```

This will verify:
- ✅ All packages are installed
- ✅ Project structure is correct
- ✅ YOLOv8 can be loaded
- ✅ PyTorch/CUDA is configured
- ✅ Custom modules import correctly

### 5. Configure Settings (Optional)

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env  # or use your preferred editor
```

Available settings:
- `LOG_LEVEL` - Logging verbosity (DEBUG/INFO/WARNING)
- `YOLO_MODEL_SIZE` - Model size (n/s/m/l/x)
- `YOLO_DEVICE` - Device (cpu/cuda/mps)
- `MOCK_CLASSIFIER_MODE` - Classifier type (brightness/edge_density/hybrid)

### 6. First Run - Backend

```bash
# Start the backend API
python backend/main.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

Test the API:
```bash
# In another terminal
curl http://localhost:8000/api/v1/health
```

### 7. Dashboard Setup (Optional)

```bash
# Navigate to dashboard
cd dashboard

# Install Node.js dependencies
npm install

# Start development server
npm run dev
```

Open browser: http://localhost:3000

## Common Issues & Solutions

### Issue: YOLOv8 fails to download

**Symptom**: `Failed to download yolov8n.pt`

**Solution**:
```bash
# Download manually
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Or specify path to local weights
# Edit ai/config.py and set path to downloaded weights
```

### Issue: OpenCV error - libGL.so.1 not found

**Symptom**: `ImportError: libGL.so.1: cannot open shared object file`

**Solution** (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
```

**Solution** (CentOS/RHEL):
```bash
sudo yum install -y mesa-libGL
```

### Issue: CUDA out of memory

**Symptom**: `RuntimeError: CUDA out of memory`

**Solution**:
1. Use smaller YOLO model (n instead of m/l/x)
2. Process fewer frames (`max_frames=20`)
3. Reduce batch size
4. Use CPU mode: `YOLO_DEVICE=cpu` in config

### Issue: Port 8000 already in use

**Symptom**: `Address already in use`

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in config
# Edit ai/config.py: API_PORT = 8001
```

### Issue: Dashboard can't connect to API

**Symptom**: Dashboard shows "Failed to fetch data"

**Solution**:
1. Ensure backend is running: `curl http://localhost:8000/api/v1/health`
2. Check CORS settings in `backend/main.py`
3. Verify API URL in dashboard (should be `http://localhost:8000`)

### Issue: Video file not found

**Symptom**: `FileNotFoundError: Video not found`

**Solution**:
1. Use absolute path: `/home/user/videos/street.mp4`
2. Or place video in `data/videos/` and use: `data/videos/street.mp4`
3. Ensure video format is supported (mp4, avi, mov, mkv)

## Performance Optimization

### For Faster Processing

1. **Use GPU**:
```python
# In ai/config.py
YOLO_DEVICE = "cuda"  # or "mps" for Mac
```

2. **Use smaller model**:
```python
YOLO_MODEL_SIZE = "n"  # nano is fastest
```

3. **Process fewer frames**:
```python
FRAME_EXTRACTION_RATE = 5  # 1 frame every 5 seconds
MAX_FRAMES_PER_VIDEO = 20
```

4. **Disable visualizations**:
```python
SAVE_VISUALIZATIONS = False
```

### For Better Accuracy

1. **Use larger model**:
```python
YOLO_MODEL_SIZE = "m"  # or "l" for even better accuracy
```

2. **Lower confidence threshold**:
```python
YOLO_CONFIDENCE_THRESHOLD = 0.15  # detect more bins
```

3. **Process more frames**:
```python
FRAME_EXTRACTION_RATE = 1  # every second
MAX_FRAMES_PER_VIDEO = 100
```

## Testing the System

### 1. Test with sample video

Download a test video:
```bash
# Example: Download from Pexels (free stock videos)
# Or use your own street video

# Place in data/videos/
mkdir -p data/videos
cp /path/to/your/video.mp4 data/videos/test.mp4
```

### 2. Analyze the video

Using curl:
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-video" \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "data/videos/test.mp4",
    "frame_skip": 2,
    "max_frames": 30
  }'
```

Using Python:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/analyze-video",
    json={
        "video_path": "data/videos/test.mp4",
        "frame_skip": 2,
        "max_frames": 30
    }
)

print(response.json())
```

### 3. View results

```bash
# Get bin status
curl http://localhost:8000/api/v1/bins-status

# Or view in dashboard
# Open http://localhost:3000
```

### 4. Check visualizations

Results are saved in `data/results/visualizations/`

```bash
ls -l data/results/visualizations/
```

## Development Tips

### Running in development mode

```bash
# Backend with auto-reload
python backend/main.py  # API_RELOAD=True by default

# Dashboard with hot reload
cd dashboard && npm run dev
```

### Testing individual components

```bash
# Test detector
python -m ai.detection.yolo_detector

# Test classifier
python -m ai.classification.fill_level_classifier

# Test pipeline
python -m ai.inference.pipeline

# Extract frames manually
python scripts/extract_frames.py --video data/videos/test.mp4
```

### Logging

Enable debug logging:
```bash
# In .env or ai/config.py
LOG_LEVEL=DEBUG
```

View logs:
```bash
# Backend logs to console
# Check terminal where you ran `python backend/main.py`
```

## Next Steps

Once everything is working:

1. **Collect training data** for custom classifier
2. **Label images** as EMPTY/HALF/FULL
3. **Train CNN model** (see TODOs in code)
4. **Fine-tune YOLO** on custom trash bin dataset
5. **Deploy to production** with Docker

## Getting Help

If you encounter issues:

1. Check this SETUP.md guide
2. Run `python test_installation.py`
3. Check logs in console output
4. Review configuration in `ai/config.py`
5. Consult API docs at http://localhost:8000/docs

## Additional Resources

- **YOLOv8 Docs**: https://docs.ultralytics.com/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **OpenCV Docs**: https://docs.opencv.org/
- **PyTorch Docs**: https://pytorch.org/docs/

---

**Ready to start? Run `python test_installation.py` to verify your setup!**
