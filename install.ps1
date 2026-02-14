<#
.SYNOPSIS
    DiaBay - Professional Slide & Film Digitization System Installer
.DESCRIPTION
    Automated installation script for Windows. Installs dependencies,
    configures directories, builds frontend, and sets up the application.
.NOTES
    Author: korgraph.io
    Requires: Python 3.10+, Node.js 18+ (optional, for building)
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ============================================================================
# HELPERS
# ============================================================================

function Write-Header {
    param([string]$Text)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "[OK]" -ForegroundColor Green -NoNewline
    Write-Host " $Text"
}

function Write-Error {
    param([string]$Text)
    Write-Host "[ERROR]" -ForegroundColor Red -NoNewline
    Write-Host " $Text"
}

function Write-Info {
    param([string]$Text)
    Write-Host "[INFO]" -ForegroundColor Yellow -NoNewline
    Write-Host " $Text"
}

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# ============================================================================
# MAIN INSTALLATION
# ============================================================================

Write-Header "DiaBay Installer for Windows"
Write-Host "Professional Slide & Film Digitization System`n" -ForegroundColor White

# Detect if running from web (irm|iex) or local file
$SCRIPT_DIR = $PSScriptRoot
$isRemoteExecution = [string]::IsNullOrEmpty($SCRIPT_DIR)

if ($isRemoteExecution) {
    Write-Info "Running from web - will download DiaBay first"

    # Installation directory
    $installPath = Join-Path $env:USERPROFILE "diabay"

    if (Test-Path $installPath) {
        Write-Info "DiaBay directory exists at: $installPath"
        Write-Host "Updating existing installation..." -ForegroundColor Cyan

        # Check if it's a git repo
        if (Test-Path (Join-Path $installPath ".git")) {
            Write-Host "Pulling latest changes from git..." -ForegroundColor Cyan
            Push-Location $installPath
            git pull 2>&1 | Out-Null
            Pop-Location
            Write-Success "Repository updated"
        } else {
            Write-Info "Not a git repository - will re-download"
            Remove-Item $installPath -Recurse -Force
        }
    }

    if (-not (Test-Path $installPath)) {
        Write-Host "Downloading DiaBay..." -ForegroundColor Cyan

        # Check for git
        if (Test-Command "git") {
            Write-Host "Using git to clone repository..." -ForegroundColor Cyan
            git clone https://github.com/mdopp/diabay.git $installPath 2>&1 | Out-Null
            Write-Success "Repository cloned"
        } else {
            Write-Host "Downloading as ZIP (git not found)..." -ForegroundColor Cyan
            $zipPath = Join-Path $env:TEMP "diabay.zip"
            Invoke-WebRequest -Uri "https://github.com/mdopp/diabay/archive/refs/heads/main.zip" -OutFile $zipPath
            Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
            Move-Item (Join-Path $env:TEMP "diabay-main") $installPath
            Remove-Item $zipPath
            Write-Success "Repository downloaded"
        }
    }

    $SCRIPT_DIR = $installPath
    Write-Info "Installation directory: $installPath"
}

$BACKEND_DIR = Join-Path $SCRIPT_DIR "backend"

