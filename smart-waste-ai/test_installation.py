#!/usr/bin/env python3
"""
Installation Test Script
========================
Verify that all dependencies are installed correctly.

Usage:
    python test_installation.py
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing Python package imports...")
    print("=" * 50)

    tests = [
        ("FastAPI", "fastapi"),
        ("Pydantic", "pydantic"),
        ("OpenCV", "cv2"),
        ("NumPy", "numpy"),
        ("PyTorch", "torch"),
        ("Ultralytics (YOLO)", "ultralytics"),
        ("Uvicorn", "uvicorn"),
    ]

    failed = []

    for name, module in tests:
        try:
            __import__(module)
            print(f"✓ {name:30s} OK")
        except ImportError as e:
            print(f"✗ {name:30s} FAILED: {e}")
            failed.append(name)

    print("=" * 50)

    if failed:
        print(f"\n❌ {len(failed)} package(s) failed to import:")
        for pkg in failed:
            print(f"   - {pkg}")
        print("\nRun: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All packages imported successfully!")
        return True


def test_yolo():
    """Test YOLOv8 model loading."""
    print("\nTesting YOLOv8 model loading...")
    print("=" * 50)

    try:
        from ultralytics import YOLO
        print("Attempting to load YOLOv8n model (will download if needed)...")
        model = YOLO('yolov8n.pt')
        print(f"✓ YOLOv8 model loaded successfully")
        print(f"  Model type: {type(model)}")
        return True
    except Exception as e:
        print(f"✗ Failed to load YOLOv8: {e}")
        return False


def test_pytorch():
    """Test PyTorch and device availability."""
    print("\nTesting PyTorch configuration...")
    print("=" * 50)

    try:
        import torch

        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")

        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"GPU device: {torch.cuda.get_device_name(0)}")

        # Check for Apple Silicon
        if hasattr(torch.backends, 'mps'):
            print(f"MPS (Apple Silicon) available: {torch.backends.mps.is_available()}")

        return True
    except Exception as e:
        print(f"✗ PyTorch test failed: {e}")
        return False


def test_project_structure():
    """Test that project structure is correct."""
    print("\nTesting project structure...")
    print("=" * 50)

    required_paths = [
        "ai/config.py",
        "ai/detection/yolo_detector.py",
        "ai/classification/fill_level_classifier.py",
        "ai/inference/pipeline.py",
        "backend/main.py",
        "backend/api/routes.py",
        "data/videos",
        "data/frames",
        "data/results",
    ]

    project_root = Path(__file__).parent
    missing = []

    for path_str in required_paths:
        path = project_root / path_str
        if path.exists():
            print(f"✓ {path_str:40s} EXISTS")
        else:
            print(f"✗ {path_str:40s} MISSING")
            missing.append(path_str)

    print("=" * 50)

    if missing:
        print(f"\n❌ {len(missing)} required path(s) missing:")
        for path in missing:
            print(f"   - {path}")
        return False
    else:
        print("\n✅ Project structure is correct!")
        return True


def test_modules():
    """Test that custom modules can be imported."""
    print("\nTesting custom modules...")
    print("=" * 50)

    # Add project root to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    modules = [
        "ai.config",
        "ai.detection.detector_interface",
        "ai.detection.yolo_detector",
        "ai.classification.classifier_interface",
        "ai.classification.fill_level_classifier",
        "ai.inference.pipeline",
        "backend.schemas.bin_status",
        "backend.services.inference_service",
    ]

    failed = []

    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module:50s} OK")
        except Exception as e:
            print(f"✗ {module:50s} FAILED: {e}")
            failed.append(module)

    print("=" * 50)

    if failed:
        print(f"\n❌ {len(failed)} module(s) failed to import:")
        for mod in failed:
            print(f"   - {mod}")
        return False
    else:
        print("\n✅ All custom modules imported successfully!")
        return True


def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("Smart Waste Monitoring - Installation Test")
    print("=" * 50 + "\n")

    results = []

    # Run tests
    results.append(("Package Imports", test_imports()))
    results.append(("Project Structure", test_project_structure()))
    results.append(("Custom Modules", test_modules()))
    results.append(("PyTorch", test_pytorch()))
    results.append(("YOLOv8", test_yolo()))

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name:30s} {status}")

    all_passed = all(result[1] for result in results)

    print("=" * 50)

    if all_passed:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\nNext steps:")
        print("  1. python backend/main.py          (start API)")
        print("  2. cd dashboard && npm install      (install dashboard)")
        print("  3. cd dashboard && npm run dev      (start dashboard)")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
