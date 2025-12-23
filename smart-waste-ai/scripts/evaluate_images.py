"""
Evaluation Script for Image Classification
===========================================
Evaluates the accuracy of the trash bin fill level classifier.

Usage:
    python scripts/evaluate_images.py --input data/evaluation_set

Expected directory structure:
    input_folder/
    ├── empty/         # Images of empty bins
    ├── half/          # Images of half-full bins
    ├── full/          # Images of full bins
    └── no_bin/        # Images with no bins

Output:
    - data/results/eval_report.json      # Evaluation metrics
    - data/results/mistakes/             # Misclassified examples
"""

import argparse
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
import cv2
import numpy as np

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.detection.yolo_detector import YOLOv8Detector
from ai.classification.fill_level_classifier import get_classifier
from ai.classification.classifier_interface import FillLevel
from ai.config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Mapping from folder names to expected status
LABEL_MAP = {
    "empty": "EMPTY",
    "half": "HALF",
    "full": "FULL",
    "no_bin": "NO_BIN_DETECTED"
}


class BinEvaluator:
    """
    Evaluates trash bin classifier on a labeled dataset.
    """

    def __init__(self, classifier_mode: str = None):
        """
        Initialize evaluator.

        Args:
            classifier_mode: Classifier to use (brightness/edge_density/hybrid)
        """
        logger.info("Initializing evaluator...")

        # Initialize detector and classifier
        self.detector = YOLOv8Detector()
        self.detector.load_model()

        self.classifier = get_classifier(classifier_mode)

        # Results storage
        self.results = []
        self.confusion_matrix = defaultdict(lambda: defaultdict(int))

    def evaluate_image(
        self,
        image_path: Path,
        ground_truth: str
    ) -> Dict:
        """
        Evaluate a single image.

        Args:
            image_path: Path to image file
            ground_truth: Expected status (EMPTY/HALF/FULL/NO_BIN_DETECTED)

        Returns:
            Dictionary with evaluation results
        """
        # Read image
        image = cv2.imread(str(image_path))
        if image is None:
            logger.warning(f"Failed to read image: {image_path}")
            return None

        # Run detection
        detections = self.detector.detect(image)

        # If no bins detected
        if not detections:
            predicted = "NO_BIN_DETECTED"
            confidence = 0.0
        else:
            # Classify each detected bin
            classifications = []
            for detection in detections:
                cropped = detection.crop_from_image(image)
                classification = self.classifier.classify(cropped)
                classifications.append(classification)

            # Get fullest bin (conservative approach)
            level_order = {FillLevel.EMPTY: 0, FillLevel.HALF: 1, FillLevel.FULL: 2}
            fullest = max(classifications, key=lambda c: level_order[c.fill_level])

            predicted = fullest.fill_level.value
            confidence = fullest.confidence

        # Determine if prediction is correct
        correct = (predicted == ground_truth)

        result = {
            "image_path": str(image_path),
            "image_name": image_path.name,
            "ground_truth": ground_truth,
            "predicted": predicted,
            "confidence": confidence,
            "correct": correct,
            "bins_detected": len(detections)
        }

        # Update confusion matrix
        self.confusion_matrix[ground_truth][predicted] += 1

        return result

    def evaluate_dataset(self, dataset_path: Path) -> Dict:
        """
        Evaluate entire dataset.

        Args:
            dataset_path: Path to dataset folder with subfolders

        Returns:
            Dictionary with evaluation metrics
        """
        logger.info(f"Evaluating dataset: {dataset_path}")

        # Ensure dataset path exists
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")

        # Process each class folder
        for folder_name, ground_truth in LABEL_MAP.items():
            folder_path = dataset_path / folder_name
            if not folder_path.exists():
                logger.warning(f"Folder not found: {folder_path}, skipping...")
                continue

            # Get all image files
            image_extensions = ['.jpg', '.jpeg', '.png']
            images = []
            for ext in image_extensions:
                images.extend(folder_path.glob(f"*{ext}"))
                images.extend(folder_path.glob(f"*{ext.upper()}"))

            logger.info(f"Processing {len(images)} images from {folder_name}/")

            # Evaluate each image
            for image_path in images:
                result = self.evaluate_image(image_path, ground_truth)
                if result:
                    self.results.append(result)

        # Compute metrics
        metrics = self._compute_metrics()

        return metrics

    def _compute_metrics(self) -> Dict:
        """
        Compute evaluation metrics.

        Returns:
            Dictionary with accuracy, per-class metrics, and confusion matrix
        """
        if not self.results:
            return {"error": "No results to compute metrics"}

        total = len(self.results)
        correct = sum(1 for r in self.results if r["correct"])

        # Overall accuracy
        accuracy = correct / total if total > 0 else 0

        # Per-class metrics
        per_class = {}
        for label in LABEL_MAP.values():
            true_positives = self.confusion_matrix[label][label]
            false_positives = sum(
                self.confusion_matrix[other][label]
                for other in LABEL_MAP.values()
                if other != label
            )
            false_negatives = sum(
                self.confusion_matrix[label][other]
                for other in LABEL_MAP.values()
                if other != label
            )

            precision = (
                true_positives / (true_positives + false_positives)
                if (true_positives + false_positives) > 0
                else 0
            )

            recall = (
                true_positives / (true_positives + false_negatives)
                if (true_positives + false_negatives) > 0
                else 0
            )

            f1 = (
                2 * (precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0
            )

            per_class[label] = {
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
                "support": sum(self.confusion_matrix[label].values())
            }

        # Convert confusion matrix to regular dict for JSON serialization
        confusion_matrix_dict = {
            gt: dict(pred)
            for gt, pred in self.confusion_matrix.items()
        }

        metrics = {
            "total_images": total,
            "correct_predictions": correct,
            "accuracy": round(accuracy, 4),
            "per_class_metrics": per_class,
            "confusion_matrix": confusion_matrix_dict
        }

        return metrics

    def save_report(self, output_path: Path, metrics: Dict):
        """
        Save evaluation report to JSON file.

        Args:
            output_path: Path to save report
            metrics: Evaluation metrics dictionary
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "timestamp": str(Path().absolute()),
            "dataset_info": {
                "total_images": len(self.results),
                "classifier": self.classifier.get_model_info(),
                "detector": self.detector.get_model_info()
            },
            "metrics": metrics,
            "config": {
                "classifier_mode": config.MOCK_CLASSIFIER_MODE,
                "brightness_empty_threshold": config.BRIGHTNESS_EMPTY_THRESHOLD,
                "brightness_half_threshold": config.BRIGHTNESS_HALF_THRESHOLD,
                "edge_empty_threshold": config.EDGE_EMPTY_THRESHOLD,
                "edge_half_threshold": config.EDGE_HALF_THRESHOLD
            }
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved to: {output_path}")

    def save_mistakes(self, mistakes_dir: Path, max_per_class: int = 5):
        """
        Save examples of misclassified images.

        Args:
            mistakes_dir: Directory to save mistakes
            max_per_class: Maximum mistakes to save per class
        """
        mistakes_dir.mkdir(parents=True, exist_ok=True)

        # Get incorrect predictions
        mistakes = [r for r in self.results if not r["correct"]]

        if not mistakes:
            logger.info("No mistakes found!")
            return

        logger.info(f"Saving {len(mistakes)} mistake examples...")

        # Group by ground truth class
        mistakes_by_class = defaultdict(list)
        for mistake in mistakes:
            mistakes_by_class[mistake["ground_truth"]].append(mistake)

        # Save examples for each class
        for ground_truth, class_mistakes in mistakes_by_class.items():
            # Limit number of examples per class
            examples = class_mistakes[:max_per_class]

            for i, mistake in enumerate(examples):
                # Create descriptive filename
                filename = (
                    f"{ground_truth.lower()}_"
                    f"predicted_{mistake['predicted'].lower()}_"
                    f"{i+1}.jpg"
                )

                # Copy original image
                src_path = Path(mistake["image_path"])
                dst_path = mistakes_dir / filename

                if src_path.exists():
                    # Copy image with overlay showing detection
                    image = cv2.imread(str(src_path))

                    # Add text overlay with prediction info
                    text = f"GT: {ground_truth} | Pred: {mistake['predicted']} | Conf: {mistake['confidence']:.2f}"
                    cv2.putText(
                        image,
                        text,
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2
                    )

                    cv2.imwrite(str(dst_path), image)

        logger.info(f"Mistake examples saved to: {mistakes_dir}")


def main():
    """Main entry point for evaluation script."""
    parser = argparse.ArgumentParser(
        description="Evaluate trash bin classifier on labeled dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python scripts/evaluate_images.py --input data/evaluation_set

Dataset structure:
  data/evaluation_set/
  ├── empty/         # Images of empty bins
  ├── half/          # Images of half-full bins
  ├── full/          # Images of full bins
  └── no_bin/        # Images with no bins
        """
    )

    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Path to evaluation dataset folder'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='data/results/eval_report.json',
        help='Path to save evaluation report (default: data/results/eval_report.json)'
    )

    parser.add_argument(
        '--mistakes',
        type=str,
        default='data/results/mistakes',
        help='Directory to save mistake examples (default: data/results/mistakes/)'
    )

    parser.add_argument(
        '--classifier',
        type=str,
        choices=['brightness', 'edge_density', 'hybrid'],
        default=None,
        help='Classifier to use (default: from config)'
    )

    parser.add_argument(
        '--max-mistakes',
        type=int,
        default=5,
        help='Maximum mistake examples per class (default: 5)'
    )

    args = parser.parse_args()

    # Initialize evaluator
    evaluator = BinEvaluator(classifier_mode=args.classifier)

    # Run evaluation
    dataset_path = Path(args.input)
    metrics = evaluator.evaluate_dataset(dataset_path)

    # Save report
    output_path = Path(args.output)
    evaluator.save_report(output_path, metrics)

    # Save mistake examples
    mistakes_dir = Path(args.mistakes)
    evaluator.save_mistakes(mistakes_dir, max_per_class=args.max_mistakes)

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total images: {metrics['total_images']}")
    print(f"Correct: {metrics['correct_predictions']}")
    print(f"Accuracy: {metrics['accuracy']:.2%}")
    print("\nPer-class metrics:")
    for label, class_metrics in metrics['per_class_metrics'].items():
        print(f"\n  {label}:")
        print(f"    Precision: {class_metrics['precision']:.2%}")
        print(f"    Recall:    {class_metrics['recall']:.2%}")
        print(f"    F1-score:  {class_metrics['f1_score']:.4f}")
        print(f"    Support:   {class_metrics['support']}")

    print("\nConfusion Matrix:")
    print("                 Predicted →")
    print("     ", end="")
    labels = list(LABEL_MAP.values())
    for label in labels:
        print(f"{label[:12]:>12}", end=" ")
    print()

    for gt_label in labels:
        print(f"{gt_label[:5]:>5}", end=" ")
        for pred_label in labels:
            count = metrics['confusion_matrix'].get(gt_label, {}).get(pred_label, 0)
            print(f"{count:>12}", end=" ")
        print()

    print("\n" + "=" * 60)
    print(f"\nReport saved to: {output_path}")
    print(f"Mistakes saved to: {mistakes_dir}")
    print("\n✓ Evaluation complete!")


if __name__ == "__main__":
    main()


# TODO: Add support for custom confidence thresholds
# TODO: Add ROC curve analysis
# TODO: Add visualization of mistake patterns
# TODO: Add support for video evaluation
# TODO: Add per-image debug output
