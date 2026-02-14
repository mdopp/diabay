#!/usr/bin/env python3
"""
Test automatic orientation detection
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.orientation_detector import OrientationDetector
import cv2
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def test_auto_orientation(image_path: Path):
    """Test automatic orientation detection on an image"""

    print(f"\n{'='*70}")
    print(f"Testing Automatic Orientation Detection")
    print(f"Image: {image_path.name}")
    print(f"{'='*70}\n")

    # Load image for content analysis
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"❌ Could not load image: {image_path}")
        return

    print(f"Original dimensions: {img.shape[1]}×{img.shape[0]}")
    print(f"Aspect ratio: {img.shape[1]/img.shape[0]:.2f}\n")

    # Test 1: Tesseract OSD
    print("Test 1: Tesseract OSD Detection")
    print("-" * 70)
    try:
        angle = OrientationDetector.detect_orientation_tesseract(image_path)
        if angle is not None:
            print(f"✓ Tesseract detected rotation: {angle}°")
            if angle == 0:
                print("  → Image is correctly oriented")
            else:
                print(f"  → Image needs {angle}° rotation")
        else:
            print("⚠️  Tesseract OSD could not detect orientation")
    except Exception as e:
        print(f"❌ Tesseract test failed: {e}")

    # Test 2: Face detection
    print("\nTest 2: Face-Based Detection")
    print("-" * 70)
    try:
        angle = OrientationDetector._detect_by_faces(img)
        if angle is not None:
            print(f"✓ Face detection suggests rotation: {angle}°")
        else:
            print("⚠️  No faces detected or unclear orientation")
    except Exception as e:
        print(f"❌ Face detection failed: {e}")

    # Test 3: Edge analysis
    print("\nTest 3: Edge-Based Detection")
    print("-" * 70)
    try:
        angle = OrientationDetector._detect_by_edges(img)
        if angle is not None:
            print(f"✓ Edge analysis suggests rotation: {angle}°")
        else:
            print("⚠️  Edge analysis inconclusive")
    except Exception as e:
        print(f"❌ Edge analysis failed: {e}")

    # Final recommendation
    print("\n" + "="*70)
    print("FINAL RECOMMENDATION")
    print("="*70)
    angle = OrientationDetector.auto_detect_orientation(image_path, img)
    print(f"Recommended rotation: {angle}°")

    if angle == 0:
        print("✓ Image appears to be correctly oriented")
    else:
        print(f"→ Rotate image {angle}° clockwise to correct orientation")

    print()

if __name__ == "__main__":
    # Test the specific image
    test_image = Path("input/image_260204_133644.tif")

    if test_image.exists():
        test_auto_orientation(test_image)
    else:
        print(f"❌ Image not found: {test_image}")
        print("\nLooking for TIF files in input directory...")
        input_dir = Path("input")
        if input_dir.exists():
            tif_files = list(input_dir.glob("*.tif")) + list(input_dir.glob("*.tiff"))
            if tif_files:
                print(f"Found {len(tif_files)} TIF files:")
                for f in tif_files:
                    print(f"  - {f.name}")
                print(f"\nTesting first file: {tif_files[0].name}\n")
                test_auto_orientation(tif_files[0])
            else:
                print("No TIF files found in input directory")
