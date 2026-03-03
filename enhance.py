"""
Image enhancement pipeline for scanned slides.
Stages: CLAHE (histogram/contrast) + optional OpenVINO Real-ESRGAN (NPU/GPU/CPU).
"""
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Preset(Enum):
    GENTLE = ("gentle", 0.3, 1.0)
    BALANCED = ("balanced", 0.5, 1.5)
    AGGRESSIVE = ("aggressive", 0.7, 2.0)

    def __init__(self, preset_name: str, hist_clip: float, clahe_clip: float):
        self.preset_name = preset_name
        self.hist_clip = hist_clip
        self.clahe_clip = clahe_clip


@dataclass
class EnhanceResult:
    image: np.ndarray
    preset: str
    quality_score: float
    faces_detected: int
    accelerator: str  # "NPU", "GPU", "CPU", or "none"


# ---------------------------------------------------------------------------
# 16-bit to 8-bit conversion
# ---------------------------------------------------------------------------

def convert_16bit_to_8bit(img: np.ndarray) -> np.ndarray:
    """Convert 16-bit image to 8-bit using percentile stretching per channel."""
    if img.dtype != np.uint16:
        return img
    if len(img.shape) == 3:
        result = np.zeros(img.shape, dtype=np.uint8)
        for c in range(img.shape[2]):
            ch = img[:, :, c]
            p_low = np.percentile(ch, 0.1)
            p_high = np.percentile(ch, 99.9)
            if p_high > p_low:
                stretched = (ch.astype(np.float32) - p_low) / (p_high - p_low) * 255
            else:
                stretched = ch.astype(np.float32) / 256
            result[:, :, c] = np.clip(stretched, 0, 255).astype(np.uint8)
        return result
    p_low = np.percentile(img, 0.1)
    p_high = np.percentile(img, 99.9)
    if p_high > p_low:
        return np.clip(
            (img.astype(np.float32) - p_low) / (p_high - p_low) * 255, 0, 255
        ).astype(np.uint8)
    return (img / 256).astype(np.uint8)


# ---------------------------------------------------------------------------
# CLAHE pipeline
# ---------------------------------------------------------------------------

