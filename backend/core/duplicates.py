"""
Duplicate detection using perceptual hashing
Finds similar images in input (pre-enhancement) and output (post-enhancement)
"""
import imagehash
from PIL import Image
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detect duplicate and similar images using perceptual hashing
    """

    def __init__(self, threshold: float = 0.95):
        """
        Initialize detector

        Args:
            threshold: Similarity threshold (0.0-1.0)
                      0.95 = very similar, 0.85 = similar
        """
        self.threshold = threshold
        self.hash_cache: Dict[Path, str] = {}

    def compute_hash(self, image_path: Path) -> str:
        """
        Compute perceptual hash for an image

        Args:
            image_path: Path to image file

        Returns:
            Hex string of perceptual hash
        """
        try:
            img = Image.open(image_path)
            # Use 16-bit phash for better accuracy
            phash = imagehash.phash(img, hash_size=16)
            return str(phash)
        except Exception as e:
            logger.error(f"Error computing hash for {image_path}: {e}")
            return ""

    def calculate_similarity(self, hash1: str, hash2: str) -> float:
        """
        Calculate similarity between two hashes

        Args:
            hash1, hash2: Hex string hashes

        Returns:
            Similarity score (0.0-1.0), 1.0 = identical
        """
        if not hash1 or not hash2:
            return 0.0

        try:
            # Convert hex strings to imagehash objects
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)

            # Calculate Hamming distance
            distance = h1 - h2

            # Normalize to similarity (0.0-1.0)
            max_distance = len(hash1) * 4  # Each hex char = 4 bits
            similarity = 1.0 - (distance / max_distance)

            return similarity

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def find_duplicates(self, directory: Path) -> List[Dict]:
        """
        Find duplicate groups in a directory

        Args:
            directory: Directory to scan for duplicates

        Returns:
            List of duplicate groups, each containing similar images
        """
        logger.info(f"Scanning for duplicates in: {directory}")

        # Get all image files
        image_files = list(directory.rglob("*.jpg")) + \
                     list(directory.rglob("*.tif")) + \
                     list(directory.rglob("*.tiff"))

        if len(image_files) < 2:
            logger.info("Not enough images to check for duplicates")
            return []

        # Compute hashes
        logger.info(f"Computing hashes for {len(image_files)} images...")
        hashes = {}
        for image_path in image_files:
            phash = self.compute_hash(image_path)
            if phash:
                hashes[image_path] = phash

        # Find similar images
        logger.info("Finding similar images...")
        duplicate_groups = []
        processed = set()

        for img1, hash1 in hashes.items():
            if img1 in processed:
                continue

            # Find all images similar to img1
            group = [img1]
            similarities = []

            for img2, hash2 in hashes.items():
                if img2 == img1 or img2 in processed:
                    continue

                similarity = self.calculate_similarity(hash1, hash2)

                if similarity >= self.threshold:
                    group.append(img2)
                    similarities.append(similarity)
                    processed.add(img2)

            # If group has duplicates, add it
            if len(group) > 1:
                processed.add(img1)

                # Calculate average similarity
                avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0

                duplicate_groups.append({
                    'original': str(img1),
                    'duplicates': [str(img) for img in group[1:]],
                    'avg_similarity': round(avg_similarity, 3),
                    'count': len(group)
                })

        logger.info(f"Found {len(duplicate_groups)} duplicate groups")

        return duplicate_groups

    def scan_input_duplicates(self, input_dir: Path, analysed_dir: Path) -> Dict:
        """
        Scan input directory for duplicates before enhancement

        This saves processing time by skipping exact duplicates

        Args:
            input_dir: Directory with new scans
            analysed_dir: Directory with already processed files

        Returns:
            Dict with duplicate groups and skip recommendations
        """
        logger.info("Scanning input for duplicates (pre-enhancement)...")

        # Get files from both directories
        input_files = list(input_dir.rglob("*.tif*"))
        analysed_files = list(analysed_dir.rglob("*.tif*"))

        all_files = input_files + analysed_files

        if len(all_files) < 2:
            return {'groups': [], 'skip_count': 0}

        # Compute hashes
        hashes = {f: self.compute_hash(f) for f in all_files if f.exists()}

        # Find exact matches and near-matches
        skip_files = []
        alert_files = []
        groups = []

        for input_file in input_files:
            if input_file not in hashes:
                continue

            input_hash = hashes[input_file]

            for other_file in analysed_files:
                if other_file not in hashes:
                    continue

                similarity = self.calculate_similarity(input_hash, hashes[other_file])

                if similarity >= 0.99:
                    # Exact match - recommend skip
                    skip_files.append(input_file)
                    groups.append({
                        'type': 'exact',
                        'input_file': str(input_file),
                        'match': str(other_file),
                        'similarity': round(similarity, 3),
                        'action': 'skip'
                    })
                    break

                elif similarity >= self.threshold:
                    # Near match - alert user
                    alert_files.append(input_file)
                    groups.append({
                        'type': 'near',
                        'input_file': str(input_file),
                        'match': str(other_file),
                        'similarity': round(similarity, 3),
                        'action': 'alert'
                    })
                    break

        return {
            'groups': groups,
            'skip_count': len(skip_files),
            'alert_count': len(alert_files),
            'total_input': len(input_files)
        }
