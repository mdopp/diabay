"""
Automatic image orientation detection using Tesseract OSD
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class OrientationDetector:
    """Detect and correct image orientation automatically"""

    @staticmethod
    def detect_orientation_tesseract(image_path: Path) -> Optional[int]:
        """
        Use Tesseract OSD to detect image orientation

        Returns:
            Rotation angle in degrees (0, 90, 180, 270) or None if detection fails
        """
        try:
            import pytesseract
            from PIL import Image

            # Load image
            img = Image.open(image_path)

            # Run OSD (Orientation and Script Detection)
            osd_data = pytesseract.image_to_osd(img)

            # Parse OSD output
            for line in osd_data.split('\n'):
                if 'Rotate' in line:
                    # Extract rotation angle
                    # Format: "Rotate: 90"
                    angle = int(line.split(':')[1].strip())
                    logger.info(f"Tesseract OSD detected rotation: {angle}°")
                    return angle

            return None

        except ImportError:
            logger.warning("pytesseract not available for orientation detection")
            return None
        except Exception as e:
            logger.debug(f"Tesseract OSD failed: {e}")
            return None

    @staticmethod
    def detect_orientation_content(image: np.ndarray) -> Optional[int]:
        """
        Detect orientation based on content analysis (faces, text, edges)

        Returns:
            Rotation angle (0, 90, 180, 270) or None if uncertain
        """
        try:
            # Strategy 1: Face detection
            face_angle = OrientationDetector._detect_by_faces(image)
            if face_angle is not None:
                logger.info(f"Orientation detected by faces: {face_angle}°")
                return face_angle

            # Strategy 2: Edge directionality
            edge_angle = OrientationDetector._detect_by_edges(image)
            if edge_angle is not None:
                logger.info(f"Orientation detected by edges: {edge_angle}°")
                return edge_angle

            return None

        except Exception as e:
            logger.debug(f"Content-based orientation detection failed: {e}")
            return None

    @staticmethod
    def _detect_by_faces(image: np.ndarray) -> Optional[int]:
        """
        Try to detect orientation based on face detection in different rotations
        """
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )

            # Try each rotation and count faces detected
            max_faces = 0
            best_rotation = None

            for angle in [0, 90, 180, 270]:
                if angle == 0:
                    rotated = image
                elif angle == 90:
                    rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
                elif angle == 180:
                    rotated = cv2.rotate(image, cv2.ROTATE_180)
                else:  # 270
                    rotated = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

                # Convert to grayscale for face detection
                gray = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)

                # Detect faces
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(30, 30)
                )

                if len(faces) > max_faces:
                    max_faces = len(faces)
                    best_rotation = angle

            # Only return if we found at least one face
            if max_faces > 0:
                return best_rotation

            return None

        except Exception as e:
            logger.debug(f"Face-based orientation detection failed: {e}")
            return None

    @staticmethod
    def _detect_by_edges(image: np.ndarray) -> Optional[int]:
        """
        Detect orientation based on edge distribution
        Images are typically wider than tall, with horizontal edges
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply Canny edge detection
            edges = cv2.Canny(gray, 50, 150)

            # Calculate edge density in horizontal vs vertical directions
            h_edges = np.sum(edges, axis=1)  # Sum along width (horizontal edges)
            v_edges = np.sum(edges, axis=0)  # Sum along height (vertical edges)

            # Detect if image seems upside down or sideways based on edge distribution
            # This is a simple heuristic - most photos have more detail/edges at bottom

            height, width = image.shape[:2]

            # Check if image is extremely tall (might be rotated 90°)
            aspect = width / height

            if aspect < 0.6:  # Very tall - likely needs 90° rotation
                return 90
            elif aspect > 1.7:  # Very wide - likely correct or needs 180°
                # Check top vs bottom edge density to detect upside down
                top_half_edges = np.sum(h_edges[:height//2])
                bottom_half_edges = np.sum(h_edges[height//2:])

                # If top has significantly more edges, might be upside down
                if top_half_edges > bottom_half_edges * 1.5:
                    return 180

            return None  # Can't determine with confidence

        except Exception as e:
            logger.debug(f"Edge-based orientation detection failed: {e}")
            return None

    @staticmethod
    def auto_detect_orientation(image_path: Path, image: Optional[np.ndarray] = None) -> int:
        """
        Automatically detect the correct orientation for an image

        Args:
            image_path: Path to image file
            image: Optional pre-loaded image array

        Returns:
            Recommended rotation angle (0, 90, 180, 270)
        """
        logger.info(f"Auto-detecting orientation for: {image_path.name}")

        # Try Tesseract OSD first (most reliable for text)
        angle = OrientationDetector.detect_orientation_tesseract(image_path)
        if angle is not None:
            return angle

        # Fall back to content analysis
        if image is None:
            image = cv2.imread(str(image_path))

        if image is not None:
            angle = OrientationDetector.detect_orientation_content(image)
            if angle is not None:
                return angle

        # Default: no rotation
        logger.info("Could not detect orientation, assuming correct (0°)")
        return 0