# Verify backend directory exists
if (-not (Test-Path $BACKEND_DIR)) {
    Write-Error "Backend directory not found at: $BACKEND_DIR"
    Write-Host "Please ensure you're running this script from the DiaBay directory." -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# DEPENDENCY CHECKS
# ============================================================================

Write-Header "Checking Dependencies"

# Check Python
$pythonInstalled = Test-Command "python"
if ($pythonInstalled) {
    $pythonVersion = (python --version 2>&1) -replace "Python ", ""
    $versionParts = $pythonVersion.Split('.')
    $majorVersion = [int]$versionParts[0]
    $minorVersion = [int]$versionParts[1]

    if ($majorVersion -ge 3 -and $minorVersion -ge 10) {
        Write-Success "Python $pythonVersion found"
    } else {
        Write-Error "Python $pythonVersion is too old (need 3.10+)"
        $pythonInstalled = $false
    }
}

if (-not $pythonInstalled) {
    Write-Host "`nPython 3.10+ is required but not found." -ForegroundColor Yellow
    Write-Host "Installation options:" -ForegroundColor Yellow
    Write-Host "  1. Install via winget (recommended)" -ForegroundColor White
    Write-Host "  2. Install via Chocolatey" -ForegroundColor White
    Write-Host "  3. Download from python.org" -ForegroundColor White
    Write-Host "  4. Exit and install manually" -ForegroundColor White

    $choice = Read-Host "`nChoose an option (1-4)"

    switch ($choice) {
        "1" {
            if (Test-Command "winget") {
                Write-Host "Installing Python via winget..." -ForegroundColor Cyan
                winget install Python.Python.3.12 --silent
                Write-Success "Python installed. Please restart your terminal and run the installer again."
                exit 0
            } else {
                Write-Error "winget not found. Choose another option."
                exit 1
            }
        }
        "2" {
            if (Test-Command "choco") {
                Write-Host "Installing Python via Chocolatey..." -ForegroundColor Cyan
                choco install python --version=3.12 -y
                Write-Success "Python installed. Please restart your terminal and run the installer again."
                exit 0
            } else {
                Write-Error "Chocolatey not found. Install from https://chocolatey.org/"
                exit 1
            }
        }
        "3" {
            Write-Host "Opening Python download page..." -ForegroundColor Cyan
            Start-Process "https://www.python.org/downloads/"
            Write-Host "After installing Python, restart your terminal and run this installer again." -ForegroundColor Yellow
            exit 0
        }
        default {
            Write-Host "Please install Python 3.10+ manually from https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
    }
}

# Node.js not required - using pre-built frontend from CI/CD
Write-Success "Using pre-built frontend (Node.js not required)"

# ============================================================================
# DIRECTORY CONFIGURATION
# ============================================================================

Write-Header "Directory Configuration"

# Check for existing .env file to use as defaults
$envPath = Join-Path $BACKEND_DIR ".env"
$existingInput = $null
$existingOutput = $null

if (Test-Path $envPath) {
    Write-Info "Found existing .env file - using values as defaults"

    # Parse .env file
    $envContent = Get-Content $envPath
    foreach ($line in $envContent) {
        if ($line -match '^INPUT_DIR\s*=\s*(.+)$') {
            $existingInput = $matches[1].Trim('"').Trim("'")
        }
        elseif ($line -match '^OUTPUT_DIR\s*=\s*(.+)$') {
            $existingOutput = $matches[1].Trim('"').Trim("'")
        }
    }
}

# Get user directories as fallback
$userDocuments = [Environment]::GetFolderPath("MyDocuments")
$userPictures = [Environment]::GetFolderPath("MyPictures")

# Prompt for input directory
Write-Host "Input directory (where scanner saves TIFF files):" -ForegroundColor Yellow
if ($existingInput) {
    $defaultInput = $existingInput
    Write-Host "  Current: $existingInput" -ForegroundColor Gray
} else {
    $defaultInput = $userDocuments
}
$inputDir = Read-Host "  Path [$defaultInput]"
if ([string]::IsNullOrWhiteSpace($inputDir)) {
    $inputDir = $defaultInput
}
$inputDir = [System.IO.Path]::GetFullPath($inputDir)
Write-Success "Input: $inputDir"

# Prompt for output directory
Write-Host "`nOutput directory (where enhanced images will be saved):" -ForegroundColor Yellow
if ($existingOutput) {
    $defaultOutput = $existingOutput
    Write-Host "  Current: $existingOutput" -ForegroundColor Gray
} else {
    $defaultOutput = Join-Path $userPictures "dias"
}
$outputDir = Read-Host "  Path [$defaultOutput]"
if ([string]::IsNullOrWhiteSpace($outputDir)) {
    $outputDir = $defaultOutput
}
$outputDir = [System.IO.Path]::GetFullPath($outputDir)
Write-Success "Output: $outputDir"

# Derive other directories
$analysedDir = Join-Path (Split-Path $inputDir -Parent) "analysed"
$modelsDir = Join-Path $BACKEND_DIR "models"

Write-Info "Analysed: $analysedDir (auto-derived)"
Write-Info "Models: $modelsDir (auto-derived)"

# Create directories
Write-Host "`nCreating directories..." -ForegroundColor Yellow
foreach ($dir in @($inputDir, $analysedDir, $outputDir, $modelsDir)) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Success "Created: $dir"
    } else {
        Write-Info "Exists: $dir"
    }
}

