# Debugging and Evaluation Guide

Complete guide for debugging classifier behavior and evaluating accuracy.

---

## 🎯 Three New Features

1. **NO_BIN_DETECTED Status** - Clear distinction between "no bins found" and "empty bins"
2. **DEBUG MODE** - Save visualization artifacts and metadata for analysis
3. **Evaluation Script** - Measure accuracy on labeled datasets

---

## 1️⃣ NO_BIN_DETECTED Status

### What Changed

Previously, when no bins were detected, the system returned `status="EMPTY"` with `confidence=0`. This was confusing because it conflated "no bin found" with "found an empty bin".

Now: `status="NO_BIN_DETECTED"` when `bins_detected==0`.

### Status Values

| Status | Meaning | Color | Use Case |
|--------|---------|-------|----------|
| `EMPTY` | Bin detected and is empty | 🟢 Green | Normal operation |
| `HALF` | Bin detected and half full | 🟠 Orange | Normal operation |
| `FULL` | Bin detected and full | 🔴 Red | Schedule pickup |
| `NO_BIN_DETECTED` | No bin found in image/video | ⚫ Gray | Check camera angle |

### API Response Example

```json
{
  "input_type": "image",
  "status": "NO_BIN_DETECTED",
  "confidence": 0.0,
  "bins_detected": 0,
  "message": "No bins detected in image"
}
```

### Dashboard UI

The upload page now shows:
- **"NO BIN DETECTED"** (with spaces, not underscores)
- Gray badge (⚫) instead of green
- Helps users distinguish detection failures from actual results

---

## 2️⃣ DEBUG MODE

### Overview

DEBUG MODE saves detailed artifacts for every analysis, helping you understand:
- Why did the classifier choose this status?
- What were the raw scores?
- Which parts of the image were analyzed?
- Are the detections accurate?

### Enable Debug Mode

```bash
# Option 1: Environment variable
export DEBUG_MODE=true
python backend/main.py

# Option 2: Add to .env file
echo "DEBUG_MODE=true" >> .env
python backend/main.py

# Option 3: Temporarily for one session
DEBUG_MODE=true python backend/main.py
```

### What Gets Saved

When DEBUG_MODE is enabled, every call to `/analyze-upload` saves:

#### 1. Overlay Image
**Location**: `data/results/debug/overlay_{analysis_id}.jpg`

Shows:
- Original image
- Bounding boxes around detected bins
- Color-coded by fill level:
  - 🟢 Green = EMPTY
  - 🟠 Orange = HALF
  - 🔴 Red = FULL
- Text labels with fill level and confidence

**Example**: `overlay_20251223_143000_a1b2c3.jpg`

#### 2. Cropped Bin Images
**Location**: `data/results/debug/bin_{index}_{analysis_id}.jpg`

Shows:
- Exact cropped image sent to classifier
- One file per detected bin
- Helps verify detection quality

**Example**:
- `bin_0_20251223_143000_a1b2c3.jpg` (first bin)
- `bin_1_20251223_143000_a1b2c3.jpg` (second bin)

#### 3. Metadata JSON
**Location**: `data/results/debug/metadata_{analysis_id}.json`

Contains:
- Analysis timestamp and ID
- Overall status and confidence
- Per-bin details:
  - Bounding box coordinates
  - Detection confidence (from YOLO)
  - Fill level prediction
  - Classification confidence
  - **Raw classifier scores**:
    - `avg_brightness` (brightness classifier)
    - `edge_density` (edge density classifier)
    - Thresholds used
    - Method name

**Example**: `metadata_20251223_143000_a1b2c3.json`

### Example Metadata JSON

```json
{
  "analysis_id": "20251223_143000_a1b2c3",
  "timestamp": "2025-12-23T14:30:00.123456",
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
    },
    {
      "bin_index": 1,
      "bbox": [350, 200, 550, 600],
      "detection_confidence": 0.92,
      "fill_level": "EMPTY",
      "classification_confidence": 0.7,
      "classifier_metadata": {
        "method": "brightness",
        "avg_brightness": 175.3,
        "threshold_empty": 150,
        "threshold_half": 100
      }
    }
  ]
}
```