def auto_levels_histogram(img: np.ndarray, clip_pct: float = 0.5) -> np.ndarray:
    """Remove gray haze using histogram stretching."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hist, _ = np.histogram(gray.flatten(), 256, [0, 256])
    cdf = hist.cumsum()
    total = gray.shape[0] * gray.shape[1]
    clip_pixels = int(total * clip_pct / 100)

    min_gray = int(np.searchsorted(cdf, clip_pixels))
    max_gray = int(np.searchsorted(cdf, total - clip_pixels))

    if max_gray > min_gray:
        alpha = 255.0 / (max_gray - min_gray)
        beta = -alpha * min_gray
        return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    return img


def apply_lab_clahe(img: np.ndarray, clip_limit: float = 1.5) -> np.ndarray:
    """Apply CLAHE to L-channel in LAB color space (preserves colors)."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    h, w = img.shape[:2]
    grid = max(4, min(16, max(h, w) // 500))
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid, grid))
    l = clahe.apply(l)

    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def detect_faces(img: np.ndarray) -> list:
    """Detect faces using Haar cascade. Returns list of (x,y,w,h)."""
    try:
        h, w = img.shape[:2]
        if h > 8000 or w > 8000:
            return []
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        min_face = max(80, min(h, w) // 35)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=8, minSize=(min_face, min_face))
        return list(faces) if len(faces) > 0 else []
    except Exception as e:
        logger.debug(f"Face detection failed: {e}")
        return []


def apply_face_aware_clahe(img: np.ndarray, faces: list, clip_limit: float = 1.5) -> np.ndarray:
    """Apply gentler CLAHE to face regions, full CLAHE elsewhere."""
    full_enhanced = apply_lab_clahe(img, clip_limit)
    gentle_enhanced = apply_lab_clahe(img, clip_limit * 0.5)

    mask = np.zeros(img.shape[:2], dtype=np.float32)
    for (x, y, w, h) in faces:
        margin = int(max(w, h) * 0.3)
        x1, y1 = max(0, x - margin), max(0, y - margin)
        x2, y2 = min(img.shape[1], x + w + margin), min(img.shape[0], y + h + margin)
        center = ((x1 + x2) // 2, (y1 + y2) // 2)
        axes = ((x2 - x1) // 2, (y2 - y1) // 2)
        cv2.ellipse(mask, center, axes, 0, 0, 360, 1.0, -1)

    mask = cv2.GaussianBlur(mask, (51, 51), 0)
    mask3 = np.expand_dims(mask, axis=2)
    return (gentle_enhanced * mask3 + full_enhanced * (1 - mask3)).astype(np.uint8)


def calculate_quality_score(img: np.ndarray) -> float:
    """Quality score 0-100: sharpness (40%) + contrast (30%) + range (30%)."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness_score = min(100.0, laplacian.var() / 100)
    std_dev = gray.std()
    contrast_score = 100.0 * (1 - abs(std_dev - 55) / 55)
    dynamic_range = float(gray.max()) - float(gray.min())
    range_score = (dynamic_range / 255) * 100
    return sharpness_score * 0.4 + contrast_score * 0.3 + range_score * 0.3


def clahe_pipeline(img: np.ndarray, preset: Preset) -> Tuple[np.ndarray, int]:
    """Full CLAHE pipeline: histogram stretch + LAB CLAHE + face-aware blending."""
    img = auto_levels_histogram(img, preset.hist_clip)
    faces = detect_faces(img)
    if faces:
        img = apply_face_aware_clahe(img, faces, preset.clahe_clip)
    else:
        img = apply_lab_clahe(img, preset.clahe_clip)
    return img, len(faces)


# ---------------------------------------------------------------------------
# OpenVINO super-resolution accelerator
# Uses Intel's single-image-super-resolution-1033 (pre-converted IR model)
# ---------------------------------------------------------------------------

_MODEL_BASE = "https://storage.openvinotoolkit.org/repositories/open_model_zoo/temp/single-image-super-resolution-1033/FP16"
_MODEL_FILES = ["single-image-super-resolution-1033.xml", "single-image-super-resolution-1033.bin"]
_MODEL_SCALE = 3  # This model upscales 3x

_ov_model = None
_ov_device = "none"


def _get_ov_model() -> Tuple[Optional[object], str]:
    """
    Load Intel super-resolution model via OpenVINO.
    Tries NPU first, then GPU, then CPU.
    Returns (compiled_model, device_name) or (None, "none").
    """
    global _ov_model, _ov_device
    if _ov_model is not None:
        return _ov_model, _ov_device
    if _ov_device == "failed":
        return None, "none"

    try:
        import openvino as ov
    except ImportError:
        logger.info("OpenVINO not installed — using CLAHE only (pip install openvino)")
        _ov_device = "failed"
        return None, "none"

    # Download model files if needed
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "diabay")
    os.makedirs(cache_dir, exist_ok=True)

    for fname in _MODEL_FILES:
        local_path = os.path.join(cache_dir, fname)
        if not os.path.exists(local_path):
            url = f"{_MODEL_BASE}/{fname}"
            logger.info(f"Downloading {fname}...")
            import urllib.request
            urllib.request.urlretrieve(url, local_path)

    xml_path = os.path.join(cache_dir, _MODEL_FILES[0])

    core = ov.Core()
    available = core.available_devices
    logger.info(f"OpenVINO devices: {available}")

    model = core.read_model(xml_path)

    # Try devices in priority order
    for device in ["NPU", "GPU", "CPU"]:
        if device not in available:
            continue
        try:
            compiled = core.compile_model(model, device)
            _ov_model = compiled
            _ov_device = device
            logger.info(f"Super-resolution loaded on {device}")
            return compiled, device
        except Exception as e:
            logger.info(f"Cannot use {device}: {e}")
            continue

    logger.info("No OpenVINO device available for super-resolution")
    _ov_device = "failed"
    return None, "none"


def apply_openvino_sr(img: np.ndarray, tile_size: int = 480) -> Tuple[np.ndarray, str]:
    """
    Enhance image using OpenVINO super-resolution with tiling.
    The model expects two inputs:
      - original image [1,3,H,W]
      - bicubic-upscaled image [1,3,H*3,W*3]
    Returns (enhanced_image, device_used). Output is at original resolution.
    """
    compiled, device = _get_ov_model()
    if compiled is None:
        return img, "none"

    h, w = img.shape[:2]
    scale = _MODEL_SCALE

    # Process in tiles for large images
    output_full = np.zeros((h * scale, w * scale, 3), dtype=np.float32)

    for y in range(0, h, tile_size):
        for x in range(0, w, tile_size):
            th = min(tile_size, h - y)
            tw = min(tile_size, w - x)
            tile = img[y:y + th, x:x + tw]

            # Prepare inputs: original tile and bicubic-upscaled tile
            lr = tile.astype(np.float32) / 255.0
            lr_blob = np.transpose(lr, (2, 0, 1))  # HWC -> CHW
            lr_blob = np.expand_dims(lr_blob, 0)  # [1,3,H,W]

            bicubic = cv2.resize(tile, (tw * scale, th * scale), interpolation=cv2.INTER_CUBIC)
            bi = bicubic.astype(np.float32) / 255.0
            bi_blob = np.transpose(bi, (2, 0, 1))
            bi_blob = np.expand_dims(bi_blob, 0)  # [1,3,H*3,W*3]

            try:
                result = compiled([lr_blob, bi_blob])[0]
                result = np.squeeze(result, 0)
                result = np.transpose(result, (1, 2, 0))  # CHW -> HWC
                output_full[y * scale:(y + th) * scale, x * scale:(x + tw) * scale] = result
            except Exception as e:
                # Fallback: use bicubic upscale for this tile
                logger.debug(f"SR tile failed: {e}")
                output_full[y * scale:(y + th) * scale, x * scale:(x + tw) * scale] = bi

    output_full = np.clip(output_full * 255, 0, 255).astype(np.uint8)

    # Downscale back to original size (we want enhancement, not upscaling)
    output_full = cv2.resize(output_full, (w, h), interpolation=cv2.INTER_AREA)
    return output_full, device


# ---------------------------------------------------------------------------
# Main enhance function
# ---------------------------------------------------------------------------

def enhance_image(img: np.ndarray, preset_name: str = "auto",
                  use_accelerator: bool = True) -> EnhanceResult:
    """
    Full enhancement pipeline:
    1. 16-bit to 8-bit conversion
    2. CLAHE (histogram stretch + contrast + face-aware)
    3. OpenVINO Real-ESRGAN if available (NPU > GPU > CPU)

    Falls back to CLAHE-only if OpenVINO is not installed.
    """
    img = convert_16bit_to_8bit(img)

    if preset_name == "auto":
        best_img, best_score, best_preset, best_faces = None, -1, "balanced", 0
        for preset in Preset:
            enhanced, face_count = clahe_pipeline(img.copy(), preset)
            score = calculate_quality_score(enhanced)
            if score > best_score:
                best_img, best_score, best_preset, best_faces = enhanced, score, preset.preset_name, face_count
        img = best_img
        used_preset = best_preset
        quality = best_score
        faces = best_faces
    else:
        preset_map = {p.preset_name: p for p in Preset}
        preset = preset_map.get(preset_name, Preset.BALANCED)
        img, faces = clahe_pipeline(img, preset)
        quality = calculate_quality_score(img)
        used_preset = preset.preset_name

    # OpenVINO super-resolution enhancement
    accelerator = "none"
    if use_accelerator:
        img, accelerator = apply_openvino_sr(img)

    return EnhanceResult(
        image=img,
        preset=used_preset,
        quality_score=quality,
        faces_detected=faces,
        accelerator=accelerator,
    )
