"""DiaBay Configuration Management"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Directories
    input_dir: Path = Path("./input")
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

    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        import os
        # Skip directory creation in CI/test environments or if paths are not writable
        if os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST"):
            return

        for dir_path in [self.input_dir, self.analysed_dir,
                         self.output_dir, self.models_dir]:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError) as e:
                # Log warning but don't fail - directories might be created later
                print(f"Warning: Could not create directory {dir_path}: {e}")


# Global settings instance
settings = Settings()
settings.ensure_directories()