### API Response with Debug Artifacts

```json
{
  "input_type": "image",
  "status": "HALF",
  "confidence": 0.72,
  "bins_detected": 2,
  "message": "Image analysis complete",
  "debug_artifacts": {
    "overlay_image": "data/results/debug/overlay_20251223_143000_a1b2c3.jpg",
    "cropped_bins": [
      "data/results/debug/bin_0_20251223_143000_a1b2c3.jpg",
      "data/results/debug/bin_1_20251223_143000_a1b2c3.jpg"
    ],
    "metadata": "data/results/debug/metadata_20251223_143000_a1b2c3.json"
  }
}
```

### Use Cases for Debug Mode

#### 1. Understanding Misclassifications

```bash
# Enable debug mode
export DEBUG_MODE=true
python backend/main.py

# Upload image that was misclassified
curl -X POST "http://localhost:8000/api/v1/analyze-upload" -F "file=@problem_image.jpg"

# Check the artifacts
ls data/results/debug/
# overlay_20251223_143000_a1b2c3.jpg       <- Visual check
# bin_0_20251223_143000_a1b2c3.jpg        <- Cropped bin
# metadata_20251223_143000_a1b2c3.json     <- Raw scores
```

**Inspect metadata**:
```bash
cat data/results/debug/metadata_20251223_143000_a1b2c3.json | jq '.bins[0].classifier_metadata'
```

**Output**:
```json
{
  "method": "brightness",
  "avg_brightness": 140.5,
  "threshold_empty": 150,
  "threshold_half": 100
}
```

**Analysis**: Brightness is 140.5, which is between 100-150, so it's classified as HALF. But visually it looks EMPTY? Maybe threshold needs adjustment!

#### 2. Tuning Thresholds

Use debug artifacts to determine better thresholds:

```python
import json
import glob

# Collect metadata from many debug runs
metadata_files = glob.glob("data/results/debug/metadata_*.json")

brightness_values = {"EMPTY": [], "HALF": [], "FULL": []}

for file in metadata_files:
    with open(file) as f:
        data = json.load(f)
        for bin_data in data["bins"]:
            status = bin_data["fill_level"]
            brightness = bin_data["classifier_metadata"].get("avg_brightness")
            if brightness:
                brightness_values[status].append(brightness)

# Find optimal thresholds
import numpy as np
print("EMPTY brightness range:", np.min(brightness_values["EMPTY"]), "-", np.max(brightness_values["EMPTY"]))
print("HALF brightness range:", np.min(brightness_values["HALF"]), "-", np.max(brightness_values["HALF"]))
print("FULL brightness range:", np.min(brightness_values["FULL"]), "-", np.max(brightness_values["FULL"]))
```

#### 3. Verifying Detections

Check if YOLO is detecting bins correctly:

```bash
# View overlay image
open data/results/debug/overlay_20251223_143000_a1b2c3.jpg

# Questions to ask:
# - Are bounding boxes accurate?
# - Are any bins missed?
# - Are false positives detected?
# - Do bounding boxes include the whole bin?
```

---

## 3️⃣ Evaluation Script

### Overview

The evaluation script measures classifier accuracy on a labeled dataset.

**Benefits**:
- Quantitative accuracy metrics
- Confusion matrix to see error patterns
- Per-class precision/recall/F1
- Examples of mistakes for manual review

### Prepare Evaluation Dataset

Create a folder with labeled images:

```
data/evaluation_set/
├── empty/          # 25+ images of empty bins
├── half/           # 25+ images of half-full bins
├── full/           # 25+ images of full bins
└── no_bin/         # 25+ images with no bins
```

**Tips**:
- At least 25 images per class (100+ total recommended)
- Diverse lighting conditions
- Different bin types/angles
- Real-world images, not synthetic

### Run Evaluation

```bash
python scripts/evaluate_images.py \
  --input data/evaluation_set \
  --output data/results/eval_report.json \
  --mistakes data/results/mistakes \
  --classifier brightness \
  --max-mistakes 5
```

