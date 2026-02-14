"""
File system watcher for automatic image processing
Monitors input directory and triggers processing pipeline
"""
import asyncio
import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileDeletedEvent
import logging

logger = logging.getLogger(__name__)


class ImageFileHandler(FileSystemEventHandler):
    """Handle file system events for image files"""

    SUPPORTED_EXTENSIONS = {'.tif', '.tiff', '.TIF', '.TIFF', '.jpg', '.jpeg', '.JPG', '.JPEG'}

    def __init__(self,
                 callback: Callable[[Path], None],
                 deletion_callback: Optional[Callable[[Path], None]] = None,
                 debounce_seconds: float = 2.0):
        """
        Initialize handler

        Args:
            callback: Async function to call when new image file is stable
            deletion_callback: Async function to call when file is deleted
            debounce_seconds: Wait time for file to finish writing
        """
        super().__init__()
        self.callback = callback
        self.deletion_callback = deletion_callback
        self.debounce_seconds = debounce_seconds
        self.pending_files = {}  # path -> (size, timestamp)

    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if supported image format
        if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
            return

        logger.info(f"New file detected: {file_path.name}")

        # Add to pending files for stability check
        self.pending_files[file_path] = (0, time.time())

    def on_deleted(self, event):
        """Handle file deletion events"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if supported image format
        if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
            return

        logger.info(f"File deleted: {file_path.name}")

        # Remove from pending files if it was there
        if file_path in self.pending_files:
            del self.pending_files[file_path]

        # Call deletion callback if provided
        if self.deletion_callback:
            try:
                # Create async task for deletion callback
                asyncio.create_task(self.deletion_callback(file_path))
            except Exception as e:
                logger.error(f"Error handling deletion of {file_path}: {e}")

    async def check_stable_files(self):
        """
        Continuously check if pending files are stable (finished writing)
        A file is stable when its size hasn't changed for debounce_seconds
        """
        logger.info("[Stability Checker] Started")
        try:
            while True:
                await asyncio.sleep(1)  # Check every second

                # Log pending files count periodically
                if len(self.pending_files) > 0:
                    logger.debug(f"[Stability Checker] Checking {len(self.pending_files)} pending files")

                stable_files = []
                current_time = time.time()

                for file_path, (prev_size, timestamp) in list(self.pending_files.items()):
                    if not file_path.exists():
                        # File deleted, remove from pending
                        del self.pending_files[file_path]
                        continue

                    try:
                        current_size = file_path.stat().st_size

                        if current_size == prev_size:
                            # Size unchanged
                            if current_time - timestamp >= self.debounce_seconds:
                                # File is stable!
                                stable_files.append(file_path)
                                del self.pending_files[file_path]
                        else:
                            # Size changed, update and reset timer
                            self.pending_files[file_path] = (current_size, current_time)

                    except OSError as e:
                        logger.warning(f"Error checking file {file_path}: {e}")
                        continue

                # Process stable files
                for file_path in stable_files:
                    logger.info(f"[Stability Checker] File stable, processing: {file_path.name}")
                    try:
                        await self.callback(file_path)
                    except Exception as e:
                        logger.error(f"[Stability Checker] Error processing {file_path}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"[Stability Checker] CRASHED: {e}", exc_info=True)
            raise


class FileWatcher:
    """
    Watch directory for new image files and trigger processing
    """

    def __init__(self,
                 watch_dir: Path,
                 callback: Callable[[Path], None],
                 deletion_callback: Optional[Callable[[Path], None]] = None,
                 debounce_seconds: float = 2.0):
        """
        Initialize file watcher

        Args:
            watch_dir: Directory to monitor
            callback: Async function to call for each stable file
            deletion_callback: Async function to call when file is deleted
            debounce_seconds: Wait time for file stability
        """
        self.watch_dir = watch_dir
        self.callback = callback
        self.deletion_callback = deletion_callback
        self.debounce_seconds = debounce_seconds

        self.observer: Optional[Observer] = None
        self.handler: Optional[ImageFileHandler] = None
        self._stability_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start watching directory"""
        self.watch_dir.mkdir(parents=True, exist_ok=True)

        self.handler = ImageFileHandler(
            self.callback,
            self.deletion_callback,
            self.debounce_seconds
        )
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.watch_dir), recursive=True)
        self.observer.start()

        # Start stability checker
        self._stability_task = asyncio.create_task(self.handler.check_stable_files())

        logger.info(f"Started watching: {self.watch_dir}")

    async def stop(self):
        """Stop watching"""
        if self.observer:
            self.observer.stop()
            self.observer.join()

        if self._stability_task:
            self._stability_task.cancel()
            try:
                await self._stability_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped file watcher")

    async def process_existing_files(self):
        """
        Process any existing files in the watch directory
        Useful for resuming after restart
        """
        for file_path in self.watch_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in ImageFileHandler.SUPPORTED_EXTENSIONS:
                logger.info(f"Processing existing file: {file_path.name}")
                try:
                    await self.callback(file_path)
                except Exception as e:
                    logger.error(f"Error processing existing file {file_path}: {e}")
