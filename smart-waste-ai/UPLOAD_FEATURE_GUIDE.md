# File Upload & Analysis Feature Guide

## 🎉 New Feature: Upload & Analyze

You can now upload video or image files directly to the Smart Waste Monitoring system for instant analysis!

---

## 📋 Overview

This feature allows you to:
- **Upload videos** (.mp4, .avi, .mov, .mkv) for multi-frame analysis
- **Upload images** (.jpg, .jpeg, .png) for single-frame analysis
- Get **instant results** with fill level status and confidence score
- Use via **web dashboard** (easiest) or **API** (programmatic)

---

## 🌐 Using the Web Dashboard (Easiest Method)

### Step 1: Start the Backend

```bash
cd smart-waste-ai
python backend/main.py
```

Backend will run on http://localhost:8000

### Step 2: Start the Dashboard

```bash
cd dashboard
npm install  # First time only
npm run dev
```

Dashboard will run on http://localhost:3000

### Step 3: Upload & Analyze

1. Open http://localhost:3000 in your browser
2. Click the **"Upload File"** button in the header (green button)
3. You'll be taken to the upload page
4. Click **"Select File"** and choose:
   - A video file (.mp4, .avi, .mov)
   - OR an image file (.jpg, .png)
5. See a preview (for images) or filename (for videos)
6. Click **"Analyze"**
7. Wait for processing (loading spinner will show)
8. View the result:
   - 🟢 **GREEN** badge = EMPTY bin
   - 🟠 **ORANGE** badge = HALF full bin
   - 🔴 **RED** badge = FULL bin
   - Confidence percentage
   - Number of bins detected

### Step 4: Upload Another File

Click **"Clear"** button to reset and upload another file.

---

## 🔌 Using the API

### Method 1: Using cURL (Terminal)

#### Upload Video:
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-upload" \
  -F "file=@/path/to/your/video.mp4"
```

#### Upload Image:
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-upload" \
  -F "file=@/path/to/your/image.jpg"
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

### Method 2: Using Python

```python
import requests

# Upload and analyze video
with open('/path/to/video.mp4', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/v1/analyze-upload',
        files={'file': f}
    )

result = response.json()

print(f"Input Type: {result['input_type']}")
print(f"Status: {result['status']}")
print(f"Confidence: {result['confidence']:.0%}")
print(f"Bins Detected: {result['bins_detected']}")
print(f"Message: {result['message']}")
```

**Output:**
```
Input Type: video
Status: FULL
Confidence: 89%
Bins Detected: 3
Message: Video analysis complete
```

### Method 3: Using JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/v1/analyze-upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result);
```

### Method 4: Using Interactive API Docs

1. Open http://localhost:8000/docs
2. Find `POST /api/v1/analyze-upload`
3. Click **"Try it out"**
4. Click **"Choose File"** and select your video/image
5. Click **"Execute"**
6. View the response below

---

## 📊 API Response Schema

```typescript
{
  input_type: string;      // "video" or "image"
  status: string;          // "EMPTY" | "HALF" | "FULL"
  confidence: number;      // 0.0 - 1.0 (e.g., 0.89 = 89%)
  bins_detected: number;   // Number of bins found (0 if none)
  message?: string;        // Additional info (e.g., "No bins detected")
}
```

### Status Values

| Status | Meaning | Color Code |
|--------|---------|------------|
| `EMPTY` | Bin is empty | 🟢 Green |
| `HALF` | Bin is half full | 🟠 Orange |
| `FULL` | Bin is full | 🔴 Red |

### Confidence Score

- **Range**: 0.0 to 1.0 (0% to 100%)
- **Interpretation**:
  - 0.9+ → Very confident
  - 0.7-0.9 → Confident
  - 0.5-0.7 → Moderate confidence
  - <0.5 → Low confidence

---

## 🎬 How It Works

### For Videos:

1. **Upload**: File is saved to temporary directory
2. **Frame Extraction**: Every 3 seconds (optimized for speed)
3. **Detection**: YOLOv8 detects trash bins in each frame
4. **Classification**: Mock classifier estimates fill level
5. **Tracking**: Same bins tracked across frames using IoU
6. **Aggregation**: Conservative approach - returns fullest bin status
7. **Cleanup**: Temporary file is automatically deleted
8. **Response**: Returns overall status + confidence

**Example:**
- Video has 3 bins detected
- Bin 1: EMPTY (0.7 confidence)
- Bin 2: HALF (0.8 confidence)
- Bin 3: FULL (0.9 confidence)
- **Result**: Status = FULL, Confidence = 0.9

### For Images:

1. **Upload**: File is saved to temporary directory
2. **Detection**: YOLOv8 detects trash bins in image
3. **Classification**: Estimates fill level for each bin
4. **Aggregation**: Returns fullest bin status
5. **Cleanup**: Temporary file is deleted
6. **Response**: Returns overall status + confidence

---

## ⚙️ Supported File Formats

### Videos
- `.mp4` (MPEG-4)
- `.avi` (Audio Video Interleave)
- `.mov` (QuickTime)
- `.mkv` (Matroska)

### Images
- `.jpg` / `.jpeg` (JPEG)
- `.png` (PNG)

**File Size Limits:**
- No hard limit enforced (TODO: Add in production)
- Recommended: <100MB for videos, <10MB for images
- Larger files take longer to process

---

## 🛠️ Technical Details

### Backend Endpoint

**URL**: `POST /api/v1/analyze-upload`

