"""
AI-powered image tagging using CLIP and computer vision analysis.

Generates automatic tags for:
- Scene classification (landscape, portrait, cityscape, etc.)
- Lighting conditions (golden hour, night, bright, dim)
- Subject detection (people, architecture, nature)
- Era/style detection (vintage, 1970s, 1980s)
- Quality metrics (sharp, blurry, overexposed)
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)


class ImageTagger:
    """
    Modern AI tagger using CLIP for zero-shot scene classification
    and OpenCV for quality/color analysis.
    """

    def __init__(self, confidence_threshold: float = 0.3):
        """
        Initialize the tagger.

        Args:
            confidence_threshold: Minimum confidence (0-1) to assign a tag
        """
        self.confidence_threshold = confidence_threshold
        self.clip_model = None
        self.clip_processor = None
        self._initialize_clip()

    def _initialize_clip(self):
        """Load CLIP model for zero-shot classification."""
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch

            # Use lightweight CLIP model for speed
            model_name = "openai/clip-vit-base-patch32"
            logger.info(f"Loading CLIP model: {model_name}")

            self.clip_model = CLIPModel.from_pretrained(model_name)
            self.clip_processor = CLIPProcessor.from_pretrained(model_name)

            # Move to GPU if available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model = self.clip_model.to(device)
            self.clip_model.eval()

            logger.info(f"CLIP model loaded successfully (device: {device})")
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            logger.warning("AI tagging will be disabled - install: pip install transformers torch")
            self.clip_model = None

    def generate_tags(self, image_path: Path) -> List[Dict[str, any]]:
        """
        Generate automatic tags for an image.

        Args:
            image_path: Path to the image file

        Returns:
            List of dicts with {tag, confidence, category}
        """
        tags = []

        try:
            # Load image
            img = cv2.imread(str(image_path))
            if img is None:
                logger.error(f"Could not load image: {image_path}")
                return tags

            # 1. Scene classification (CLIP)
            if self.clip_model is not None:
                scene_tags = self._classify_scene(image_path)
                tags.extend(scene_tags)

            # 2. Color analysis
            color_tags = self._analyze_colors(img)
            tags.extend(color_tags)

            # 3. Quality metrics
            quality_tags = self._analyze_quality(img)
            tags.extend(quality_tags)

            # 4. Lighting analysis
            lighting_tags = self._analyze_lighting(img)
            tags.extend(lighting_tags)

            # 5. Composition analysis
            composition_tags = self._analyze_composition(img)
            tags.extend(composition_tags)

            # Filter by confidence threshold
            tags = [t for t in tags if t['confidence'] >= self.confidence_threshold]

            logger.info(f"Generated {len(tags)} tags for {image_path.name}")
            return tags

        except Exception as e:
            logger.error(f"Error generating tags: {e}", exc_info=True)
            return []

    def _classify_scene(self, image_path: Path) -> List[Dict]:
        """
        Classify scene using CLIP zero-shot classification.

        Returns:
            List of scene tags with confidence scores
        """
        if self.clip_model is None:
            return []

        try:
            import torch

            # Load image for CLIP
            pil_image = Image.open(image_path).convert('RGB')

            # Define scene categories for analog photo scans
            scene_labels = [
                # Primary scenes (MOST IMPORTANT)
                "a landscape with mountains", "a beach scene", "a forest",
                "a cityscape", "a street scene", "an urban area",
                "a portrait of a person", "a group of people", "a family photo",
                "an indoor scene", "an outdoor scene", "a nature scene",

                # Architecture
                "a building", "architecture", "a house", "a church",
                "a bridge", "a monument",

                # Activities
                "people at a party", "a wedding", "people dining",
                "children playing", "people on vacation", "sports",

                # Nature & landscapes
                "mountains", "a lake", "a river", "the ocean", "the sea",
                "trees", "flowers", "a garden", "a park",
                "a sunset", "a sunrise", "night scene",

                # Urban scenes
                "a car", "cars", "traffic", "a street", "downtown",
                "a shop", "a restaurant", "people walking",

                # Vintage/Era (for analog photos)
                "a vintage photo", "1950s", "1960s", "1970s", "1980s", "1990s",
                "an old photograph", "a historical photo"
            ]

            # Prepare inputs
            inputs = self.clip_processor(
                text=scene_labels,
                images=pil_image,
                return_tensors="pt",
                padding=True
            )

            # Move to same device as model
            device = next(self.clip_model.parameters()).device
            inputs = {k: v.to(device) for k, v in inputs.items()}

            # Get predictions
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)[0].cpu().numpy()

            # Extract high-confidence tags
            tags = []
            for label, confidence in zip(scene_labels, probs):
                if confidence >= self.confidence_threshold:
                    # Clean label: "a landscape photo" -> "landscape"
                    tag_name = label.replace("a ", "").replace(" photo", "").replace(" scene", "")

                    # Boost CLIP confidence scores (2x) to make scene tags more prominent
                    # CLIP uses softmax across many labels, so scores are naturally lower
                    boosted_confidence = min(float(confidence) * 2.0, 1.0)

                    tags.append({
                        'tag': tag_name,
                        'confidence': boosted_confidence,
                        'category': 'scene'
                    })

            # Sort by confidence
            tags.sort(key=lambda x: x['confidence'], reverse=True)

            # Take top 10 scene tags (increased to get more scene context)
            return tags[:10]

        except Exception as e:
            logger.error(f"CLIP classification failed: {e}")
            return []

    def _analyze_colors(self, img: np.ndarray) -> List[Dict]:
        """
        Analyze dominant colors and color characteristics.

        Returns:
            Color-related tags
        """
        tags = []

        try:
            # Convert to HSV for color analysis
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # Calculate color statistics
            h_mean = np.mean(hsv[:, :, 0])  # Hue
            s_mean = np.mean(hsv[:, :, 1])  # Saturation
            v_mean = np.mean(hsv[:, :, 2])  # Value (brightness)

            # Saturation-based tags
            if s_mean < 50:
                tags.append({'tag': 'desaturated', 'confidence': 0.8, 'category': 'color'})
                tags.append({'tag': 'faded colors', 'confidence': 0.7, 'category': 'style'})
            elif s_mean > 150:
                tags.append({'tag': 'vibrant', 'confidence': 0.8, 'category': 'color'})
                tags.append({'tag': 'saturated', 'confidence': 0.7, 'category': 'color'})

            # Hue-based dominant color (rough categorization)
            if s_mean > 30:  # Only if there's enough color
                if 0 <= h_mean < 15 or 165 <= h_mean < 180:
                    tags.append({'tag': 'red tones', 'confidence': 0.6, 'category': 'color'})
                elif 15 <= h_mean < 35:
                    tags.append({'tag': 'warm tones', 'confidence': 0.6, 'category': 'color'})
                elif 35 <= h_mean < 85:
                    tags.append({'tag': 'green tones', 'confidence': 0.6, 'category': 'color'})
                elif 85 <= h_mean < 135:
                    tags.append({'tag': 'blue tones', 'confidence': 0.6, 'category': 'color'})
                    tags.append({'tag': 'cool tones', 'confidence': 0.5, 'category': 'color'})

            # Film stock characteristics (based on color cast)
            if s_mean < 60 and v_mean < 100:
                tags.append({'tag': 'aged film', 'confidence': 0.5, 'category': 'style'})

        except Exception as e:
            logger.error(f"Color analysis failed: {e}")

        return tags

    def _analyze_quality(self, img: np.ndarray) -> List[Dict]:
        """
        Analyze image quality (sharpness, noise, exposure).

        Returns:
            Quality-related tags
        """
        tags = []

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Sharpness (Laplacian variance)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = laplacian.var()

            if sharpness > 500:
                tags.append({'tag': 'sharp', 'confidence': 0.8, 'category': 'quality'})
            elif sharpness < 100:
                tags.append({'tag': 'blurry', 'confidence': 0.7, 'category': 'quality'})
                tags.append({'tag': 'soft focus', 'confidence': 0.5, 'category': 'style'})

            # Exposure analysis
            brightness = np.mean(gray)
            if brightness > 200:
                tags.append({'tag': 'bright', 'confidence': 0.7, 'category': 'lighting'})
                if brightness > 230:
                    tags.append({'tag': 'overexposed', 'confidence': 0.6, 'category': 'quality'})
            elif brightness < 60:
                tags.append({'tag': 'dark', 'confidence': 0.7, 'category': 'lighting'})
                if brightness < 30:
                    tags.append({'tag': 'underexposed', 'confidence': 0.6, 'category': 'quality'})

            # Grain/noise estimation (for film scans)
            noise_std = np.std(gray)
            if noise_std > 40:
                tags.append({'tag': 'grainy', 'confidence': 0.6, 'category': 'style'})
                tags.append({'tag': 'high grain', 'confidence': 0.5, 'category': 'film'})

        except Exception as e:
            logger.error(f"Quality analysis failed: {e}")

        return tags

    def _analyze_lighting(self, img: np.ndarray) -> List[Dict]:
        """
        Analyze lighting conditions and time of day.

        Returns:
            Lighting-related tags
        """
        tags = []

        try:
            # Convert to LAB color space for better lighting analysis
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l_channel = lab[:, :, 0]
            a_channel = lab[:, :, 1]
            b_channel = lab[:, :, 2]

            # Warm vs cool lighting (from b channel)
            b_mean = np.mean(b_channel)
            if b_mean > 135:
                tags.append({'tag': 'warm light', 'confidence': 0.7, 'category': 'lighting'})
                tags.append({'tag': 'golden hour', 'confidence': 0.5, 'category': 'time'})
            elif b_mean < 120:
                tags.append({'tag': 'cool light', 'confidence': 0.7, 'category': 'lighting'})
                tags.append({'tag': 'overcast', 'confidence': 0.4, 'category': 'weather'})

            # Contrast (indicates lighting quality)
            contrast = np.std(l_channel)
            if contrast > 40:
                tags.append({'tag': 'high contrast', 'confidence': 0.6, 'category': 'lighting'})
                tags.append({'tag': 'dramatic lighting', 'confidence': 0.5, 'category': 'style'})
            elif contrast < 20:
                tags.append({'tag': 'flat lighting', 'confidence': 0.6, 'category': 'lighting'})
                tags.append({'tag': 'soft light', 'confidence': 0.5, 'category': 'lighting'})

        except Exception as e:
            logger.error(f"Lighting analysis failed: {e}")

        return tags

    def _analyze_composition(self, img: np.ndarray) -> List[Dict]:
        """
        Analyze image composition and framing.

        Returns:
            Composition-related tags
        """
        tags = []

        try:
            height, width = img.shape[:2]
            aspect_ratio = width / height

            # Orientation
            if aspect_ratio > 1.3:
                tags.append({'tag': 'landscape orientation', 'confidence': 0.9, 'category': 'composition'})
            elif aspect_ratio < 0.8:
                tags.append({'tag': 'portrait orientation', 'confidence': 0.9, 'category': 'composition'})
            else:
                tags.append({'tag': 'square format', 'confidence': 0.9, 'category': 'composition'})

            # Edge detection for composition analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)

            # Analyze edge distribution (simple center-weight detection)
            center_region = edges[height//3:2*height//3, width//3:2*width//3]
            center_edges = np.sum(center_region) / (center_region.size * 255)

            if center_edges > 0.1:
                tags.append({'tag': 'centered subject', 'confidence': 0.5, 'category': 'composition'})

        except Exception as e:
            logger.error(f"Composition analysis failed: {e}")

        return tags


def extract_tags_for_display(tags: List[Dict]) -> Dict[str, List[str]]:
    """
    Group tags by category for display.

    Args:
        tags: List of tag dictionaries

    Returns:
        Dict mapping category to list of tag names
    """
    grouped = {}
    for tag_info in tags:
        category = tag_info.get('category', 'general')
        tag_name = tag_info['tag']

        if category not in grouped:
            grouped[category] = []
        grouped[category].append(tag_name)

    return grouped
