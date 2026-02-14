"""
Image Enhancement Processor for DiaBay
Handles all image processing: enhancement, format conversion, quality optimization
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum


class EnhancementPreset(Enum):
    """Pre-defined enhancement presets"""
    GENTLE = ("gentle", 0.3, 1.0)
    BALANCED = ("balanced", 0.5, 1.5)
    AGGRESSIVE = ("aggressive", 0.7, 2.0)

    def __init__(self, name: str, hist_clip: float, clahe_clip: float):
        self.preset_name = name
        self.hist_clip = hist_clip
        self.clahe_clip = clahe_clip


@dataclass
class ProcessingResult:
    """Result of image processing"""
    enhanced: np.ndarray
    original_size: Tuple[int, int]
    enhancement_params: Dict[str, float]
    face_detected: bool
    quality_score: float


class ImageProcessor:
    """
    Main image processing pipeline for analog slide enhancement
    """

    def __init__(self,
                 histogram_clip: float = 0.5,
                 clahe_clip: float = 1.5,
                 adaptive_grid: bool = True,
                 face_detection: bool = True):
        """
        Initialize processor with enhancement parameters

        Args:
            histogram_clip: Percentage to clip from histogram tails (0.0-1.0)
            clahe_clip: Contrast limiting threshold for CLAHE
            adaptive_grid: Automatically adapt CLAHE grid to image resolution
            face_detection: Enable face-aware gentle enhancement
        """
        self.histogram_clip = histogram_clip
        self.clahe_clip = clahe_clip
        self.adaptive_grid = adaptive_grid
        self.face_detection = face_detection

        # Initialize face detector (lazy loaded)
        self._face_cascade = None

    def process_image(self,
                     image_path: Path,
                     preset: Optional[EnhancementPreset] = None,
                     auto_quality: bool = False) -> ProcessingResult:
        """
        Process a single image with enhancement

        Args:
            image_path: Path to input image (TIFF or JPEG)
            preset: Use predefined enhancement preset
            auto_quality: Automatically select best preset

        Returns:
            ProcessingResult with enhanced image and metadata
        """
        # Load image
        img = self._load_image(image_path)
        original_size = (img.shape[1], img.shape[0])

        # Use preset if specified
        if preset:
            self.histogram_clip = preset.hist_clip
            self.clahe_clip = preset.clahe_clip

        # Auto-quality: try multiple presets and select best
        if auto_quality:
            return self._process_with_auto_quality(img, original_size)

        # Standard enhancement pipeline
        enhanced = self._enhance_image(img)

        # Calculate quality score
        quality_score = self._calculate_quality_score(enhanced)

        return ProcessingResult(
            enhanced=enhanced,
            original_size=original_size,
            enhancement_params={
                'histogram_clip': self.histogram_clip,
                'clahe_clip': self.clahe_clip
            },
            face_detected=False,  # Set by face detection if enabled
            quality_score=quality_score
        )

    def _load_image(self, image_path: Path) -> np.ndarray:
        """Load image and convert to 8-bit BGR if necessary"""
        img = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)

        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Convert 16-bit to 8-bit using improved percentile stretching
        if img.dtype == np.uint16:
            img = self._convert_16bit_to_8bit(img, method='percentile')

        # Ensure BGR format
        if len(img.shape) == 2:  # Grayscale
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        return img

    def _convert_16bit_to_8bit(self,
                               img: np.ndarray,
                               method: str = 'percentile',
                               per_channel: bool = False) -> np.ndarray:
        """
        Convert 16-bit image to 8-bit with multiple strategies

        Args:
            img: 16-bit input image
            method: 'percentile' (clip extremes), 'full_range' (preserve all)
            per_channel: Apply conversion per-channel (handles color casts)

        Returns:
            8-bit image
        """
        if method == 'percentile':
            if per_channel and len(img.shape) == 3:
                # Per-channel percentile stretching
                result = np.zeros_like(img, dtype=np.uint8)
                for c in range(img.shape[2]):
                    channel = img[:, :, c]
                    p_low = np.percentile(channel, 0.1)
                    p_high = np.percentile(channel, 99.9)
                    stretched = np.clip(
                        (channel.astype(np.float32) - p_low) / (p_high - p_low) * 255,
                        0, 255
                    )
                    result[:, :, c] = stretched.astype(np.uint8)
                return result
            else:
                # Global percentile stretching
                p_low = np.percentile(img, 0.1)
                p_high = np.percentile(img, 99.9)
                return np.clip(
                    (img.astype(np.float32) - p_low) / (p_high - p_low) * 255,
                    0, 255
                ).astype(np.uint8)

        elif method == 'full_range':
            # Preserve full range (for archival)
            return (img / 256).astype(np.uint8)

        else:
            raise ValueError(f"Unknown conversion method: {method}")

    def _enhance_image(self, img: np.ndarray) -> np.ndarray:
        """
        Main enhancement pipeline

        Steps:
        1. Auto-levels (histogram stretching)
        2. LAB CLAHE (local contrast)
        3. Face-aware blending (if faces detected)
        """
        # Step 1: Histogram stretching
        img = self._auto_levels_histogram(img)

        # Step 2: CLAHE in LAB color space
        img = self._apply_lab_clahe(img)

        # Step 3: Face-aware enhancement (optional)
        if self.face_detection:
            faces = self._detect_faces(img)
            if len(faces) > 0:
                img = self._apply_face_aware_enhancement(img, faces)

        return img

    def _auto_levels_histogram(self, img: np.ndarray) -> np.ndarray:
        """
        Remove gray haze using histogram stretching

        Clips bottom/top percentiles and stretches dynamic range
        """
        # Convert to grayscale for histogram calculation
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Calculate cumulative histogram
        hist, bins = np.histogram(gray.flatten(), 256, [0, 256])
        cdf = hist.cumsum()
        cdf_normalized = cdf * hist.max() / cdf.max()

        # Find clip points
        total_pixels = gray.shape[0] * gray.shape[1]
        clip_pixels = int(total_pixels * self.histogram_clip / 100)

        min_gray = np.searchsorted(cdf, clip_pixels)
        max_gray = np.searchsorted(cdf, total_pixels - clip_pixels)

        # Stretch each channel
        if max_gray > min_gray:
            alpha = 255.0 / (max_gray - min_gray)
            beta = -alpha * min_gray

            result = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
            return result

        return img

    def _apply_lab_clahe(self, img: np.ndarray) -> np.ndarray:
        """
        Apply CLAHE only to L-channel in LAB color space

        This enhances local contrast while preserving natural colors
        """
        # Convert BGR to LAB
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Calculate adaptive grid size
        if self.adaptive_grid:
            grid_size = self._calculate_adaptive_grid(img.shape)
        else:
            grid_size = (8, 8)

        # Apply CLAHE to L-channel
        clahe = cv2.createCLAHE(
            clipLimit=self.clahe_clip,
            tileGridSize=grid_size
        )
        l_enhanced = clahe.apply(l)

        # Merge channels
        lab_enhanced = cv2.merge([l_enhanced, a, b])

        # Convert back to BGR
        return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

    def _calculate_adaptive_grid(self, shape: Tuple[int, int, int]) -> Tuple[int, int]:
        """
        Calculate optimal CLAHE grid size based on image resolution

        For high-res scans (3600×2400), uses 8×5 instead of fixed 8×8
        """
        height, width = shape[:2]

        grid_width = max(4, min(16, width // 450))
        grid_height = max(4, min(16, height // 450))

        return (grid_width, grid_height)

    def _detect_faces(self, img: np.ndarray) -> list:
        """
        Detect faces using Haar Cascade

        TODO: Replace with MTCNN for better accuracy
        """
        try:
            # Validate image
            if img is None or img.size == 0:
                return []

            # Check image dimensions - skip if too large (memory issues)
            height, width = img.shape[:2]
            if height > 8000 or width > 8000:
                logger.warning(f"Image too large for face detection: {width}x{height}")
                return []

            if self._face_cascade is None:
                self._face_cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Ensure gray image is valid
            if gray is None or gray.size == 0:
                return []

            faces = self._face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )

            return faces
        except cv2.error as e:
            logger.warning(f"OpenCV face detection error: {e}")
            return []
        except Exception as e:
            logger.warning(f"Face detection failed: {e}")
            return []

    def _apply_face_aware_enhancement(self,
                                     img: np.ndarray,
                                     faces: list) -> np.ndarray:
        """
        Apply gentler enhancement to face regions

        Creates soft-edged masks around faces and blends
        gentle enhancement (50% CLAHE) with full enhancement
        """
        # Create gentle enhancement (lower CLAHE)
        gentle_clahe = self.clahe_clip * 0.5
        original_clahe = self.clahe_clip
        self.clahe_clip = gentle_clahe

        gentle_enhanced = self._apply_lab_clahe(img)
        self.clahe_clip = original_clahe

        # Create face mask
        mask = np.zeros(img.shape[:2], dtype=np.float32)

        for (x, y, w, h) in faces:
            # Expand face region by 30%
            margin = int(max(w, h) * 0.3)
            x1, y1 = max(0, x - margin), max(0, y - margin)
            x2, y2 = min(img.shape[1], x + w + margin), min(img.shape[0], y + h + margin)

            # Create elliptical soft mask
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            axes = ((x2 - x1) // 2, (y2 - y1) // 2)
            cv2.ellipse(mask, center, axes, 0, 0, 360, 1.0, -1)

        # Apply Gaussian blur for soft edges
        mask = cv2.GaussianBlur(mask, (51, 51), 0)
        mask = np.expand_dims(mask, axis=2)

        # Blend: gentle for faces, full for rest
        result = (gentle_enhanced * mask + img * (1 - mask)).astype(np.uint8)

        return result

    def _process_with_auto_quality(self,
                                   img: np.ndarray,
                                   original_size: Tuple[int, int]) -> ProcessingResult:
        """
        Try multiple presets and select the best one based on quality metrics
        """
        best_result = None
        best_score = 0

        for preset in EnhancementPreset:
            self.histogram_clip = preset.hist_clip
            self.clahe_clip = preset.clahe_clip

            enhanced = self._enhance_image(img.copy())
            score = self._calculate_quality_score(enhanced)

            if score > best_score:
                best_score = score
                best_result = (enhanced, preset)

        enhanced, preset = best_result

        return ProcessingResult(
            enhanced=enhanced,
            original_size=original_size,
            enhancement_params={
                'histogram_clip': preset.hist_clip,
                'clahe_clip': preset.clahe_clip,
                'preset': preset.preset_name
            },
            face_detected=False,
            quality_score=best_score
        )

    def _calculate_quality_score(self, img: np.ndarray) -> float:
        """
        Calculate image quality score (0-100)

        Combines:
        - Sharpness (Laplacian variance) - 40%
        - Contrast (standard deviation) - 30%
        - Dynamic range - 30%
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Sharpness (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = laplacian.var()
        sharpness_score = min(100, sharpness / 100)  # Normalize

        # Contrast (std dev, targeting 50-60)
        std_dev = gray.std()
        contrast_score = 100 * (1 - abs(std_dev - 55) / 55)

        # Dynamic range
        dynamic_range = gray.max() - gray.min()
        range_score = (dynamic_range / 255) * 100

        # Weighted combination
        total_score = (
            sharpness_score * 0.4 +
            contrast_score * 0.3 +
            range_score * 0.3
        )

        return total_score

    def save_enhanced(self,
                     enhanced: np.ndarray,
                     output_path: Path,
                     quality: int = 95,
                     formats: list = ['jpg']) -> Dict[str, Path]:
        """
        Save enhanced image in multiple formats

        Args:
            enhanced: Enhanced image array
            output_path: Base output path (without extension)
            quality: JPEG quality (0-100)
            formats: List of formats: 'jpg', 'jxl', 'png', 'tiff'

        Returns:
            Dict mapping format to saved file path
        """
        saved_files = {}

        for fmt in formats:
            if fmt == 'jpg':
                path = output_path.with_suffix('.jpg')
                cv2.imwrite(
                    str(path),
                    enhanced,
                    [cv2.IMWRITE_JPEG_QUALITY, quality]
                )
                saved_files['jpg'] = path

            elif fmt == 'png':
                path = output_path.with_suffix('_archive.png')
                cv2.imwrite(str(path), enhanced)
                saved_files['png'] = path

            elif fmt == 'tiff':
                # Save as 16-bit TIFF for archival
                path = output_path.with_suffix('_16bit.tif')
                # Convert back to 16-bit
                img_16bit = (enhanced.astype(np.float32) * 256).astype(np.uint16)
                cv2.imwrite(str(path), img_16bit)
                saved_files['tiff'] = path

            elif fmt == 'jxl':
                # JPEG XL support (requires pillow-jxl plugin)
                try:
                    from PIL import Image
                    path = output_path.with_suffix('.jxl')
                    # Convert BGR to RGB
                    rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
                    Image.fromarray(rgb).save(str(path), 'JPEG_XL', quality=quality)
                    saved_files['jxl'] = path
                except Exception:
                    # JPEG XL not available, skip
                    pass

        return saved_files
