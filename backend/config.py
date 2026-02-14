"""DiaBay Configuration Management"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Directories
    # Note: Use INPUT_DIRS (plural) for comma-separated list of directories
    # INPUT_DIR (singular) should be a single path
    input_dir: str = "./input"
    # Comma-separated list of additional input directories to watch
    # Example: INPUT_DIRS="D:/Scans/New,D:/Scans/Archive"
    input_dirs: str = ""
    analysed_dir: Path = Path("./analysed")
    output_dir: Path = Path("./output")
    models_dir: Path = Path("./models")

    # Image Processing
    jpeg_quality: int = 95
    clahe_clip_limit: float = 1.5
    histogram_clip: float = 0.5
    enable_face_detection: bool = True
    adaptive_clahe_grid: bool = True

    # Output Formats
    enable_jpeg_xl: bool = False
    enable_png_archive: bool = False
    enable_tiff_archive: bool = False

    # Duplicate Detection
    duplicate_threshold: float = 0.95
    auto_skip_duplicates: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./diabay.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    def get_input_directories(self) -> list[Path]:
        """
        Get all input directories (main + additional)

        Returns:
            List of Path objects for all input directories
        """
        dirs = []

        # Handle backward compatibility: if input_dir contains comma, parse as list
        if ',' in self.input_dir:
            print("⚠️  WARNING: INPUT_DIR contains comma-separated paths. "
                  "Please use INPUT_DIR for single path and INPUT_DIRS for additional paths.")
            for dir_str in self.input_dir.split(','):
                dir_str = dir_str.strip()
                if dir_str:
                    dirs.append(Path(dir_str))
        else:
            dirs.append(Path(self.input_dir))

        # Parse comma-separated additional directories
        if self.input_dirs:
            for dir_str in self.input_dirs.split(','):
                dir_str = dir_str.strip()
                if dir_str:
                    dirs.append(Path(dir_str))

        return dirs

    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        import os
        # Skip directory creation in CI/test environments or if paths are not writable
        if os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST"):
            return

        # Get all input directories
        all_input_dirs = self.get_input_directories()

        # Parse other directories (they might also have commas, though not recommended)
        other_dirs = [Path(self.analysed_dir), Path(self.output_dir), Path(self.models_dir)]

        for dir_path in all_input_dirs + other_dirs:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError) as e:
                # Log warning but don't fail - directories might be created later
                print(f"Warning: Could not create directory {dir_path}: {e}")


# Global settings instance
settings = Settings()
settings.ensure_directories()
