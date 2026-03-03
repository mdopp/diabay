"""
EXIF timestamp extraction and file renaming for scanned slides.
Renames TIFFs to yyyyMMdd_hh24mmss format, copies to output/originals/.
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


def extract_exif_date(file_path: Path) -> Optional[datetime]:
    """Extract date from EXIF metadata (DateTimeOriginal, DateTime, DateTimeDigitized)."""
    try:
        with Image.open(file_path) as img:
            exif = img.getexif()
            if exif:
                # 36867=DateTimeOriginal, 306=DateTime, 36868=DateTimeDigitized
                for tag_id in [36867, 306, 36868]:
                    value = exif.get(tag_id)
                    if value:
                        try:
                            return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        logger.debug(f"Could not extract EXIF from {file_path.name}: {e}")
    return None


def get_timestamp_name(file_path: Path) -> str:
    """Get yyyyMMdd_hh24mmss filename from EXIF or file mtime."""
    dt = extract_exif_date(file_path)
    if dt is None:
        dt = datetime.fromtimestamp(file_path.stat().st_mtime)
    return dt.strftime("%Y%m%d_%H%M%S")


def resolve_collision(dest_dir: Path, base_name: str, suffix: str) -> Path:
    """Append _01, _02, etc. if filename already exists."""
    candidate = dest_dir / f"{base_name}{suffix}"
    if not candidate.exists():
        return candidate
    for i in range(1, 100):
        candidate = dest_dir / f"{base_name}_{i:02d}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Too many collisions for {base_name}")


def rename_and_copy(src: Path, originals_dir: Path, prefix: str = "") -> Path:
    """
    Copy a TIFF to originals_dir with a timestamp-based name.
    If prefix is given (e.g. subdirectory name), it is prepended: prefix_yyyyMMdd_hh24mmss.
    Returns the new path.
    """
    originals_dir.mkdir(parents=True, exist_ok=True)
    base_name = get_timestamp_name(src)
    if prefix:
        base_name = f"{prefix}_{base_name}"
    dest = resolve_collision(originals_dir, base_name, src.suffix)
    # Manual byte copy — shutil.copy uses sendfile which fails on NTFS/drvfs
    st = src.stat()
    with open(src, 'rb') as fsrc, open(dest, 'wb') as fdst:
        while chunk := fsrc.read(1024 * 1024):
            fdst.write(chunk)
    try:
        os.utime(dest, (st.st_atime, st.st_mtime))
    except OSError:
        pass  # NTFS/drvfs may not support utime
    logger.info(f"Renamed: {src.name} -> {dest.name}")
    return dest