# ============================================================================
# CREATE .ENV FILE
# ============================================================================

Write-Header "Creating Configuration"

$envPath = Join-Path $BACKEND_DIR ".env"
$envContent = @"
# DiaBay Configuration
# Generated by install.ps1 on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# Directories
INPUT_DIR=$($inputDir -replace '\\', '/')
ANALYSED_DIR=$($analysedDir -replace '\\', '/')
OUTPUT_DIR=$($outputDir -replace '\\', '/')
MODELS_DIR=$($modelsDir -replace '\\', '/')

# Image Processing
JPEG_QUALITY=95
CLAHE_CLIP_LIMIT=1.5
HISTOGRAM_CLIP=0.5
ENABLE_FACE_DETECTION=true
ADAPTIVE_CLAHE_GRID=true

# Output Formats
ENABLE_JPEG_XL=false
ENABLE_PNG_ARCHIVE=false
ENABLE_TIFF_ARCHIVE=false

# Duplicate Detection
DUPLICATE_THRESHOLD=0.95
AUTO_SKIP_DUPLICATES=true

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=false

# Database
DATABASE_URL=sqlite+aiosqlite:///$($BACKEND_DIR -replace '\\', '/')/diabay.db
"@

$envContent | Out-File -FilePath $envPath -Encoding utf8 -NoNewline
Write-Success "Created: $envPath"

# ============================================================================
# PYTHON ENVIRONMENT SETUP
# ============================================================================

Write-Header "Setting Up Python Environment"

$venvDir = Join-Path $BACKEND_DIR ".venv"

# Create virtual environment
if (!(Test-Path $venvDir)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvDir
    Write-Success "Virtual environment created"
} else {
    Write-Info "Virtual environment exists"
}

# Activate virtual environment
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& $activateScript

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install binary packages first (to avoid compilation issues)
Write-Host "Installing binary dependencies..." -ForegroundColor Yellow
pip install --only-binary=:all: numpy pillow opencv-python-headless --quiet
Write-Success "Binary packages installed"

# Install PyTorch (CPU-only for better compatibility)
Write-Host "Installing PyTorch (CPU-only)..." -ForegroundColor Yellow
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu --quiet
Write-Success "PyTorch installed"

# Install remaining dependencies (use latest versions with pre-built wheels)
Write-Host "Installing remaining dependencies..." -ForegroundColor Yellow
# Install key packages - using latest versions to ensure pre-built wheels are available
pip install fastapi uvicorn sqlalchemy aiosqlite pydantic pydantic-settings python-multipart aiofiles httpx tqdm watchdog websockets transformers piexif --upgrade --quiet
Write-Success "All dependencies installed"

# ============================================================================
# FRONTEND BUILD
# ============================================================================

Write-Header "Frontend Setup"

$frontendDir = Join-Path $SCRIPT_DIR "frontend"
$distDir = Join-Path $frontendDir "dist"

