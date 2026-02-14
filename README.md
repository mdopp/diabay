# DiaBay

**Professional Slide & Film Digitization System** by [korgraph.io](https://korgraph.io)

Modern FastAPI + React application for processing, viewing, and organizing scanned analog photographs.

## Features

### 🎨 Image Enhancement
- **Adaptive CLAHE** - Contrast-limited adaptive histogram equalization
- **Face-aware processing** - Gentler enhancement for portraits
- **Auto-quality mode** - AI selects best enhancement preset
- **Multi-format output** - JPEG, JPEG XL, PNG, TIFF 16-bit

### 🤖 AI-Powered Tagging
- **CLIP scene classification** - Modern zero-shot scene recognition
- **Automatic tagging** - Lighting, composition, subject, era detection
- **Quality metrics** - Sharpness, exposure, color analysis

### 🔍 Smart Organization
- **Duplicate detection** - Pre and post-enhancement deduplication
- **Perceptual hashing** - Find similar images even if rescanned
- **Database-backed** - SQLite stores all metadata, tags, processing history
- **Rotation controls** - Manual rotation from UI

### 📊 Real-Time Monitoring
- **WebSocket updates** - Live processing status
- **Pipeline visibility** - Track stages (input → analysed → enhanced)
- **Performance metrics** - Pics/hour, avg time, ETA calculation
- **Processing statistics** - Session history, error tracking

### 📱 Modern Web UI
- **React + TypeScript** - Responsive, type-safe frontend
- **Radix UI + Tailwind** - Modern component library
- **Mobile-responsive** - Touch gestures, swipe navigation
- **Network access** - Accessible from any device on your LAN

### ⚙️ Production Ready
- **File watcher** - Auto-process new scans with debounce logic
- **Resume processing** - Continue after restart
- **Windows + Linux** - Cross-platform support
- **Database migrations** - SQLAlchemy schema management

## Quick Start

### Linux/WSL (Development)

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (CPU-only PyTorch recommended)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Run backend (serves both API and frontend)
python main.py
```

**Open browser:** http://localhost:8000

### Windows (Production)

See **[WINDOWS_SETUP.md](WINDOWS_SETUP.md)** for detailed Windows installation guide.

**Quick version:**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python main.py
```

**Open browser:** http://localhost:8000

**Access from other devices on your network:**
- The server binds to `0.0.0.0`, making it accessible on all network interfaces
- Find your server's IP: `ip addr show` (Linux) or `ipconfig` (Windows)
- Access from phone/tablet: `http://192.168.x.x:8000` (replace with actual IP)

## Usage

### Web Interface

Once DiaBay is running, open http://localhost:8000 in your browser.

**Main Views:**
- **Gallery** - Grid view of all processed images with thumbnails
- **Image Detail** - Side-by-side comparison (original vs enhanced)
- **Statistics** - Real-time processing metrics and session history
- **Duplicates** - Find and manage similar images

**Key Actions:**
- **Drop TIFFs** in input folder → auto-processed
- **Click image** → View detail with original/enhanced comparison
- **Rotate** → Click rotate button in detail view
- **Scan duplicates** → Find similar images pre/post enhancement
- **View tags** → AI-generated scene, lighting, composition tags
- **Monitor progress** → Live WebSocket updates, pics/hour stats

### File Processing Workflow

1. **Scanner** drops TIFF files into `input/` directory
2. **DiaBay automatically**:
   - Renames based on EXIF date → `image_YYMMDD_HHMMSS.tif`
   - Moves to `analysed/` folder
   - Enhances image (CLAHE, histogram, face-aware)
   - Generates AI tags (CLIP scene classification)
   - Detects duplicates (pre-enhancement)
   - Saves enhanced JPEG to `output/` folder
3. **View in browser** → Real-time updates via WebSocket

### Duplicate Detection

DiaBay detects duplicates **before** enhancement to save processing time:
- Uses perceptual hashing (imagehash library)
- Finds similar images even if rescanned at different resolutions
- Configurable similarity threshold (default: 0.95)
- Review duplicate groups in UI
- Keep best version, delete duplicates

### File Watcher

Automatic file monitoring is enabled by default:
- Watches `input/` directory for new TIFF files
- Debounce logic waits for scanner to finish writing
- Resume processing after restart (database-tracked)
- No configuration needed

## Requirements

- Python 3.10+
- PyTorch (for CLIP AI tagging)
- OpenCV (image processing)
- Pillow (EXIF reading, no exiftool needed!)
- FastAPI + Uvicorn (web framework)
- SQLAlchemy (database ORM)
- Node.js (for frontend builds, optional for production)

## Architecture

**Backend** (`backend/`):
- FastAPI (async Python web framework)
- SQLite database (SQLAlchemy ORM)
- CLIP AI for scene tagging
- OpenCV for image processing
- Pillow for EXIF metadata

**Frontend** (`frontend/`):
- React 18 + TypeScript
- Vite (build tool)
- Radix UI + Tailwind CSS
- WebSocket for real-time updates

**Deployment:**
- Development: Vite dev server (port 5000) + FastAPI (port 8000)
- Production: FastAPI serves pre-built React static files (port 8000)

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for production deployment details.

## Documentation

- **[WINDOWS_SETUP.md](WINDOWS_SETUP.md)** - Windows installation guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **[backend/README.md](backend/README.md)** - Backend architecture and API

## License

MIT © korgraph.io