**Content-Type**: `multipart/form-data`

**Parameters**:
- `file` (required): The video or image file to upload

**Processing**:
- Videos: Process every 3 seconds, max 30 frames
- Images: Single frame analysis
- Temporary file cleanup after processing
- Conservative aggregation (fullest bin wins)

**Error Handling**:
- 400: Invalid file format
- 503: Models not loaded
- 500: Analysis failed

### Frontend Page

**Route**: `/upload`

**Features**:
- File input with format validation
- Image preview for .jpg/.png files
- Video filename display for video files
- Loading state during analysis
- Color-coded result display
- Clear button to reset form
- Navigation back to dashboard

**Components**:
- TypeScript for type safety
- Tailwind CSS for styling
- React hooks for state management
- Fetch API for backend communication

---

## 📝 Example Workflows

### Workflow 1: Quick Image Check

```bash
# Take a photo of a trash bin
# Upload via dashboard
# Get instant EMPTY/HALF/FULL status
# Decision: Empty bin? No action needed
#          Full bin? Schedule pickup
```

### Workflow 2: Video Monitoring

```bash
# Record video of street with multiple bins
# Upload video
# System detects all bins automatically
# Get overall status (most full bin)
# Use for route optimization
```

### Workflow 3: Automated Monitoring

```python
import requests
import os

# Directory with daily monitoring images
image_dir = "/monitoring/images"

for filename in os.listdir(image_dir):
    if filename.endswith(('.jpg', '.png')):
        filepath = os.path.join(image_dir, filename)

        with open(filepath, 'rb') as f:
            response = requests.post(
                'http://localhost:8000/api/v1/analyze-upload',
                files={'file': f}
            )

        result = response.json()

        # Log results
        print(f"{filename}: {result['status']} ({result['confidence']:.0%})")

        # Alert if full
        if result['status'] == 'FULL' and result['confidence'] > 0.7:
            send_alert(f"Bin full detected: {filename}")
```

---

## 🔍 Troubleshooting

### Issue: "Invalid file format"

**Cause**: Uploaded file type not supported

**Solution**: Ensure file is:
- Video: .mp4, .avi, .mov, .mkv
- Image: .jpg, .jpeg, .png

### Issue: "No bins detected"

**Cause**: No trash bins found in uploaded file

**Solutions**:
- Ensure image/video contains visible trash bins
- Check image quality (not blurry)
- Ensure bins are prominent in frame
- Try different angle or lighting

### Issue: "Connection refused" or "Failed to fetch"

**Cause**: Backend not running

**Solution**:
```bash
# Start backend
cd smart-waste-ai
python backend/main.py
```

### Issue: Low confidence scores

**Cause**: Mock classifier limitations (MVP)

**Solution**: This is expected for MVP
- Current: Mock classifier using brightness/edges
- Production: Train CNN on real trash bin data
- See TODOs in code for ML training pipeline

---

## 🚀 Next Steps (TODOs)

### Immediate Improvements
- [ ] Add file size limits (e.g., 100MB for videos)
- [ ] Add drag-and-drop file upload
- [ ] Add progress bar for upload
- [ ] Add virus scanning for uploaded files

### Future Features
- [ ] Multiple file upload (batch processing)
- [ ] Save analysis history to database
- [ ] Display detected bins on image/video frame
- [ ] Export results to CSV/JSON
- [ ] Email notifications for full bins
- [ ] Integration with waste collection routes

### ML Improvements
- [ ] Train CNN classifier on real data
- [ ] Fine-tune YOLO on custom trash bin dataset
- [ ] Add uncertainty quantification
- [ ] Improve aggregation logic with weighted voting

---

## 📞 Support

If you encounter issues:

1. **Check backend logs**: Terminal where `python backend/main.py` runs
2. **Check browser console**: F12 → Console tab (for dashboard issues)
3. **Test API directly**: Use http://localhost:8000/docs
4. **Verify file format**: Ensure using supported formats
5. **Check file size**: Very large files may timeout

---

## 🎓 Comparison: Upload vs. File Path Analysis

| Feature | Upload (`/analyze-upload`) | File Path (`/analyze-video`) |
|---------|---------------------------|----------------------------|
| **Method** | Upload file via form-data | Provide file path on server |
| **Use Case** | External users, web UI | Internal batch processing |
| **File Location** | User's computer | Server filesystem |
| **Processing** | Temporary file | Direct file access |
| **Speed** | Upload time + processing | Processing only |
| **Cleanup** | Automatic | Manual |
| **Result** | Summary (status + confidence) | Full details (all bins) |
| **Best For** | Quick checks, web users | Automated pipelines, scripts |

---

## ✅ Summary

**What you can do now:**
1. ✅ Upload videos or images via web dashboard
2. ✅ Upload via API (cURL, Python, JavaScript)
3. ✅ Get instant fill level analysis
4. ✅ See confidence scores and bin counts
5. ✅ Navigate between dashboard and upload page

**Key Benefits:**
- 🚀 **Fast**: Optimized processing (3-sec frame skip)
- 🎯 **Simple**: Single status result (EMPTY/HALF/FULL)
- 🔒 **Safe**: Automatic temp file cleanup
- 💡 **Easy**: Web UI for non-technical users
- 🔌 **Flexible**: API for automated workflows

**Ready to use!** Start uploading and analyzing your trash bin videos and images now! 🎉

---

**All code committed to branch: `claude/smart-city-waste-monitoring-8Tyk0`**