# Check if pre-built frontend exists
if (Test-Path $distDir) {
    Write-Success "Using pre-built frontend"
} else {
    Write-Info "Pre-built frontend not found - downloading from GitHub releases..."

    try {
        # Download latest release artifact
        $artifactUrl = "https://github.com/mdopp/diabay/releases/latest/download/frontend-dist.zip"
        $zipPath = Join-Path $env:TEMP "diabay-frontend.zip"

        Write-Host "Downloading frontend..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $artifactUrl -OutFile $zipPath -UseBasicParsing

        Write-Host "Extracting frontend..." -ForegroundColor Yellow
        Expand-Archive -Path $zipPath -DestinationPath $frontendDir -Force
        Remove-Item $zipPath -ErrorAction SilentlyContinue

        Write-Success "Frontend downloaded and extracted"
    } catch {
        Write-Error "Failed to download frontend from GitHub releases"
        Write-Host "You can:" -ForegroundColor Yellow
        Write-Host "  1. Download the complete package from https://github.com/mdopp/diabay/releases" -ForegroundColor Yellow
        Write-Host "  2. Wait for CI/CD to build and publish artifacts" -ForegroundColor Yellow
        Write-Host "`nContinuing without frontend - backend will still work." -ForegroundColor Gray
    }
}

# ============================================================================
# CREATE STARTUP SCRIPT
# ============================================================================

Write-Header "Creating Startup Scripts"

$startScriptPath = Join-Path $SCRIPT_DIR "start-diabay.ps1"
$startScriptContent = @"
#!/usr/bin/env pwsh
# DiaBay Startup Script
# Generated by install.ps1

`$ErrorActionPreference = "Stop"
`$BACKEND_DIR = Join-Path `$PSScriptRoot "backend"

Write-Host "Starting DiaBay..." -ForegroundColor Cyan

# Activate virtual environment
`$activateScript = Join-Path `$BACKEND_DIR ".venv\Scripts\Activate.ps1"
& `$activateScript

# Change to backend directory
Push-Location `$BACKEND_DIR

# Start server
Write-Host "Server starting on http://localhost:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop`n" -ForegroundColor Yellow

python main.py

Pop-Location
"@

$startScriptContent | Out-File -FilePath $startScriptPath -Encoding utf8 -NoNewline
Write-Success "Created: $startScriptPath"

# Create batch file wrapper
$batchPath = Join-Path $SCRIPT_DIR "start-diabay.bat"
$batchContent = @"
@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0start-diabay.ps1"
"@

$batchContent | Out-File -FilePath $batchPath -Encoding ascii -NoNewline
Write-Success "Created: $batchPath"

# ============================================================================
# INSTALLATION COMPLETE
# ============================================================================

Write-Header "Installation Complete!"

Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  Input:    $inputDir" -ForegroundColor White
Write-Host "  Output:   $outputDir" -ForegroundColor White
Write-Host "  Analysed: $analysedDir" -ForegroundColor White

Write-Host "`nTo start DiaBay:" -ForegroundColor Yellow
Write-Host "  .\start-diabay.bat" -ForegroundColor White
Write-Host "  or" -ForegroundColor Gray
Write-Host "  .\start-diabay.ps1" -ForegroundColor White

Write-Host "`nThen open: http://localhost:8000" -ForegroundColor Cyan

Write-Host "`nOptional - Create Desktop Shortcut:" -ForegroundColor Yellow
$createShortcut = Read-Host "Create desktop shortcut? (y/N)"
if ($createShortcut -eq "y" -or $createShortcut -eq "Y") {
    $WshShell = New-Object -ComObject WScript.Shell
    $Desktop = [Environment]::GetFolderPath("Desktop")
    $ShortcutPath = Join-Path $Desktop "DiaBay.lnk"
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "powershell.exe"
    $Shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$startScriptPath`""
    $Shortcut.WorkingDirectory = $SCRIPT_DIR
    $Shortcut.Description = "DiaBay - Professional Slide Digitization System"
    $Shortcut.Save()
    Write-Success "Desktop shortcut created"
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Happy scanning! " -ForegroundColor White -NoNewline
Write-Host "https://korgraph.io" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
