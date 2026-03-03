```
     _ _       ____
    | (_)     |  _ \
  __| |_  __ _| |_) | __ _ _   _
 / _` | |/ _` |  _ < / _` | | | |
| (_| | | (_| | |_) | (_| | |_| |
 \__,_|_|\__,_|____/ \__,_|\__, |
                             __/ |
                            |___/
```

**Scanned slide & film digitization toolkit.**
Turn raw TIFF scans into organized, enhanced, correctly oriented JPEGs — from the terminal.

---

## What It Does

diaBay is a CLI pipeline that takes a folder of scanned slides or film negatives (TIFFs) and produces print-ready output. It handles the tedious parts of bulk scan processing automatically:

1. **Rename** files from scanner gibberish (`IMG_00042.tif`) to EXIF timestamps (`20240815_143022.jpg`)
2. **Enhance** contrast, color, and detail — face-aware, so portraits don't get blown out
3. **Orient** images using EXIF data and face detection
4. **Preview** every processed image live in the terminal as it works
5. **Review** results in a browser-based gallery with one-click rotation correction
6. **Export** high-resolution JPEGs and lossless JPEG XL from the originals

## Features

### Enhancement Pipeline

- **16-bit to 8-bit conversion** with per-channel percentile stretching — no clipping, no haze
- **Adaptive CLAHE** in LAB color space — boosts contrast without shifting colors
- **Face-aware processing** — detects faces via Haar cascades and applies gentler enhancement to skin tones
- **Auto preset selection** — tries gentle, balanced, and aggressive profiles, picks the one with the best quality score
- **OpenVINO super-resolution** — optional AI upscaling via Intel's single-image-super-resolution model, with automatic device selection (NPU > GPU > CPU)

### Orientation Detection

- Reads **EXIF orientation tags** from scanner metadata
- **Face-based rotation** — rotates the image 4 ways, picks the one where the most faces are detected (requires a clear winner to avoid false corrections)

### Review Server

A built-in Flask web app for inspecting results:

- **Gallery view** with thumbnails on a dark-themed grid
- **Per-card rotation buttons** — rotate left, flip, rotate right without opening each image
- **Modal detail view** — click any thumbnail for a full-size preview with metadata
- **Batch apply** — queue up rotation corrections and apply them all at once (parallel processing)
- Runs automatically during processing and can be started standalone

### Export

Produces archival-quality output from the original TIFFs:

- `highres/` — 8-bit JPEG, quality 98, 4:4:4 chroma subsampling
- `highres_jxl/` — 16-bit JPEG XL, lossless (requires `imagecodecs`)
- **Rotation recovery** — compares enhanced JPEGs to originals to determine the correct rotation, even if the manifest was lost

### Performance

- **Resume support** — manifest tracks what's been processed; re-run safely without redoing work
- **Smart I/O** — detects slow mounts (WSL `/mnt/`, NFS `/media/`) and processes locally first, then copies in the background
- **Live terminal preview** — half-block Unicode rendering of each image as it's processed
- **Rich progress** — per-image ETA, throughput stats, and a collapsible review server log panel

## Installation

### Prerequisites

- Python 3.10+
- OpenCV with Haar cascades (included in `opencv-python`)
- Optional: [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for OSD-based orientation
- Optional: [OpenVINO](https://docs.openvino.ai/) for AI super-resolution
- Optional: `imagecodecs` for JPEG XL export

### Setup

```bash
git clone https://github.com/mdopp/diabay.git
cd diabay
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Process scans

```bash
# Process all TIFFs in a folder
python diabay.py /path/to/scans

# Include subdirectories (prefixes filenames with folder name)
python diabay.py /path/to/scans -r

# Output to a specific directory
python diabay.py /path/to/scans -o /mnt/e/output

# Use a specific enhancement preset
python diabay.py /path/to/scans --preset aggressive

# Skip specific steps
python diabay.py /path/to/scans --skip-enhance --skip-orient

# CLAHE only, no AI super-resolution
python diabay.py /path/to/scans --no-ai
```

### Review results

```bash
# Open the review gallery in your browser
python diabay.py --review /path/to/output
```

The review server starts at `http://localhost:5555`. During processing, it runs automatically in the background so you can review images as they come in.

### Export high-res

```bash
# Export from original TIFFs using the processed manifest
python diabay.py --export /path/to/output

# Force re-export everything
python diabay.py --export --force /path/to/output
```

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
