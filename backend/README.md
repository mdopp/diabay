# DiaBay Backend

Modern FastAPI-based backend for analog slide digitization and enhancement.

## Features

✅ **Image Enhancement Pipeline**
- Adaptive CLAHE (contrast-limited adaptive histogram equalization)
- Improved 16-bit → 8-bit conversion with percentile stretching
- Face-aware gentle enhancement
- Auto-quality mode (tries multiple presets, selects best)
- Multi-format output (JPEG, JPEG XL, PNG, TIFF 16-bit)

✅ **Real-Time Monitoring**
- WebSocket for live processing updates
- Pipeline stage visibility (input → analysed → enhanced)
- ETA calculation
- Performance metrics (pics/hour, avg time)

✅ **Duplicate Detection**
- Pre-enhancement detection (saves processing time)
- Post-enhancement comparison
- Perceptual hashing with configurable threshold

✅ **File Watcher**
- Automatic processing of new scans
- Debounce logic (waits for scanner to finish)
- Resume processing after restart

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Test with Sample Files

```bash
python test_pipeline.py
```

This will:
- Copy sample TIFF files from `tests/samples/` to `input/`
- Process them through the pipeline
- Generate enhanced JPEGs in `output/`
- Show real-time progress

### 4. Run Server

```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

### REST API

- `GET /` - Health check
- `GET /api/stats` - Pipeline statistics
- `GET /api/images` - List processed images
- `GET /api/images/{id}` - Get image details
- `POST /api/images/{id}/reprocess` - Reprocess with different preset
- `GET /api/duplicates` - Find duplicates

### WebSocket

- `WS /ws/status` - Real-time processing updates

Connect with JavaScript:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/status');

ws.onmessage = (event) => {
    const stats = JSON.parse(event.data);
    console.log('Pipeline stats:', stats);
};

// Send heartbeat every 5 seconds
setInterval(() => ws.send('ping'), 5000);
```

## Project Structure

```
backend/
├── main.py                 # FastAPI application
├── config.py               # Configuration management
├── requirements.txt        # Dependencies
│
├── api/                    # API routes (TODO)
├── core/                   # Core processing
│   ├── processor.py        # Image enhancement
│   ├── pipeline.py         # Pipeline orchestrator
│   ├── watcher.py          # File system monitoring
│   └── duplicates.py       # Duplicate detection
│
└── db/                     # Database
    ├── models.py           # SQLAlchemy models
    └── database.py         # Connection & sessions
```

## Configuration

Key settings in `.env`:

```bash
# Directories
INPUT_DIR=./input            # Scanner drops files here
ANALYSED_DIR=./analysed      # Renamed files before enhancement
OUTPUT_DIR=./output          # Enhanced JPEGs

# Enhancement
JPEG_QUALITY=95              # Output quality (0-100)
CLAHE_CLIP_LIMIT=1.5         # Contrast enhancement
HISTOGRAM_CLIP=0.5           # Haze removal (%)
ADAPTIVE_CLAHE_GRID=true     # Adapt to resolution
ENABLE_FACE_DETECTION=true   # Gentle enhancement for portraits

# Output Formats
ENABLE_JPEG_XL=false         # Modern format (smaller, better quality)
ENABLE_PNG_ARCHIVE=false     # Lossless archive
ENABLE_TIFF_ARCHIVE=false    # 16-bit TIFF archive

# Duplicates
DUPLICATE_THRESHOLD=0.95     # Similarity (0.95 = very similar)
AUTO_SKIP_DUPLICATES=true    # Skip exact duplicates automatically
```

## Enhancement Presets

### Gentle (0.3 hist, 1.0 CLAHE)
- Minimal enhancement
- Best for well-exposed originals
- Preserves maximum detail

### Balanced (0.5 hist, 1.5 CLAHE) - Default
- Standard enhancement
- Good for most analog slides
- Removes haze, boosts contrast

### Aggressive (0.7 hist, 2.0 CLAHE)
- Maximum enhancement
- For very faded/dark slides
- May introduce artifacts

### Auto-Quality Mode
Automatically tries all presets and selects best based on:
- Sharpness (Laplacian variance) - 40%
- Contrast (std dev) - 30%
- Dynamic range - 30%

## Database Schema

SQLite database stores:
- **images** - Main image records with processing state
- **image_tags** - AI and manual tags
- **image_metadata** - Rotation, film type, OCR text
- **image_embeddings** - Perceptual hashes for duplicate detection
- **processing_sessions** - Statistics and resume capability
- **duplicate_groups** - Detected duplicate clusters

## Development

### Run Tests
```bash
python test_pipeline.py
```

### Debug Mode
```bash
# Enable hot reload
RELOAD=true python main.py
```

### Check Logs
Logs are written to stdout with structured format:
```
2026-02-10 23:00:00 - diabay.pipeline - INFO - Processing IMG_001.tif
2026-02-10 23:00:15 - diabay.pipeline - INFO - Enhanced in 15.2s
```

## TODO

- [ ] Scene classification (Places365 ONNX model)
- [ ] OCR text extraction (Tesseract)
- [ ] MTCNN face detection (replace Haar cascade)
- [ ] Timeline view clustering
- [ ] Narrative album generation
- [ ] Scratch removal (inpainting)
- [ ] Color grading (3D LUTs)

## License

Part of DiaBay project - Analog slide digitization system
