```
     _ _       ____
    | (_)     |  _ \
  __| |_  __ _| |_) | __ _ _   _
 / _` | |/ _` |  _ < / _` | | | |
| (_| | | (_| | |_) | (_| | |_| |
 \__,_|_|\__,_|____/ \__,_|\__, |
                            __/ |
         by Korgraph       |___/
```

**Scanned slide & film digitization toolkit.**
Turn raw TIFF scans into organized, enhanced, correctly oriented JPEGs — from the terminal.

---

## Quick Start

```bash
git clone https://github.com/mdopp/diabay.git
cd diabay
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Process a folder of scanned TIFFs
python diabay.py /path/to/scans
```

That's it. diaBay will enhance, rename, orient, and thumbnail every TIFF it finds. A review gallery opens automatically at `http://localhost:5555`.

## What It Does

diaBay takes a folder of scanned slides or film negatives (TIFFs) and produces print-ready output:

- **Rename** — scanner filenames (`IMG_00042.tif`) become EXIF timestamps (`20240815_143022.jpg`)
- **Enhance** — adaptive contrast and color correction, face-aware so portraits don't get blown out
- **Orient** — automatic rotation via EXIF data and face detection
- **Review** — browser-based gallery with one-click rotation correction
- **Export** — high-res JPEGs and lossless JPEG XL from the originals

## Usage Examples

```bash
# Include subdirectories (prefixes filenames with folder name)
python diabay.py /path/to/scans -r

# Output to a specific directory
python diabay.py /path/to/scans -o /mnt/e/output

# Use a specific enhancement preset
python diabay.py /path/to/scans --preset aggressive

# CLAHE only, no AI super-resolution
python diabay.py /path/to/scans --no-ai

# Skip specific steps
python diabay.py /path/to/scans --skip-enhance --skip-orient

# Open the review gallery standalone
python diabay.py --review /path/to/output

# Export high-res from original TIFFs
python diabay.py --export /path/to/output
```

## How It Works

**Enhancement** — 16-bit to 8-bit conversion with percentile stretching, adaptive CLAHE in LAB color space (preserves colors), face-aware processing with gentler correction on skin tones. Auto mode tries all presets and picks the best. Optional OpenVINO super-resolution on NPU/GPU/CPU.

**Orientation** — Reads EXIF tags from scanner metadata. Face-based detection rotates the image 4 ways and picks the rotation where the most faces are found.

**Review** — Built-in Flask gallery with thumbnail grid, per-card rotation buttons, full-size modal previews, and batch apply. Runs automatically during processing.

**Export** — Archival output from original TIFFs: high-res JPEG (quality 98, 4:4:4 chroma) and lossless 16-bit JPEG XL. Recovers correct rotation by comparing enhanced JPEGs to originals.

**Performance** — Resume support via manifest, smart I/O for slow mounts (WSL `/mnt/`, NFS), live terminal image preview, and per-image ETA.

## Optional Dependencies

The core pipeline only needs what's in `requirements.txt`. For extra capabilities:

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — OSD-based orientation detection
- [OpenVINO](https://docs.openvino.ai/) — AI super-resolution (NPU > GPU > CPU, auto-selected)
- `pip install imagecodecs` — JPEG XL lossless export

## CLI Reference

```
usage: diabay.py [-h] [-o OUTPUT] [-r] [--preset {auto,gentle,balanced,aggressive}]
                 [--quality QUALITY] [--review] [--export] [--force]
                 [--skip-rename] [--skip-orient] [--skip-enhance] [--no-ai] [-v]
                 input_dir

positional arguments:
  input_dir             Folder with scanned TIFFs (or output dir with --review/--export)

options:
  -o, --output          Output folder (default: ./output)
  -r, --recursive       Include subdirectories (prefix dir name to filenames)
  --preset              Enhancement preset: auto, gentle, balanced, aggressive (default: auto)
  --quality             JPEG quality 1-100 (default: 95)
  --review              Start review server instead of processing
  --export              Export high-res JPEGs from original TIFFs
  --force               Re-export all images (ignore resume cache)
  --skip-rename         Keep original filenames
  --skip-orient         Skip orientation detection
  --skip-enhance        Skip enhancement step
  --no-ai               CLAHE only, skip OpenVINO super-resolution
  -v, --verbose         Verbose logging
```

## Output Structure

```
output/
├── enhanced/           # Processed JPEGs (default quality 95)
├── thumbs/             # 320px thumbnails for the review gallery
├── highres/            # Full-res JPEGs from --export (quality 98)
├── highres_jxl/        # Lossless JPEG XL from --export
└── manifest.json       # Processing metadata and rotation state
```

The `manifest.json` tracks every processed image:

```json
{
  "images": {
    "20240815_143022": {
      "original": "IMG_00042.tif",
      "source_dir": "/path/to/scans",
      "prefix": "",
      "rotation": 0,
      "preset": "balanced",
      "quality_score": 72.3,
      "faces_detected": 2,
      "accelerator": "GPU"
    }
  }
}
```

## Keyboard Shortcuts

During processing:

| Key | Action |
|---|---|
| `Ctrl+O` | Toggle full review server log |
| `Ctrl+C` | Stop processing / exit |

In the review UI:

| Key | Action |
|---|---|
| `Escape` | Close modal |

## Project Structure

```
diabay.py          Main CLI — orchestrates the full pipeline
enhance.py         CLAHE + OpenVINO super-resolution pipeline
orient.py          EXIF / face-based orientation detection
rename.py          EXIF timestamp extraction and renaming
review.py          Flask review server
templates/
  review.html      Review gallery SPA (vanilla JS)
```

## License

MIT
