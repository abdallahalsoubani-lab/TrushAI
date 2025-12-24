# Training Guide (Custom Trash Container Model)

This project ships with COCO `yolov8n.pt` by default. For real trash bin detection, train a custom single-class model named `trash_container`.

## 1) Prepare dataset structure

```
dataset/
├── images/
│   ├── train/
│   └── val/
├── labels/
│   ├── train/
│   └── val/
└── dataset.yaml
```

Label format: YOLO TXT with normalized `class_id x_center y_center width height`.

## 2) Extract frames from videos

```
python scripts/prepare_dataset_frames.py --videos data/videos --output dataset/images
```

Move or split images into `dataset/images/train` and `dataset/images/val`, then label them.

## 3) Create dataset.yaml

```
python scripts/create_dataset_yaml.py --dataset dataset --name trash_container
```

This creates `dataset/dataset.yaml` with a single class.

## 4) Train with Ultralytics

Recommended command:

```
yolo detect train \
  data=dataset/dataset.yaml \
  model=yolov8n.pt \
  epochs=100 \
  imgsz=640 \
  batch=16 \
  device=cpu
```

Augmentation tips:
- Use `degrees=5` and `shear=2` if bins are rotated in camera views.
- Use `hsv_h=0.015 hsv_s=0.7 hsv_v=0.4` for variable lighting.
- Use `translate=0.1 scale=0.5` to improve size/position robustness.
- If your dataset is small, try `mosaic=0.8 mixup=0.1`.

## 5) Use the trained weights

After training, copy the best weights to the project root as `bins.pt`:

```
cp runs/detect/train/weights/best.pt bins.pt
```

The system will auto-load `bins.pt` and switch to:
- `DETECT_ALL_OBJECTS=False`
- `TRASH_BIN_CLASSES=["trash_container"]`

Or set a custom path explicitly:

```
export YOLO_WEIGHTS_PATH=/absolute/path/to/best.pt
```

## 6) Quick sanity check (single image)

```
python scripts/analyze_image.py --image path/to/image.jpg --output data/results/debug/annotated.jpg
```

Use `--raw` to see all detections (no filtering).

---

## Training From the Dashboard (UI)

1) Open `http://localhost:3000/train`
2) Upload images → annotate each with one bounding box
3) Click **Auto split train/val**
4) Configure training and click **Start Training**
5) Monitor logs + progress, then **Download best.pt** or **Use This Model**

---

## Apple Silicon (MPS)

If you are on macOS with Apple Silicon:

```
pip install ultralytics torch torchvision
```

Then choose `device=mps` or leave `device=auto` in the UI.