**Arguments**:
- `--input`: Path to evaluation dataset folder
- `--output`: Where to save JSON report (default: `data/results/eval_report.json`)
- `--mistakes`: Directory for mistake examples (default: `data/results/mistakes/`)
- `--classifier`: Which classifier to test (`brightness`/`edge_density`/`hybrid`)
- `--max-mistakes`: Max examples per class to save (default: 5)

### Output

#### 1. Terminal Summary

```
============================================================
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

Confusion Matrix:
                 Predicted →
     EMPTY        HALF        FULL        NO_BIN_DETECTED
EMPTY      21           3           1           0
HALF        5          16           4           0
FULL        1           4          20           0
NO_BIN      0           0           0          25

============================================================
Report saved to: data/results/eval_report.json
Mistakes saved to: data/results/mistakes/
```

#### 2. JSON Report

**File**: `data/results/eval_report.json`

```json
{
  "timestamp": "/path/to/project",
  "dataset_info": {
    "total_images": 100,
    "classifier": {
      "type": "mock",
      "name": "BrightnessClassifier",
      "classes": ["EMPTY", "HALF", "FULL"]
    },
    "detector": {
      "name": "YOLOv8n",
      "version": "8",
      "device": "cpu"
    }
  },
  "metrics": {
    "total_images": 100,
    "correct_predictions": 75,
    "accuracy": 0.75,
    "per_class_metrics": {
      "EMPTY": {
        "precision": 0.8,
        "recall": 0.85,
        "f1_score": 0.8235,
        "support": 25
      },
      ...
    },
    "confusion_matrix": {
      "EMPTY": {"EMPTY": 21, "HALF": 3, "FULL": 1, "NO_BIN_DETECTED": 0},
      "HALF": {"EMPTY": 5, "HALF": 16, "FULL": 4, "NO_BIN_DETECTED": 0},
      "FULL": {"EMPTY": 1, "HALF": 4, "FULL": 20, "NO_BIN_DETECTED": 0},
      "NO_BIN_DETECTED": {"EMPTY": 0, "HALF": 0, "FULL": 0, "NO_BIN_DETECTED": 25}
    }
  },
  "config": {
    "classifier_mode": "brightness",
    "brightness_empty_threshold": 150,
    "brightness_half_threshold": 100,
    "edge_empty_threshold": 0.05,
    "edge_half_threshold": 0.15
  }
}
```

#### 3. Mistake Examples

**Directory**: `data/results/mistakes/`

Files named: `{ground_truth}_predicted_{prediction}_{n}.jpg`

Examples:
- `empty_predicted_half_1.jpg` - Empty bin misclassified as HALF
- `half_predicted_full_2.jpg` - Half bin misclassified as FULL
- `full_predicted_empty_1.jpg` - Full bin misclassified as EMPTY

Each image has overlay text showing:
- `GT: EMPTY | Pred: HALF | Conf: 0.65`

### Interpreting Results

#### Accuracy
- **75%+**: Good for MVP mock classifier
- **60-75%**: Needs threshold tuning
- **<60%**: Consider different features or train CNN

#### Precision vs Recall
- **High Precision, Low Recall**: Classifier is conservative (many false negatives)
- **Low Precision, High Recall**: Classifier is aggressive (many false positives)
- **Both Low**: Classifier is confused, needs improvement

#### Confusion Matrix Patterns

**Example 1**: EMPTY often predicted as HALF
```
      Pred: EMPTY  HALF  FULL
GT:
EMPTY      15      10     0
```
→ **Solution**: Increase `BRIGHTNESS_EMPTY_THRESHOLD` (currently 150 → try 160)

**Example 2**: HALF confused with both EMPTY and FULL
```
      Pred: EMPTY  HALF  FULL
GT:
HALF       8       10     7
```
→ **Solution**: HALF threshold range too wide, adjust `BRIGHTNESS_HALF_THRESHOLD`

