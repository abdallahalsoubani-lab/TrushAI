"""
Frame Extraction Script
=======================
Utility script to extract frames from video files.

This script can be used to:
- Preview videos before processing
- Create test datasets
- Debug frame extraction logic
- Generate training data for custom models

Usage:
    python scripts/extract_frames.py --video path/to/video.mp4
    python scripts/extract_frames.py --video path/to/video.mp4 --rate 1 --max 100
    python scripts/extract_frames.py --video path/to/video.mp4 --output frames/
"""

import argparse
import cv2
from pathlib import Path
import logging

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_frames(
    video_path: str,
    output_dir: str,
    frame_rate: int = 2,
    max_frames: int = None,
    format: str = 'jpg',
    quality: int = 95
):
    """
    Extract frames from a video file.

    Args:
        video_path: Path to input video
        output_dir: Directory to save frames
        frame_rate: Extract 1 frame every N seconds
        max_frames: Maximum number of frames to extract
        format: Output image format (jpg/png)
        quality: JPEG quality (0-100)

    Returns:
        Number of frames extracted
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)

    # Validate video exists
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Extracting frames from: {video_path.name}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Frame rate: 1 frame every {frame_rate} seconds")

    # Open video
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        raise ValueError(f"Failed to open video: {video_path}")

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    logger.info(f"Video info:")
    logger.info(f"  Resolution: {width}x{height}")
    logger.info(f"  FPS: {fps:.2f}")
    logger.info(f"  Total frames: {total_frames}")
    logger.info(f"  Duration: {duration:.2f}s")

    # Calculate frame skip
    skip_frames = int(fps * frame_rate)
    logger.info(f"  Skipping {skip_frames} frames between extractions")

    # Extract frames
    frame_count = 0
    extracted_count = 0
    video_name = video_path.stem

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Check if we should extract this frame
        if frame_count % skip_frames == 0:
            # Generate filename
            timestamp = frame_count / fps
            filename = f"{video_name}_frame_{extracted_count:04d}_t{timestamp:.2f}s.{format}"
            output_path = output_dir / filename

            # Save frame
            if format.lower() == 'jpg':
                cv2.imwrite(
                    str(output_path),
                    frame,
                    [cv2.IMWRITE_JPEG_QUALITY, quality]
                )
            else:
                cv2.imwrite(str(output_path), frame)

            logger.debug(f"Saved: {filename}")
            extracted_count += 1

            # Check max frames limit
            if max_frames and extracted_count >= max_frames:
                logger.info(f"Reached max frames limit: {max_frames}")
                break

        frame_count += 1

        # Progress update every 100 frames
        if frame_count % 100 == 0:
            progress = (frame_count / total_frames) * 100
            logger.info(f"Progress: {progress:.1f}% ({extracted_count} frames extracted)")

    cap.release()

    logger.info(f"✓ Extraction complete!")
    logger.info(f"  Processed: {frame_count} frames")
    logger.info(f"  Extracted: {extracted_count} frames")
    logger.info(f"  Output: {output_dir}")

    return extracted_count


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Extract frames from video files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract 1 frame every 2 seconds
  python scripts/extract_frames.py --video data/videos/street.mp4

  # Extract 1 frame every 5 seconds, max 20 frames
  python scripts/extract_frames.py --video data/videos/street.mp4 --rate 5 --max 20

  # Custom output directory
  python scripts/extract_frames.py --video data/videos/street.mp4 --output my_frames/

  # High quality PNG
  python scripts/extract_frames.py --video data/videos/street.mp4 --format png
        """
    )

    parser.add_argument(
        '--video',
        type=str,
        required=True,
        help='Path to input video file'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help=f'Output directory (default: {config.FRAMES_DIR})'
    )

    parser.add_argument(
        '--rate',
        type=int,
        default=config.FRAME_EXTRACTION_RATE,
        help=f'Extract 1 frame every N seconds (default: {config.FRAME_EXTRACTION_RATE})'
    )

    parser.add_argument(
        '--max',
        type=int,
        default=None,
        help='Maximum number of frames to extract (default: no limit)'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['jpg', 'png'],
        default='jpg',
        help='Output image format (default: jpg)'
    )

    parser.add_argument(
        '--quality',
        type=int,
        default=95,
        help='JPEG quality 0-100 (default: 95)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine output directory
    output_dir = args.output or config.FRAMES_DIR

    try:
        # Extract frames
        num_frames = extract_frames(
            video_path=args.video,
            output_dir=output_dir,
            frame_rate=args.rate,
            max_frames=args.max,
            format=args.format,
            quality=args.quality
        )

        print(f"\n✓ Successfully extracted {num_frames} frames")

    except Exception as e:
        logger.error(f"✗ Error: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()


# TODO: Add support for extracting specific time ranges
# TODO: Add support for extracting frames at specific timestamps
# TODO: Add support for resizing frames during extraction
# TODO: Add support for batch processing multiple videos
# TODO: Add preview mode (show frames before saving)
# TODO: Add frame deduplication (skip similar frames)
# TODO: Add motion detection (only extract frames with changes)
