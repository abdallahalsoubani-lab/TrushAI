# Batch Image Upload Feature Guide

## 🎉 New Feature: Batch Upload & Analysis

You can now upload **multiple images at once** to the Smart Waste Monitoring system for bulk analysis!

---

## 📋 Overview

This feature allows you to:
- **Upload multiple images** (.jpg, .jpeg, .png, .webp) simultaneously
- Process **hundreds of images** in a single batch
- Get **aggregated results** with status counts breakdown
- View **individual item details** with artifacts and overlays
- Track **batch processing status** and errors
- **Manage and review** past batches

---

## 🌐 Using the Web Dashboard

### Step 1: Start the Backend and Dashboard

```bash
# Start backend
cd smart-waste-ai
python backend/main.py

# In another terminal, start dashboard
cd dashboard
npm install  # First time only
npm run dev
```

Backend: http://localhost:8000
Dashboard: http://localhost:3000

### Step 2: Upload Multiple Images

1. Open http://localhost:3000 in your browser
2. Navigate to the **Upload** page
3. Select **"Batch Upload"** mode (toggle button at top)
4. Click **"Select Multiple Images"**
5. Select **multiple image files** (Ctrl/Cmd+Click or Shift+Click)
6. Review the **thumbnail previews** of selected images
7. Click **"Analyze Batch"**
8. Wait for processing (progress indicator shows)
9. View the **batch summary** with status counts
10. Click **"View Batch Details"** to see individual results

### Step 3: View Batch Results

**On the Batches List Page:**
- See all recent batch uploads
- Filter by status (All/Completed/Processing/Failed)
- View summary counts for each batch
- Navigate to batch details

**On Batch Details Page:**
- View full batch metadata
- See status distribution breakdown
- Browse paginated table of all items
- Click on individual items for details

**On Batch Item Details Page:**
- View original image analysis
- See overlay image with detected bins
- Download cropped bin images
- Access debug artifacts
- View confidence scores and metadata

---

## 🔌 Using the API

### Method 1: Using cURL (Terminal)

```bash
curl -X POST "http://localhost:8000/api/v1/analyze-batch-upload" \
  -F "files=@/path/to/image1.jpg" \
  -F "files=@/path/to/image2.jpg" \
  -F "files=@/path/to/image3.jpg"
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
    },
    {
      "id": 2,
      "filename": "image2.jpg",
      "status": "HALF",
      "confidence": 0.78,
      "bins_detected": 1
    },
    {
      "id": 3,
      "filename": "image3.jpg",
      "status": "FULL",
      "confidence": 0.92,
      "bins_detected": 3
    }
  ],
  "internal_batch_id": 42
}
```

### Method 2: Using Python

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

# Close file handles
for _, file_handle in files:
    file_handle.close()

# Parse result
result = response.json()

print(f"Batch ID: {result['batch_id']}")
print(f"Total Files: {result['total_files']}")
print(f"\nStatus Counts:")
for status, count in result['status_counts'].items():
    print(f"  {status}: {count}")

print(f"\nItems:")
for item in result['items']:
    print(f"  {item['filename']}: {item['status']} ({item['confidence']:.0%})")
```

**Output:**
```
Batch ID: batch_20250101_123045_a1b2c3d4
Total Files: 3

Status Counts:
  EMPTY: 1
  HALF: 1
  FULL: 1
  NO_BIN_DETECTED: 0

Items:
  image1.jpg: EMPTY (85%)
  image2.jpg: HALF (78%)
  image3.jpg: FULL (92%)
```

### Method 3: Using JavaScript/Fetch

```javascript
// Get files from input
const fileInput = document.querySelector('input[type="file"]');
const files = fileInput.files;

// Create FormData
const formData = new FormData();
for (let i = 0; i < files.length; i++) {
  formData.append('files', files[i]);
}

