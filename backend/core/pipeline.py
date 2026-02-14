"""
Processing pipeline orchestrator
Coordinates all stages: ingestion → enhancement → tagging → duplicate detection
"""
import asyncio
import time
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.processor import ImageProcessor, EnhancementPreset
from core.watcher import FileWatcher
from core.tagger import ImageTagger
from db.models import Image, ImageMetadata, ImageEmbedding, ImageTag, ProcessingSession
from config import settings

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """
    Main processing pipeline that orchestrates all stages
    """

    def __init__(self,
                 db_session_factory: Callable,
                 status_callback: Optional[Callable] = None):
        """
        Initialize pipeline

        Args:
            db_session_factory: Factory function to create database sessions
            status_callback: Async callback for status updates (for WebSocket)
        """
        self.db_session_factory = db_session_factory
        self.status_callback = status_callback

        # Initialize components
        self.processor = ImageProcessor(
            histogram_clip=settings.histogram_clip,
            clahe_clip=settings.clahe_clip_limit,
            adaptive_grid=settings.adaptive_clahe_grid,
            face_detection=settings.enable_face_detection
        )

        # Initialize AI tagger (lazy loading of CLIP model)
        self.tagger: Optional[ImageTagger] = None
        try:
            self.tagger = ImageTagger(confidence_threshold=0.15)  # Lower threshold to get more scene tags
            logger.info("AI tagger initialized successfully")
        except Exception as e:
            logger.warning(f"AI tagger initialization failed: {e}")
            logger.warning("Auto-tagging will be disabled")

        self.watchers: list[FileWatcher] = []  # Multiple input directory watchers
        self.output_watcher: Optional[FileWatcher] = None  # Watches output directory for deletions

        # Processing state
        self.is_processing = False
        self.current_file: Optional[str] = None
        self.current_stage: Optional[str] = None
        self.stats = {
            'processed_count': 0,
            'error_count': 0,
            'start_time': None,
            'processing_times': [],  # Last 50 processing times
            'hourly_counts': {},  # Dict[hour_key, count] for timeline chart
            'error_log': [],  # Recent errors with details (last 50)
        }

    async def start(self):
        """Start the pipeline and file watcher"""
        logger.info("Starting processing pipeline...")

        self.stats['start_time'] = datetime.utcnow()

        # Create watchers for all input directories
        all_input_dirs = settings.get_input_directories()
        logger.info(f"Setting up watchers for {len(all_input_dirs)} input directories")

        for input_dir in all_input_dirs:
            if not input_dir.exists():
                logger.warning(f"Input directory does not exist: {input_dir}")
                continue

            watcher = FileWatcher(
                watch_dir=input_dir,
                callback=self.process_file,
                debounce_seconds=2.0
            )
            self.watchers.append(watcher)
            logger.info(f"Created watcher for input directory: {input_dir}")

        # Create output directory watcher (for deletions)
        self.output_watcher = FileWatcher(
            watch_dir=settings.output_dir,
            callback=lambda x: asyncio.create_task(asyncio.sleep(0)),  # No-op for creation
            deletion_callback=self.handle_file_deletion,
            debounce_seconds=0.5
        )

        # Start all watchers
        for watcher in self.watchers:
            await watcher.start()
        await self.output_watcher.start()

        # Launch background task to process existing files (don't block API startup)
        asyncio.create_task(self._process_existing_files_background())

        logger.info("Pipeline started successfully")

    async def stop(self):
        """Stop the pipeline"""
        for watcher in self.watchers:
            await watcher.stop()

        if self.output_watcher:
            await self.output_watcher.stop()

        logger.info("Pipeline stopped")

    async def update_tag_stats_cache(self, tag_stats: dict):
        """Update cached tag statistics for WebSocket broadcast"""
        self._cached_tag_stats = tag_stats

    async def _process_existing_files_background(self):
        """
        Background task to process existing files without blocking API startup.

        This method runs in the background and processes:
        1. Existing files in input directory (ingest + enhance)
        2. Existing files in analysed directory (enhance only)
        """
        try:
            # First, process existing files in all input directories
            logger.info(f"Background task: Processing existing files from {len(self.watchers)} watchers...")
            for i, watcher in enumerate(self.watchers):
                logger.info(f"  Watcher {i+1}/{len(self.watchers)}: {watcher.watch_dir}")
                await watcher.process_existing_files()

            # Then, process existing files in analysed directory
            logger.info("Background task: Processing existing files in analysed directory...")
            await self.process_existing_analysed_files()

            logger.info("Background task: Finished processing all existing files")
        except Exception as e:
            logger.error(f"Error in background file processing: {e}", exc_info=True)

    async def handle_file_deletion(self, file_path: Path):
        """
        Handle deletion of enhanced image files.

        When a user deletes an enhanced JPG, update the database and optionally
        clean up related files (thumbnail, etc.)

        Args:
            file_path: Path to the deleted file
        """
        try:
            filename = file_path.name
            logger.info(f"Handling deletion of: {filename}")

            async with self.db_session_factory() as session:
                # Find the image record
                query = select(Image).where(Image.filename == filename)
                result = await session.execute(query)
                image = result.scalar_one_or_none()

                if image:
                    # Delete related records (tags, metadata, embeddings) - handled by cascade
                    await session.delete(image)
                    await session.commit()

                    logger.info(f"Deleted database record for {filename}")

                    # Optionally delete thumbnail
                    thumbnail_path = settings.output_dir.parent / "thumbnails" / filename
                    if thumbnail_path.exists():
                        await asyncio.to_thread(thumbnail_path.unlink)
                        logger.info(f"Deleted thumbnail for {filename}")
                else:
                    logger.warning(f"No database record found for deleted file: {filename}")

        except Exception as e:
            logger.error(f"Error handling file deletion for {file_path}: {e}", exc_info=True)

    async def process_existing_analysed_files(self):
        """
        Process existing files in the analysed directory that haven't been enhanced yet.

        This handles the case where files are already in analysed/ (from previous sessions)
        but haven't been enhanced yet. Skips the ingestion stage since files are already renamed.
        """
        logger.info("Scanning analysed directory for unprocessed files...")

        analysed_files = list(settings.analysed_dir.rglob("*.tif*"))
        unprocessed_count = 0

        for analysed_path in analysed_files:
            # Check if this file has already been enhanced
            # The output filename is the same stem but .jpg extension
            output_path = settings.output_dir / f"{analysed_path.stem}.jpg"

            if output_path.exists():
                # Already processed, skip
                continue

            # Process this file (skip ingestion since it's already in analysed)
            unprocessed_count += 1
            logger.info(f"Processing existing analysed file: {analysed_path.name}")
            await self.process_analysed_file(analysed_path)

        if unprocessed_count > 0:
            logger.info(f"Processed {unprocessed_count} existing files from analysed directory")
        else:
            logger.info("No unprocessed files found in analysed directory")

    async def process_file(self, file_path: Path):
        """
        Process a single file through the entire pipeline

        Stages:
        1. Ingest: Move to analysed/ with intelligent naming
        2. Enhance: Apply image enhancement
        3. Tag: Extract metadata, scene classification, OCR
        4. Save: Write enhanced image and update database
        """
        start_time = time.time()
        self.is_processing = True
        self.current_file = file_path.name

        try:
            async with self.db_session_factory() as session:
                # Stage 1: Ingest (rename based on EXIF)
                await self._update_status("ingestion", 10)
                analysed_path = await self._ingest_file(file_path, session)

                # Update current file to show renamed filename
                self.current_file = analysed_path.name

                # Stage 2: Enhance
                await self._update_status("enhancement", 40)
                result = await asyncio.to_thread(
                    self.processor.process_image,
                    analysed_path,
                    auto_quality=True
                )

                # Stage 3: Save enhanced image
                await self._update_status("saving", 70)
                output_formats = ['jpg']
                if settings.enable_jpeg_xl:
                    output_formats.append('jxl')
                if settings.enable_png_archive:
                    output_formats.append('png')
                if settings.enable_tiff_archive:
                    output_formats.append('tiff')

                # Use renamed filename (from analysed directory) for output
                output_path = settings.output_dir / analysed_path.stem
                saved_files = await asyncio.to_thread(
                    self.processor.save_enhanced,
                    result.enhanced,
                    output_path,
                    quality=settings.jpeg_quality,
                    formats=output_formats
                )

                # Stage 4: Update database
                await self._update_status("tagging", 90)
                await self._save_to_database(
                    session,
                    file_path,
                    analysed_path,
                    saved_files['jpg'],
                    result
                )

                await session.commit()

                # Update stats
                processing_time = time.time() - start_time
                self.stats['processed_count'] += 1
                self.stats['processing_times'].append(processing_time)
                if len(self.stats['processing_times']) > 50:
                    self.stats['processing_times'].pop(0)

                # Track hourly count for timeline chart
                hour_key = datetime.utcnow().strftime('%Y-%m-%d %H:00')
                self.stats['hourly_counts'][hour_key] = self.stats['hourly_counts'].get(hour_key, 0) + 1

                await self._update_status("complete", 100)
                logger.info(f"Successfully processed {file_path.name} in {processing_time:.1f}s")

        except Exception as e:
            self.stats['error_count'] += 1

            # Store error details for user visibility
            error_detail = {
                'filename': file_path.name,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'stage': self.current_stage or 'unknown'
            }
            self.stats['error_log'].append(error_detail)

            # Keep only last 50 errors
            if len(self.stats['error_log']) > 50:
                self.stats['error_log'] = self.stats['error_log'][-50:]

            logger.error(f"Error processing {file_path}: {e}", exc_info=True)
            await self._update_status("error", 0, error=str(e))

        finally:
            self.is_processing = False
            self.current_file = None
            self.current_stage = None

    async def process_analysed_file(self, analysed_path: Path):
        """
        Process a file that's already in the analysed directory (skip ingestion stage).

        This is used for files that were renamed/moved in a previous session but
        haven't been enhanced yet.

        Stages:
        1. (Skipped) Ingest - already in analysed/
        2. Enhance: Apply image enhancement
        3. Tag: Extract metadata, scene classification, OCR
        4. Save: Write enhanced image and update database
        """
        start_time = time.time()
        self.is_processing = True
        self.current_file = analysed_path.name

        try:
            async with self.db_session_factory() as session:
                # Stage 2: Enhance (skip ingestion since file is already in analysed/)
                await self._update_status("enhancement", 40)
                result = await asyncio.to_thread(
                    self.processor.process_image,
                    analysed_path,
                    auto_quality=True
                )

                # Stage 3: Save enhanced image
                await self._update_status("saving", 70)
                output_formats = ['jpg']
                if settings.enable_jpeg_xl:
                    output_formats.append('jxl')
                if settings.enable_png_archive:
                    output_formats.append('png')
                if settings.enable_tiff_archive:
                    output_formats.append('tiff')

                # Use existing filename (already renamed in analysed directory)
                output_path = settings.output_dir / analysed_path.stem
                saved_files = await asyncio.to_thread(
                    self.processor.save_enhanced,
                    result.enhanced,
                    output_path,
                    quality=settings.jpeg_quality,
                    formats=output_formats
                )

                # Stage 4: Update database
                await self._update_status("tagging", 90)
                await self._save_to_database(
                    session,
                    analysed_path,  # Use analysed_path as both original and analysed
                    analysed_path,
                    saved_files['jpg'],
                    result
                )

                await session.commit()

                # Update stats
                processing_time = time.time() - start_time
                self.stats['processed_count'] += 1
                self.stats['processing_times'].append(processing_time)
                if len(self.stats['processing_times']) > 50:
                    self.stats['processing_times'].pop(0)

                # Track hourly count for timeline chart
                hour_key = datetime.utcnow().strftime('%Y-%m-%d %H:00')
                self.stats['hourly_counts'][hour_key] = self.stats['hourly_counts'].get(hour_key, 0) + 1

                await self._update_status("complete", 100)
                logger.info(f"Successfully processed existing file {analysed_path.name} in {processing_time:.1f}s")

        except Exception as e:
            self.stats['error_count'] += 1

            # Store error details for user visibility
            error_detail = {
                'filename': analysed_path.name,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'stage': self.current_stage or 'unknown'
            }
            self.stats['error_log'].append(error_detail)

            # Keep only last 50 errors
            if len(self.stats['error_log']) > 50:
                self.stats['error_log'] = self.stats['error_log'][-50:]

            logger.error(f"Error processing existing file {analysed_path}: {e}", exc_info=True)
            await self._update_status("error", 0, error=str(e))

        finally:
            self.is_processing = False
            self.current_file = None
            self.current_stage = None

    def _extract_exif_date(self, file_path: Path) -> Optional[datetime]:
        """
        Extract scan date from EXIF metadata

        Args:
            file_path: Path to TIFF file

        Returns:
            Datetime from EXIF, or None if not found
        """
        try:
            from PIL import Image as PILImage
            from PIL.ExifTags import TAGS

            img = PILImage.open(file_path)
            exif_data = img._getexif()

            if exif_data:
                # Try different date fields
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    if tag_name in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                        # Parse EXIF date format: "2024:02:10 14:32:15"
                        try:
                            return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            continue

            return None

        except Exception as e:
            logger.warning(f"Could not extract EXIF from {file_path.name}: {e}")
            return None

    def _generate_unique_filename(self, base_date: datetime, extension: str = ".tif") -> Path:
        """
        Generate unique filename based on date

        Format: image_YYMMDD_HHMMSS.tif
        If collision, adds counter: image_YYMMDD_HHMMSS_01.tif

        Args:
            base_date: Date to use for filename
            extension: File extension

        Returns:
            Path to unique file in analysed directory
        """
        # Base filename: image_240210_143215.tif
        base_name = f"image_{base_date.strftime('%y%m%d_%H%M%S')}"
        candidate = settings.analysed_dir / f"{base_name}{extension}"

        # Handle collisions
        counter = 1
        while candidate.exists():
            candidate = settings.analysed_dir / f"{base_name}_{counter:02d}{extension}"
            counter += 1

        return candidate

    async def _ingest_file(self, file_path: Path, session: AsyncSession) -> Path:
        """
        Move file to analysed directory with EXIF-based naming

        Critical: Renames files immediately to avoid overwrites when
        processing multiple magazines with repeating filenames (IMG_001.tif, etc.)

        Naming strategy:
        1. Extract EXIF scan date → image_YYMMDD_HHMMSS.tif
        2. Fall back to file modification time if no EXIF
        3. Add counter suffix for collisions
        """
        # Extract date from EXIF or file stats
        exif_date = await asyncio.to_thread(self._extract_exif_date, file_path)

        if exif_date:
            logger.info(f"Using EXIF date for {file_path.name}: {exif_date}")
            base_date = exif_date
        else:
            # Fallback to file modification time
            file_stat = file_path.stat()
            base_date = datetime.fromtimestamp(file_stat.st_mtime)
            logger.info(f"Using file date for {file_path.name}: {base_date}")

        # Generate unique filename
        analysed_path = self._generate_unique_filename(base_date, file_path.suffix)
        analysed_path.parent.mkdir(parents=True, exist_ok=True)

        # Move and rename file
        # Use shutil.move for cross-drive compatibility (rename doesn't work across drives)
        import shutil
        await asyncio.to_thread(shutil.move, str(file_path), str(analysed_path))
        logger.info(f"Renamed: {file_path.name} → {analysed_path.name}")

        return analysed_path

    async def _save_to_database(self,
                                session: AsyncSession,
                                original_path: Path,
                                analysed_path: Path,
                                enhanced_path: Path,
                                result):
        """Save image record and metadata to database"""
        from sqlalchemy import select

        # Check if image already exists
        query = select(Image).where(Image.filename == enhanced_path.name)
        result_db = await session.execute(query)
        existing_image = result_db.scalar_one_or_none()

        if existing_image:
            # Update existing record
            # Store enhanced_path as relative to static file serving (e.g., "output/image.jpg")
            existing_image.original_path = str(analysed_path)
            existing_image.enhanced_path = f"output/{enhanced_path.name}"
            existing_image.width = result.original_size[0]
            existing_image.height = result.original_size[1]
            existing_image.file_size = enhanced_path.stat().st_size
            existing_image.status = "complete"
            existing_image.stage = "tagging"
            existing_image.progress = 100.0
            existing_image.histogram_clip = result.enhancement_params['histogram_clip']
            existing_image.clahe_clip = result.enhancement_params['clahe_clip']
            existing_image.face_detected = result.face_detected
            existing_image.processed_at = datetime.utcnow()
            existing_image.updated_at = datetime.utcnow()
            image = existing_image
        else:
            # Create new image record
            # Store enhanced_path as relative to static file serving (e.g., "output/image.jpg")
            image = Image(
                filename=enhanced_path.name,
                original_path=str(analysed_path),
                enhanced_path=f"output/{enhanced_path.name}",
                width=result.original_size[0],
                height=result.original_size[1],
                file_size=enhanced_path.stat().st_size,
                status="complete",
                stage="tagging",
                progress=100.0,
                histogram_clip=result.enhancement_params['histogram_clip'],
                clahe_clip=result.enhancement_params['clahe_clip'],
                face_detected=result.face_detected,
                processed_at=datetime.utcnow()
            )
            session.add(image)
            await session.flush()  # Get image.id

            # Create or update metadata record (upsert)
            result = await session.execute(
                select(ImageMetadata).where(ImageMetadata.image_id == image.id)
            )
            metadata = result.scalar_one_or_none()

            if metadata is None:
                # Create new metadata
                metadata = ImageMetadata(
                    image_id=image.id,
                    rotation=0  # TODO: Add rotation detection
                )
                session.add(metadata)
            else:
                # Update existing metadata if needed
                metadata.rotation = 0

            # Create or update embedding record (upsert)
            result_embed = await session.execute(
                select(ImageEmbedding).where(ImageEmbedding.image_id == image.id)
            )
            embedding = result_embed.scalar_one_or_none()

            if embedding is None:
                # Create new embedding
                embedding = ImageEmbedding(
                    image_id=image.id,
                    phash="",  # TODO: Calculate perceptual hash
                    face_count=0  # TODO: Count faces
                )
                session.add(embedding)
            else:
                # Update existing embedding
                embedding.phash = ""
                embedding.face_count = 0
                embedding.updated_at = datetime.utcnow()

        # Generate AI tags for the image (if tagger is available)
        if self.tagger is not None:
            try:
                # Check if image already has AI tags
                existing_tags_query = select(ImageTag).where(
                    ImageTag.image_id == image.id,
                    ImageTag.source == 'ai'
                )
                result_tags = await session.execute(existing_tags_query)
                existing_ai_tags = result_tags.scalars().all()

                # Only generate tags if none exist
                if len(existing_ai_tags) == 0:
                    logger.info(f"Generating AI tags for {enhanced_path.name}")
                    tags = await asyncio.to_thread(
                        self.tagger.generate_tags,
                        enhanced_path
                    )

                    # Save tags to database
                    for tag_info in tags:
                        tag_record = ImageTag(
                            image_id=image.id,
                            tag=tag_info['tag'],
                            source='ai',
                            confidence=tag_info['confidence'],
                            category=tag_info.get('category', 'general')
                        )
                        session.add(tag_record)

                    logger.info(f"Added {len(tags)} AI tags for {enhanced_path.name}")
                else:
                    logger.debug(f"Image {enhanced_path.name} already has {len(existing_ai_tags)} AI tags, skipping")
            except Exception as e:
                logger.error(f"Failed to generate tags: {e}", exc_info=True)

    async def _update_status(self,
                           stage: str,
                           progress: float,
                           error: Optional[str] = None):
        """
        Update current processing status and notify via callback

        Args:
            stage: Current processing stage
            progress: Progress percentage (0-100)
            error: Error message if any
        """
        self.current_stage = stage

        if self.status_callback:
            # Send full stats with nested structure for consistency
            stats = self.get_stats()
            # Update progress from current operation
            stats['current']['progress'] = progress
            if error:
                stats['current']['error'] = error
            await self.status_callback(stats)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current pipeline statistics

        Returns detailed statistics for monitoring UI
        """
        # Count files in each stage (across all input directories)
        input_count = 0
        for input_dir in settings.get_input_directories():
            input_count += sum(1 for _ in input_dir.rglob("*.tif*"))

        # Count analysed files that HAVEN'T been enhanced yet
        analysed_count = 0
        for analysed_file in settings.analysed_dir.rglob("*.tif*"):
            # Check if enhanced version exists
            output_file = settings.output_dir / f"{analysed_file.stem}.jpg"
            if not output_file.exists():
                analysed_count += 1

        output_count = sum(1 for _ in settings.output_dir.rglob("*.jpg"))

        # Calculate processing rate
        if self.stats['processing_times']:
            avg_time = sum(self.stats['processing_times']) / len(self.stats['processing_times'])
            pictures_per_hour = 3600 / avg_time if avg_time > 0 else 0
        else:
            avg_time = 0
            pictures_per_hour = 0

        # Calculate ETA
        total_pending = input_count + analysed_count
        if total_pending > 0 and avg_time > 0:
            eta_seconds = total_pending * avg_time
            eta_minutes = int(eta_seconds / 60)
        else:
            eta_minutes = 0

        # Session duration
        if self.stats['start_time']:
            duration_seconds = (datetime.utcnow() - self.stats['start_time']).total_seconds()
            duration_hours = duration_seconds / 3600
        else:
            duration_hours = 0

        # Generate hourly timeline for last 48 hours
        from datetime import timedelta
        now = datetime.utcnow()
        hourly_timeline = []
        for i in range(48):
            hour_dt = now - timedelta(hours=47 - i)
            hour_key = hour_dt.strftime('%Y-%m-%d %H:00')
            hour_label = hour_dt.strftime('%H:00')  # Just time for display
            count = self.stats['hourly_counts'].get(hour_key, 0)
            hourly_timeline.append({
                'hour': hour_label,
                'timestamp': hour_key,
                'count': count
            })

        # Calculate processing trend
        processing_trend = 'stable'
        if len(self.stats['processing_times']) >= 10:
            recent_avg = sum(self.stats['processing_times'][-5:]) / 5
            overall_avg = sum(self.stats['processing_times']) / len(self.stats['processing_times'])
            if recent_avg > overall_avg * 1.3:
                processing_trend = 'degrading'
            elif recent_avg < overall_avg * 0.7:
                processing_trend = 'accelerating'

        # Anomaly detection
        alerts = []

        # Stall detection: No processing for 15+ minutes
        if self.stats['processing_times'] and not self.is_processing:
            # Check if we have pending work but aren't processing
            if total_pending > 0:
                alerts.append({
                    'type': 'stall_warning',
                    'severity': 'warning',
                    'message': f'Pipeline idle with {total_pending} pending files',
                    'timestamp': datetime.utcnow().isoformat()
                })

        # Degradation warning
        if processing_trend == 'degrading':
            alerts.append({
                'type': 'performance_degradation',
                'severity': 'info',
                'message': 'Processing speed has slowed down',
                'timestamp': datetime.utcnow().isoformat()
            })

        # Error alerts
        if self.stats['error_count'] > 0:
            total_attempts = self.stats['processed_count'] + self.stats['error_count']

            if total_attempts > 0:
                error_rate = self.stats['error_count'] / total_attempts

                # High error rate (>10%)
                if error_rate > 0.1:
                    alerts.append({
                        'type': 'high_error_rate',
                        'severity': 'error',
                        'message': f'High error rate: {self.stats["error_count"]} errors out of {total_attempts} files ({int(error_rate * 100)}%)',
                        'timestamp': datetime.utcnow().isoformat()
                    })

            # Alert if only errors, no successes
            if self.stats['processed_count'] == 0:
                alerts.append({
                    'type': 'all_errors',
                    'severity': 'error',
                    'message': f'{self.stats["error_count"]} file(s) failed with errors. Check error log below.',
                    'timestamp': datetime.utcnow().isoformat()
                })

        # Get tag statistics (use cached value to avoid event loop conflicts)
        # Tag stats are updated by the REST API endpoint and cached here
        tag_stats = getattr(self, '_cached_tag_stats', {
            'ai_tags': [],
            'user_tags': [],
            'total_tags': 0,
            'total_images_tagged': 0
        })

        return {
            'current': {
                'is_processing': self.is_processing,
                'current_file': self.current_file,
                'current_stage': self.current_stage,
                'progress': 0  # Set by _update_status
            },
            'pipeline': {
                'input_queue': input_count,
                'analysed_queue': analysed_count,
                'completed_total': output_count,
                'completed_session': self.stats['processed_count']
            },
            'performance': {
                'pictures_per_hour': round(pictures_per_hour, 1),
                'avg_time_per_image': round(avg_time, 1),
                'eta_minutes': eta_minutes,
                'processing_trend': processing_trend
            },
            'history': {
                'session_duration_hours': round(duration_hours, 2),
                'error_count': self.stats['error_count'],
                'hourly_timeline': hourly_timeline,  # Last 48 hours of processing counts
                'error_log': self.stats['error_log']  # Recent errors with details
            },
            'alerts': alerts,
            'tags': tag_stats  # Include tag statistics
        }