**Example 3**: NO_BIN_DETECTED working perfectly
```
      Pred: EMPTY  HALF  FULL  NO_BIN
GT:
NO_BIN     0       0     0     25
```
→ **Good**: YOLO detection is reliable

---

## 🔄 Recommended Workflow

### Step 1: Collect Sample Images

```bash
# Create evaluation folders
mkdir -p data/evaluation_set/{empty,half,full,no_bin}

# Manually sort images into folders
# or use existing labeled dataset
```

### Step 2: Run Initial Evaluation

```bash
# Test current classifier
python scripts/evaluate_images.py \
  --input data/evaluation_set \
  --classifier brightness

# Check accuracy
cat data/results/eval_report.json | jq '.metrics.accuracy'
```

### Step 3: Enable Debug Mode for Mistakes

```bash
# Enable debug mode
export DEBUG_MODE=true
python backend/main.py

# In another terminal, upload some mistake images
for img in data/results/mistakes/*.jpg; do
  curl -X POST "http://localhost:8000/api/v1/analyze-upload" -F "file=@$img"
done

# Analyze debug artifacts
ls data/results/debug/
```

### Step 4: Analyze Patterns

```bash
# Check metadata for mistakes
cat data/results/debug/metadata_*.json | jq '.bins[].classifier_metadata'

# Look for patterns:
# - Are empty bins darker than expected?
# - Are full bins brighter than expected?
# - Is there overlap in brightness ranges?
```

### Step 5: Adjust Thresholds

Edit `ai/config.py`:

```python
# Old thresholds
BRIGHTNESS_EMPTY_THRESHOLD: int = 150
BRIGHTNESS_HALF_THRESHOLD: int = 100

# New thresholds (based on debug analysis)
BRIGHTNESS_EMPTY_THRESHOLD: int = 160  # Increased
BRIGHTNESS_HALF_THRESHOLD: int = 110   # Increased
```

### Step 6: Re-evaluate

```bash
# Restart backend with new thresholds
python backend/main.py

# Run evaluation again
python scripts/evaluate_images.py \
  --input data/evaluation_set \
  --classifier brightness

# Compare results
echo "Old accuracy: 75%"
echo "New accuracy: $(cat data/results/eval_report.json | jq '.metrics.accuracy')"
```

### Step 7: Iterate

Repeat steps 3-6 until accuracy is satisfactory (75%+ for MVP).

---

## 🎯 Quick Reference

### Enable DEBUG MODE
```bash
export DEBUG_MODE=true
python backend/main.py
```

### Test Single Image with Debug
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-upload" \
  -F "file=@test_image.jpg"

# Check artifacts
ls data/results/debug/
```

### Run Evaluation
```bash
python scripts/evaluate_images.py \
  --input data/evaluation_set \
  --classifier brightness
```

### View Mistakes
```bash
open data/results/mistakes/
```

### Check Accuracy
```bash
cat data/results/eval_report.json | jq '.metrics.accuracy'
```

---

## 📊 Expected Baseline Performance

Current mock classifier performance (typical):

| Metric | Expected Range |
|--------|---------------|
| **Overall Accuracy** | 70-80% |
| **EMPTY Precision** | 75-85% |
| **EMPTY Recall** | 80-90% |
| **HALF Precision** | 65-75% (hardest class) |
| **HALF Recall** | 60-70% |
| **FULL Precision** | 70-80% |
| **FULL Recall** | 75-85% |
| **NO_BIN Precision** | 95-100% |
| **NO_BIN Recall** | 95-100% |

**Note**: These are heuristic-based classifiers. For production, train a CNN to achieve 90%+ accuracy.

---

## 🚀 Next Steps

After debugging and evaluation:

1. **Collect More Data**: 1000+ images per class
2. **Label Carefully**: Ensure ground truth is accurate
3. **Train CNN**: Replace mock classifier with trained model
4. **Fine-tune YOLO**: Custom trash bin dataset
5. **Deploy**: Use evaluation metrics to validate production readiness

---

**All features are committed and pushed to**: `claude/smart-city-waste-monitoring-8Tyk0`
