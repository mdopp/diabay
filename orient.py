"""
Rotation detection for scanned slides.
Uses Tesseract OSD (via subprocess) with face detection fallback.
"""
import subprocess
import logging
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def detect_orientation_tesseract(image_path: Path) -> Optional[int]:
    """
    Use Tesseract OSD via subprocess to detect rotation.
    Returns 0, 90, 180, or 270, or None if detection fails.
    """
    try:
        # Tesseract --psm 0 = OSD only
        result = subprocess.run(
            ["tesseract", str(image_path), "-", "--psm", "0"],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.split("\n"):
            if "Rotate" in line:
                angle = int(line.split(":")[1].strip())
                logger.info(f"Tesseract OSD detected rotation: {angle}°")
                return angle
    except FileNotFoundError:
        logger.debug("Tesseract not installed, skipping OSD detection")
    except subprocess.TimeoutExpired:
        logger.debug("Tesseract OSD timed out")
    except Exception as e:
        logger.debug(f"Tesseract OSD failed: {e}")
    return None


def detect_orientation_faces(image: np.ndarray, min_neighbors: int = 10,
                             min_face_size: int = 0) -> Optional[int]:
    """
    Try 4 rotations, detect faces with Haar cascade, pick rotation with most faces.
    Only returns a rotation if the best candidate has strictly more faces than
    all other rotations (clear winner). Returns None if ambiguous or no faces.

    Args:
        min_neighbors: Higher = fewer false positives (default 8, opencv default is 3).
        min_face_size: Minimum face width/height in pixels (default 50).
    """
    try:
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        if min_face_size <= 0:
            h, w = image.shape[:2]
            min_face_size = max(80, min(h, w) // 35)

        counts = {}
        for angle in [0, 90, 180, 270]:
            if angle == 0:
                rotated = image
            elif angle == 90:
                rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                rotated = cv2.rotate(image, cv2.ROTATE_180)
            else:
                rotated = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

            gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=min_neighbors,
                minSize=(min_face_size, min_face_size)
            )
            counts[angle] = len(faces)

        best_angle = max(counts, key=counts.get)
        best_count = counts[best_angle]
        second_best = max(c for a, c in counts.items() if a != best_angle)

        if best_count == 0:
            return None

        # Require clear winner: best must have strictly more faces than any other
        if best_count <= second_best:
            logger.debug(f"Ambiguous rotation: {counts} — skipping")
            return None

        logger.info(f"Face detection: {best_angle}° ({best_count} faces, runner-up {second_best}) — {counts}")
        return best_angle
    except Exception as e:
        logger.debug(f"Face-based orientation detection failed: {e}")
    return None


def detect_orientation_exif(image_path: Path) -> Optional[int]:
    """
    Check EXIF Orientation tag. Scanners often set this correctly.
    EXIF orientation values: 1=normal, 3=180°, 6=90°CW, 8=270°CW
    """
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            exif = img.getexif()
            if exif:
                orient = exif.get(274)  # 274 = Orientation tag
                if orient == 3:
                    return 180
                elif orient == 6:
                    return 90
                elif orient == 8:
                    return 270
                elif orient == 1:
                    return 0
    except Exception as e:
        logger.debug(f"EXIF orientation check failed: {e}")
    return None


def detect_orientation(image_path: Path, image: Optional[np.ndarray] = None) -> int:
    """
    Detect orientation from EXIF tag only.
    Auto-detection (Tesseract/face) is unreliable on scanned slides —
    use the review UI for manual correction instead.
    Returns rotation angle: 0, 90, 180, or 270.
    """
    angle = detect_orientation_exif(image_path)
    if angle is not None:
        if angle > 0:
            logger.info(f"EXIF orientation for {image_path.name}: {angle}°")
        return angle

    return 0


def apply_rotation(image: np.ndarray, angle: int) -> np.ndarray:
    """Apply rotation correction to image. Angle is 0, 90, 180, or 270."""
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image
