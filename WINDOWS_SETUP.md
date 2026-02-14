# DiaBay - Windows Setup Guide

Quick guide to get DiaBay running on Windows for production use.

## Prerequisites

Install these on Windows using the package manager:

```powershell
# Python 3.10 or later
winget install Python.Python.3.12

# Git
winget install Git.Git

# (Optional) Node.js - only needed if you want to build the frontend yourself
# The repo already has pre-built files, so this is optional
winget install OpenJS.NodeJS
```

## Quick Start (5 minutes)

### 1. Clone the Repository

```powershell
git clone https://github.com/yourusername/photoenhancer.git
cd photoenhancer\diabay\backend
```

### 2. Create Python Virtual Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate
```

### 3. Install Python Dependencies

```powershell
# Install PyTorch (CPU-only, avoids 2GB CUDA download)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
pip install -r requirements.txt
```

This will take 2-3 minutes. The main packages installed:
- `fastapi` - Web framework
- `opencv-python` - Image processing
- `Pillow` - EXIF reading
- `transformers` - AI scene tagging (CLIP)
- `imagehash` - Duplicate detection
- `watchdog` - File monitoring

### 4. Run DiaBay

```powershell
# From diabay\backend directory
python main.py
```

**That's it!** Open your browser to **http://localhost:8000**

## Configuration (Optional)

Create a `.env` file in `diabay/backend/` to customize directories:

```env
# Input directory (where scanner drops files)
INPUT_DIR=C:\Users\YourName\ScanInput

# Output directory (where enhanced JPEGs are saved)
OUTPUT_DIR=C:\Users\YourName\Pictures\Enhanced

# Analyzed directory (renamed TIFFs)
ANALYSED_DIR=C:\Users\YourName\Pictures\Analysed
```

If you don't create a `.env` file, DiaBay will use default directories relative to the backend folder.

## File Processing Workflow

1. **Drop TIFFs** into the input directory (or default: `diabay/backend/input/`)
2. **DiaBay automatically**:
   - Renames files based on EXIF date → `image_YYMMDD_HHMMSS.tif`
   - Moves to `analysed/` folder
   - Enhances the image (histogram leveling, contrast, face-aware processing)
   - Generates AI tags (scene, lighting, composition)
   - Saves enhanced JPEG to `output/` folder
   - Creates thumbnails for gallery view
3. **View in browser** at http://localhost:8000 (real-time updates via WebSocket)

## Features

- ✅ **Real-time monitoring** - WebSocket updates while processing
- ✅ **AI scene tagging** - CLIP-based automatic tagging
- ✅ **Duplicate detection** - Find similar images before/after enhancement
- ✅ **Rotation controls** - Rotate images from the UI
- ✅ **Database-backed** - SQLite stores all metadata, tags, processing history
- ✅ **Multi-format output** - JPEG (default), can enable JPEG XL, PNG, TIFF
- ✅ **Processing statistics** - Track pics/hour, session history, performance
- ✅ **Auto-quality mode** - AI selects best enhancement preset
- ✅ **Mobile-responsive** - Access from tablets/phones on your network

## Network Access (Optional)

To access DiaBay from other devices on your network:

1. Find your Windows PC's IP address:
   ```powershell
   ipconfig
   # Look for "IPv4 Address" under your active network adapter
   # Example: 192.168.1.100
   ```

2. DiaBay already binds to `0.0.0.0:8000`, so it's accessible on your LAN

3. From your phone/tablet, open: **http://192.168.1.100:8000** (replace with your IP)

## Troubleshooting

### "Python not found"
Make sure Python is in your PATH. Restart your terminal after installing Python.

### "ModuleNotFoundError: No module named 'PIL'"
```powershell
pip install Pillow
```

### "Frontend not found" error
The pre-built frontend should be in `diabay/frontend/dist/`. If missing:
```powershell
cd ..\frontend
npm install
npm run build
cd ..\backend
```

### "Slow processing"
Make sure you installed the CPU-only PyTorch. Check with:
```powershell
pip show torch
# Should say: Installed from: ...whl/cpu/...
```

If it says `cu118` or `cu121` (CUDA versions), reinstall:
```powershell
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### "File watcher not detecting new files"
- Check folder permissions (ensure DiaBay can read/write)
- Try using absolute paths in `.env` file
- Restart DiaBay after adding files

### "CLIP model download stuck"
First-time startup downloads ~350MB CLIP model. This is normal. If it fails:
- Check internet connection
- Or temporarily disable AI tagging by editing `backend/core/pipeline.py`:
  ```python
  self.tagger = None  # Disable AI tagging
  ```

## Updating DiaBay

When there are updates:

```powershell
# Pull latest code
git pull

# Rebuild frontend (if there were frontend changes)
cd diabay\frontend
npm run build

# Restart backend
cd ..\backend
python main.py
```

## Running as Windows Service (Advanced)

To run DiaBay as a background service that starts automatically:

1. Install `nssm` (Non-Sucking Service Manager):
   ```powershell
   winget install nssm
   ```

2. Create service:
   ```powershell
   nssm install DiaBay "C:\Users\YourName\photoenhancer\diabay\backend\.venv\Scripts\python.exe" "main.py"
   nssm set DiaBay AppDirectory "C:\Users\YourName\photoenhancer\diabay\backend"
   nssm set DiaBay DisplayName "DiaBay Photo Enhancement"
   nssm set DiaBay Description "Automatic slide digitization and enhancement service"
   ```

3. Start service:
   ```powershell
   nssm start DiaBay
   ```

4. Service will now start automatically on boot. Access at http://localhost:8000

## Performance Tuning

**For better performance on Windows:**

1. **Use SSD** for input/output directories
2. **CPU-only PyTorch** (unless you have NVIDIA GPU)
3. **Close unnecessary programs** during heavy processing
4. **Adjust enhancement preset** in `.env`:
   ```env
   # gentle = fast but minimal enhancement
   # balanced = default, good quality/speed balance
   # aggressive = best quality but slower
   ENHANCEMENT_PRESET=gentle
   ```

## Support

- Documentation: See `diabay/DEPLOYMENT.md` for production deployment details
- Issues: https://github.com/yourusername/photoenhancer/issues
- Architecture: Backend is FastAPI (Python), Frontend is React (TypeScript)

---

**Estimated setup time:** 5-10 minutes
**Works on:** Windows 10/11, Windows Server 2019+
