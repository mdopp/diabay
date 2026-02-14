# DiaBay Installation Guide

Complete installation instructions for DiaBay - Professional Slide & Film Digitization System.

## Table of Contents

- [Quick Install](#quick-install)
- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
  - [Automated Installation](#automated-installation)
  - [Manual Installation](#manual-installation)
  - [Pre-Built Packages](#pre-built-packages)
- [Configuration](#configuration)
- [Starting DiaBay](#starting-diabay)
- [Troubleshooting](#troubleshooting)

---

## Quick Install

### Windows

**Option 1: Download and run installer**
```powershell
.\install.bat
```

**Option 2: One-line from web (if repository is public)**
```powershell
irm https://raw.githubusercontent.com/YOUR_ORG/diabay/main/install.ps1 | iex
```

### Linux/WSL

**Option 1: Download and run installer**
```bash
./install.sh
```

**Option 2: One-line from web (if repository is public)**
```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/diabay/main/install.sh | bash
```

---

## System Requirements

### Minimum Requirements

- **OS:** Windows 10/11, Linux (Ubuntu 20.04+, Debian 11+, or similar)
- **CPU:** Intel Core i5 or AMD Ryzen 5 (4+ cores recommended)
- **RAM:** 4 GB (8 GB+ recommended for AI processing)
- **Storage:** 10 GB free space (more for images)
- **Python:** 3.10 or newer
- **Network:** For web UI access from other devices (optional)

### Optional Dependencies

- **Node.js 18+:** Only needed for building frontend from source (installer can use pre-built)
- **Git:** For cloning repository (or download as ZIP)

---

## Installation Methods

### Automated Installation

The automated installer (`install.ps1` for Windows, `install.sh` for Linux) handles everything:

**What it does:**
1. ✅ Checks for Python 3.10+
2. ✅ Prompts for input directory (default: `Documents`)
3. ✅ Prompts for output directory (default: `Pictures/dias`)
4. ✅ Creates required directories automatically
5. ✅ Generates `.env` configuration file
6. ✅ Creates Python virtual environment
7. ✅ Installs PyTorch (CPU-only for compatibility)
8. ✅ Installs all Python dependencies
9. ✅ Builds frontend (or uses pre-built from CI/CD)
10. ✅ Creates startup scripts
11. ✅ (Linux only) Optionally creates systemd service

**What it asks you:**
- Input directory path (where your scanner saves TIFF files)
- Output directory path (where enhanced images will be saved)
- (Linux only) Whether to create a systemd service

**Derived automatically:**
- `analysed/` directory: placed next to input directory
- `models/` directory: inside backend folder (for AI models)
- Database location: inside backend folder

**Example directory structure:**
```
C:\Users\YourName\Documents\           ← Input directory (TIFF files from scanner)
C:\Users\YourName\Documents\..\analysed\  ← Analysed (renamed TIFF files)
C:\Users\YourName\Pictures\dias\       ← Output directory (enhanced JPEG files)
```

### Manual Installation

If you prefer manual control:

#### 1. Clone or Download

```bash
git clone https://github.com/YOUR_ORG/diabay.git
cd diabay
```

#### 2. Create Virtual Environment

**Linux/WSL:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
# Install PyTorch (CPU-only)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install other requirements
pip install -r requirements.txt
```

#### 4. Configure Environment

Copy `.env.example` to `.env` and edit paths:

**Linux:**
```bash
cp .env.example .env
nano .env
```

**Windows:**
```powershell
copy .env.example .env
notepad .env
```

**Update these values:**
```env
INPUT_DIR=/path/to/your/scanner/input
OUTPUT_DIR=/path/to/your/pictures/dias
ANALYSED_DIR=/path/to/analysed
MODELS_DIR=./models
```

#### 5. Build Frontend (Optional)

If you have Node.js and want to build from source:

```bash
cd frontend
npm install
npm run build
cd ..
```

Or download pre-built frontend from CI/CD artifacts (see below).

#### 6. Start Application

```bash
cd backend
python main.py
```

Open browser: http://localhost:8000

---

### Pre-Built Packages

For production deployments without Node.js:

#### Download from GitLab CI/CD

1. Go to your GitLab project
2. Navigate to **CI/CD → Pipelines**
3. Find latest successful pipeline on `main` branch
4. Download artifacts:
   - **Windows:** `diabay-windows-{sha}.zip`
   - **Linux:** `diabay-linux-{sha}.tar.gz`

#### Download from Releases

1. Go to **Releases** page
2. Download latest stable release:
   - **Windows:** `diabay-windows-{version}.zip`
   - **Linux:** `diabay-linux-{version}.tar.gz`

#### Extract and Install

**Windows:**
```powershell
Expand-Archive diabay-windows-*.zip -DestinationPath C:\DiaBay
cd C:\DiaBay\diabay
.\install.bat
```

**Linux:**
```bash
tar xzf diabay-linux-*.tar.gz
cd diabay
./install.sh
```

These packages include pre-built frontend, so Node.js is **not** required.

---

## Configuration

### Environment Variables

All configuration is in `backend/.env`:

```env
# Directories (absolute paths recommended)
INPUT_DIR=/home/user/Documents
ANALYSED_DIR=/home/user/Documents/analysed
OUTPUT_DIR=/home/user/Pictures/dias
MODELS_DIR=/home/user/diabay/backend/models

# Image Processing
JPEG_QUALITY=95              # Output JPEG quality (80-100)
CLAHE_CLIP_LIMIT=1.5         # Contrast enhancement strength
HISTOGRAM_CLIP=0.5           # Histogram adjustment
ENABLE_FACE_DETECTION=true   # Gentler processing for portraits
ADAPTIVE_CLAHE_GRID=true     # Adaptive grid sizing

# Output Formats (experimental)
ENABLE_JPEG_XL=false         # Enable JPEG XL output
ENABLE_PNG_ARCHIVE=false     # Save PNG copies
ENABLE_TIFF_ARCHIVE=false    # Save TIFF copies

# Duplicate Detection
DUPLICATE_THRESHOLD=0.95     # Similarity threshold (0.0-1.0)
AUTO_SKIP_DUPLICATES=true    # Skip processing duplicates

# Server
HOST=0.0.0.0                 # Listen on all interfaces
PORT=8000                    # Server port
RELOAD=false                 # Auto-reload on code changes (dev only)

# Database
DATABASE_URL=sqlite+aiosqlite:///./diabay.db
```

### Directory Recommendations

**Input Directory:**
- Where your scanner software saves TIFF files
- Should have fast disk I/O
- Example: `C:\Users\YourName\Documents\Scanner` (Windows)
- Example: `/home/user/Documents/Scanner` (Linux)

**Output Directory:**
- Where enhanced JPEG files are saved
- Can be on different drive for space
- Example: `D:\Pictures\dias` (Windows with multiple drives)
- Example: `/home/user/Pictures/dias` (Linux)

**Analysed Directory:**
- Stores renamed TIFF files (original + EXIF date)
- Should be near input directory
- Automatically derived: `{INPUT_DIR}/../analysed`

---

## Starting DiaBay

### Windows

**Start script (recommended):**
```powershell
.\start-diabay.bat
```

**PowerShell script:**
```powershell
.\start-diabay.ps1
```

**Manual:**
```powershell
cd backend
.venv\Scripts\activate
python main.py
```

### Linux

**Start script (recommended):**
```bash
./start-diabay.sh
```

**Systemd service (if installed):**
```bash
systemctl --user start diabay
systemctl --user status diabay
systemctl --user enable diabay  # Auto-start on boot
```

**Manual:**
```bash
cd backend
source .venv/bin/activate
python main.py
```

### Access Web UI

- **Local:** http://localhost:8000
- **Network:** http://{your-ip}:8000
  - Find your IP: `ipconfig` (Windows) or `ip addr show` (Linux)
  - Example: http://192.168.1.100:8000
  - Access from phone, tablet, or other computers

---

## Troubleshooting

### Python Not Found

**Error:** `python: command not found` or `Python 3.10+ not found`

**Solution:**
- **Windows:** Install from [python.org](https://www.python.org/downloads/)
  - Check "Add Python to PATH" during installation
- **Linux:** `sudo apt install python3 python3-venv python3-pip`

### Permission Denied (Linux)

**Error:** `Permission denied: './install.sh'`

**Solution:**
```bash
chmod +x install.sh
./install.sh
```

### Virtual Environment Activation Fails (Windows)

**Error:** `cannot be loaded because running scripts is disabled`

**Solution:** Run PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port 8000 Already in Use

**Error:** `Address already in use: 8000`

**Solution:** Change port in `.env`:
```env
PORT=8001
```

### No Frontend Build Found

**Error:** `No frontend build found and Node.js not available`

**Solution 1:** Download pre-built package from CI/CD (recommended)

**Solution 2:** Install Node.js and rebuild:
```bash
cd frontend
npm install
npm run build
```

### PyTorch Installation Fails

**Error:** Memory errors or slow installation

**Solution:** Use CPU-only version:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Database Lock Errors

**Error:** `database is locked`

**Solution:** Ensure only one instance is running:
- Stop all DiaBay processes
- Delete `backend/diabay.db-journal` if exists
- Restart

### File Watcher Not Detecting New Files

**Symptoms:** New TIFFs in input directory not processed

**Solution:**
- Check `.env` paths are correct and absolute
- Verify directories exist and are writable
- Check logs: `backend/backend.log`
- Restart DiaBay

---

## Next Steps

After installation:

1. **Place TIFF files** in your input directory
2. **Open web UI** at http://localhost:8000
3. **Watch processing** happen automatically
4. **View enhanced images** in gallery
5. **Check statistics** for processing metrics

For detailed usage instructions, see [README.md](README.md).

For production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md).

For Windows-specific setup, see [WINDOWS_SETUP.md](WINDOWS_SETUP.md).

---

## Support

- **Issues:** https://github.com/YOUR_ORG/diabay/issues
- **Documentation:** Project README and docs/
- **Website:** https://korgraph.io

---

**Happy scanning!** 📸