// Upload batch
const response = await fetch('http://localhost:8000/api/v1/analyze-batch-upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log('Batch ID:', result.batch_id);
console.log('Status Counts:', result.status_counts);
```

---

## 📊 Batch API Endpoints

### 1. Upload Batch

**Endpoint:** `POST /api/v1/analyze-batch-upload`

**Request:**
- Content-Type: `multipart/form-data`
- Field: `files` (multiple files)
- Accepts: `.jpg`, `.jpeg`, `.png`, `.webp`

**Response:**
```typescript
{
  batch_id: string;              // Unique batch identifier
  total_files: number;           // Number of images uploaded
  status_counts: {               // Aggregated results
    EMPTY: number;
    HALF: number;
    FULL: number;
    NO_BIN_DETECTED: number;
  };
  items: Array<{                 // Individual item summaries
    id: number;
    filename: string;
    status: string;
    confidence: number;
    bins_detected: number;
  }>;
  internal_batch_id?: number;    // Database ID (for navigation)
}
```

### 2. List Batches

**Endpoint:** `GET /api/v1/batches`

**Query Parameters:**
- `skip` (default: 0) - Pagination offset
- `limit` (default: 20) - Items per page
- `status` (optional) - Filter by status: "processing", "completed", "failed"

**Response:**
```typescript
{
  batches: Array<Batch>;
  total: number;
  skip: number;
  limit: number;
}
```

### 3. Get Batch Details

**Endpoint:** `GET /api/v1/batches/{batch_id}`

**Response:**
```typescript
{
  id: number;
  batch_id: string;
  total_files: number;
  status_counts: {
    EMPTY: number;
    HALF: number;
    FULL: number;
    NO_BIN_DETECTED: number;
  };
  created_at: string;
  completed_at: string | null;
  processing_status: "processing" | "completed" | "failed";
  error_message: string | null;
  failed_count: number;
}
```

### 4. Get Batch Items

**Endpoint:** `GET /api/v1/batches/{batch_id}/items`

**Query Parameters:**
- `skip` (default: 0)
- `limit` (default: 100)

**Response:**
```typescript
{
  items: Array<BatchItem>;
  total: number;
  skip: number;
  limit: number;
}
```

### 5. Get Batch Item Details

**Endpoint:** `GET /api/v1/batch-items/{item_id}`

**Response:**
```typescript
{
  id: number;
  batch_id: number;
  original_filename: string;
  stored_path: string;
  status: "EMPTY" | "HALF" | "FULL" | "NO_BIN_DETECTED";
  confidence: number;
  bins_detected: number;
  created_at: string;
  completed_at: string | null;
  processing_status: string;
  error_message: string | null;
  artifacts: Array<{
    id: number;
    type: "overlay" | "cropped_bin" | "debug_json";
    path: string;
    bin_index: number | null;
    file_size: number | null;
    mime_type: string | null;
  }>;
}
```

---

## 🎬 How Batch Processing Works

### Processing Pipeline

1. **Validation**
   - All files validated before processing starts
   - Only image formats accepted (no videos)
   - Invalid files rejected with error message

2. **Batch Creation**
   - Unique batch ID generated: `batch_YYYYMMDD_HHMMSS_<uuid>`
   - Batch record created in database
   - Processing status set to "processing"

3. **File Storage**
   - Each file saved to: `data/results/analyses/{batch_id}/{index}_{filename}`
   - Original filenames preserved with index prefix
   - Batch items created in database

4. **Image Analysis** (for each image)
   - YOLOv8 bin detection
   - Fill level classification
   - Artifact generation (overlay, cropped bins, debug JSON)
   - Results saved to database

5. **Batch Completion**
   - Status counts aggregated
   - Processing status set to "completed"
   - Failed count tracked
   - Completion timestamp recorded

### Storage Structure

```
data/results/analyses/
└── batch_20250101_123045_a1b2c3d4/
    ├── 0000_image1.jpg
    ├── 0000_image1_overlay.jpg
    ├── 0000_image1_bin_0.jpg
    ├── 0000_image1_debug.json
    ├── 0001_image2.jpg
    ├── 0001_image2_overlay.jpg
    ├── 0001_image2_bin_0.jpg
    ├── 0001_image2_debug.json
    └── ...
```

---

## 📝 Example Workflows

### Workflow 1: Daily Monitoring

```python
import requests
import os
from datetime import datetime

# Directory with today's monitoring images
image_dir = "/monitoring/images/2025-01-01"
images = [f for f in os.listdir(image_dir) if f.endswith(('.jpg', '.png'))]

# Upload batch
files = [('files', open(os.path.join(image_dir, img), 'rb')) for img in images]
response = requests.post(
    'http://localhost:8000/api/v1/analyze-batch-upload',
    files=files
)

# Close handles
for _, f in files:
    f.close()

result = response.json()

# Generate report
print(f"Daily Report - {datetime.now()}")
print(f"Total Images: {result['total_files']}")
print(f"Empty Bins: {result['status_counts']['EMPTY']}")
print(f"Half Full: {result['status_counts']['HALF']}")
print(f"Full Bins: {result['status_counts']['FULL']}")
print(f"No Bins: {result['status_counts']['NO_BIN_DETECTED']}")

# Alert if any full bins
if result['status_counts']['FULL'] > 0:
    send_alert(f"{result['status_counts']['FULL']} full bins detected!")
```

### Workflow 2: Route Coverage Analysis

```bash
# Upload all images from a collection route
curl -X POST "http://localhost:8000/api/v1/analyze-batch-upload" \
  $(for img in route_1/*.jpg; do echo "-F files=@$img"; done)

# Review results on dashboard
# Navigate to /batches
# Click on latest batch
# Export results for route optimization
```

### Workflow 3: Historical Comparison

```python
import requests

# Get all batches from last week
response = requests.get('http://localhost:8000/api/v1/batches?limit=100')
batches = response.json()['batches']

# Analyze trends
for batch in batches:
    full_count = batch['status_counts']['FULL']
    total = batch['total_files']
    full_rate = (full_count / total * 100) if total > 0 else 0

    print(f"{batch['batch_id']}: {full_rate:.1f}% full bins")

    if full_rate > 50:
        print(f"  ⚠️  High full bin rate detected!")
```

---

## 🛠️ Technical Details

### Database Schema

**BatchAnalysis Table:**
```sql
CREATE TABLE batch_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id VARCHAR(64) UNIQUE NOT NULL,
    total_files INTEGER NOT NULL,
    status_counts TEXT,  -- JSON: {"EMPTY": 5, "HALF": 3, ...}
    created_at DATETIME NOT NULL,
    completed_at DATETIME,
    processing_status VARCHAR(20) NOT NULL,  -- processing/completed/failed
    error_message TEXT,
    failed_count INTEGER DEFAULT 0
);
```

**BatchItem Table:**
```sql
CREATE TABLE batch_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER REFERENCES batch_analyses(id) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    stored_path VARCHAR(512) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- EMPTY/HALF/FULL/NO_BIN_DETECTED
    confidence FLOAT NOT NULL,
    bins_detected INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    completed_at DATETIME,
    processing_status VARCHAR(20) NOT NULL,  -- pending/processing/completed/failed
    error_message TEXT
);
```

**Artifact Table (Updated):**
```sql
CREATE TABLE artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
    batch_item_id INTEGER REFERENCES batch_items(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL,  -- overlay/cropped_bin/debug_json
    path VARCHAR(512) NOT NULL,
    bin_index INTEGER,
    file_size INTEGER,
    mime_type VARCHAR(50)
);
```

### Frontend Pages

**Upload Page (`/upload`):**
- Mode toggle: Single File / Batch Upload
- Multiple file input with previews
- Thumbnail grid display
- Batch analysis progress
- Summary results with link to details

**Batches List (`/batches`):**
- Paginated batch list
- Status filtering
- Summary cards
- Quick navigation to details

**Batch Details (`/batches/[id]`):**
- Batch metadata and summary
- Status distribution breakdown
- Paginated items table
- Links to individual items

**Batch Item Details (`/batch-items/[id]`):**
- Original and overlay images
- Cropped bin thumbnails
- Artifact download links
- Confidence and metadata

---

## 🔍 Troubleshooting

### Issue: "Invalid file types detected"

**Cause:** Non-image files included in batch

**Solution:**
- Only select image files (.jpg, .jpeg, .png, .webp)
- Videos are NOT supported in batch upload
- Use single file upload for videos

### Issue: Batch processing stuck

**Cause:** Backend may have crashed or timed out

**Solution:**
```bash
# Check backend logs
# Restart backend
cd smart-waste-ai
python backend/main.py

# Check database for batch status
sqlite3 data/smart_waste.db "SELECT * FROM batch_analyses ORDER BY id DESC LIMIT 1;"
```

### Issue: Some items failed in batch

**Cause:** Individual images may have errors (corrupt, unreadable, etc.)

**Solution:**
- Check `failed_count` in batch details
- Review individual item error messages
- Re-upload failed images separately
- Verify image file integrity

### Issue: Can't see batch in list

**Cause:** Database not updated or batch creation failed

**Solution:**
- Refresh the page
- Check backend logs for errors
- Verify API response included `internal_batch_id`
- Check database: `SELECT * FROM batch_analyses;`

---

## ⚡ Performance Considerations

### Upload Size Recommendations

- **Small batches** (<10 images): Instant processing
- **Medium batches** (10-50 images): 1-5 minutes
- **Large batches** (50-100 images): 5-15 minutes
- **Very large batches** (100+ images): Consider splitting

### Optimization Tips

1. **Resize images** before upload for faster processing
2. **Upload in batches** of 50-100 for manageable processing
3. **Use consistent naming** for easier result tracking
4. **Monitor backend logs** for processing progress
5. **Check disk space** before large uploads

### Resource Usage

- **Memory:** ~200MB base + ~50MB per concurrent image
- **Disk:** ~2-5MB per image (original + artifacts)
- **CPU:** One image processed at a time (sequential)

---

## 🚀 Best Practices

### 1. File Organization

```
monitoring/
├── 2025-01-01/
│   ├── route_1/
│   │   ├── bin_001.jpg
│   │   ├── bin_002.jpg
│   │   └── ...
│   └── route_2/
│       ├── bin_101.jpg
│       └── ...
└── 2025-01-02/
    └── ...
```

### 2. Naming Conventions

- Use descriptive filenames: `location_bin_timestamp.jpg`
- Include metadata in filename: `route1_bin5_20250101_0800.jpg`
- Avoid special characters and spaces

### 3. Quality Guidelines

- **Resolution:** 640x480 minimum, 1920x1080 recommended
- **Lighting:** Good lighting conditions for best results
- **Angle:** Front-facing view of bins
- **Focus:** Clear, non-blurry images

### 4. Batch Size Strategy

- **Real-time monitoring:** Small batches (5-10 images)
- **Daily processing:** Medium batches (20-50 images)
- **Historical analysis:** Large batches (50-100 images)

---

## 📊 Database Queries

### Get all batches from today
```sql
SELECT * FROM batch_analyses
WHERE DATE(created_at) = DATE('now')
ORDER BY created_at DESC;
```

### Get batch with highest full bin count
```sql
SELECT batch_id, status_counts
FROM batch_analyses
WHERE processing_status = 'completed'
ORDER BY json_extract(status_counts, '$.FULL') DESC
LIMIT 1;
```

### Get failed items in a batch
```sql
SELECT * FROM batch_items
WHERE batch_id = 1 AND processing_status = 'failed';
```

### Get batch statistics
```sql
SELECT
    COUNT(*) as total_batches,
    SUM(total_files) as total_images,
    AVG(total_files) as avg_batch_size
FROM batch_analyses
WHERE processing_status = 'completed';
```

---

## ✅ Summary

**What you can do now:**

1. ✅ Upload multiple images simultaneously
2. ✅ Process hundreds of images in one batch
3. ✅ View aggregated status counts
4. ✅ Browse individual item results
5. ✅ Download artifacts and overlays
6. ✅ Filter and search batches
7. ✅ Track processing status
8. ✅ Export results via API

**Key Benefits:**

- 🚀 **Efficient**: Process many images at once
- 📊 **Organized**: All results grouped by batch
- 🔍 **Detailed**: Individual item analysis available
- 📱 **User-friendly**: Web UI for easy management
- 🔌 **Automated**: API for programmatic workflows
- 💾 **Persistent**: All results saved to database

**Ready to use!** Start batch uploading and analyzing your trash bin images now! 🎉

---

**Feature added to branch:** `claude/smart-city-waste-monitoring-8Tyk0`

**Documentation updated:** December 2025
