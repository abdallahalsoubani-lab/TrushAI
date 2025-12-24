"""
Analyze Single Image
====================
Run detection on a single image and save an annotated output image.

Usage:
  python scripts/analyze_image.py --image path/to/image.jpg --output data/results/debug/annotated.jpg
"""

import argparse
from pathlib import Path
import sys
import cv2

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.detection.yolo_detector import YOLOv8Detector
from ai.config import config


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a single image with YOLO.")
    parser.add_argument("--image", type=str, required=True, help="Path to input image")
    parser.add_argument(
        "--output",
        type=str,
        default=str(config.DEBUG_OUTPUT_DIR / "annotated.jpg"),
        help="Path to save annotated image"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Use raw detections (no bin filtering)"
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Failed to read image: {image_path}")

    detector = YOLOv8Detector()
    detector.load_model()

    if args.raw and hasattr(detector, "detect_raw"):
        detections = detector.detect_raw(image, log_detections=True)
    else:
        detections = detector.detect(image, log_detections=True)

    annotated = detector.visualize_detections(image, detections)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), annotated)

    print(f"✓ Detections: {len(detections)}")
    print(f"✓ Annotated image saved to: {output_path}")


if __name__ == "__main__":
    main()
