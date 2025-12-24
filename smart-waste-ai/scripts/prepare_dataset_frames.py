"""
Prepare Dataset Frames
======================
Extract frames from one or more videos into a dataset/images folder.

Usage:
  python scripts/prepare_dataset_frames.py --videos data/videos --output dataset/images
  python scripts/prepare_dataset_frames.py --video data/videos/sample.mp4 --output dataset/images --rate 1 --max 200
"""

import argparse
from pathlib import Path
import logging
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.extract_frames import extract_frames
from ai.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def collect_videos(video_path: Path) -> list[Path]:
    if video_path.is_file():
        return [video_path]

    if not video_path.exists():
        raise FileNotFoundError(f"Video path not found: {video_path}")

    extensions = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"}
    return sorted([p for p in video_path.rglob("*") if p.suffix.lower() in extensions])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract frames from videos into a dataset/images folder."
    )
    parser.add_argument(
        "--video",
        type=str,
        help="Single video file to process"
    )
    parser.add_argument(
        "--videos",
        type=str,
        help="Directory with multiple videos to process"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="dataset/images",
        help="Output directory for extracted frames (default: dataset/images)"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=config.FRAME_EXTRACTION_RATE,
        help=f"Extract 1 frame every N seconds (default: {config.FRAME_EXTRACTION_RATE})"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum number of frames to extract per video (default: no limit)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["jpg", "png"],
        default="jpg",
        help="Output image format (default: jpg)"
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        help="JPEG quality 0-100 (default: 95)"
    )

    args = parser.parse_args()

    if not args.video and not args.videos:
        parser.error("Provide --video or --videos")

    video_target = Path(args.video) if args.video else Path(args.videos)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    videos = collect_videos(video_target)
    if not videos:
        raise FileNotFoundError(f"No videos found in: {video_target}")

    total_frames = 0
    for video in videos:
        logger.info("Processing %s", video)
        extracted = extract_frames(
            video_path=str(video),
            output_dir=str(output_dir),
            frame_rate=args.rate,
            max_frames=args.max,
            format=args.format,
            quality=args.quality
        )
        total_frames += extracted

    logger.info("✓ Dataset frame extraction complete: %s frames", total_frames)


if __name__ == "__main__":
    main()
