"""
Create Ultralytics Dataset YAML
===============================
Creates dataset.yaml for a single-class trash_container dataset.

Usage:
  python scripts/create_dataset_yaml.py --dataset dataset --name trash_container
"""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create dataset.yaml for Ultralytics training.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="dataset",
        help="Dataset root containing images/ and labels/ (default: dataset)"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="trash_container",
        help="Class name (default: trash_container)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for dataset.yaml (default: <dataset>/dataset.yaml)"
    )

    args = parser.parse_args()

    dataset_root = Path(args.dataset)
    output_path = Path(args.output) if args.output else dataset_root / "dataset.yaml"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(f"path: {dataset_root}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write("names:\n")
        f.write(f"  - {args.name}\n")

    print(f"✓ Wrote {output_path}")


if __name__ == "__main__":
    main()
