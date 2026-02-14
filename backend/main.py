"""
DiaBay - FastAPI Application
Main entry point for the web server
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db.database import init_db, get_db, AsyncSessionLocal
from core.pipeline import ProcessingPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global pipeline instance
pipeline: ProcessingPipeline = None

# WebSocket connections for real-time updates
active_connections: list[WebSocket] = []

# Global progress tracking for duplicate detection
duplicate_scan_progress = {
    'is_scanning': False,
    'current': 0,
    'total': 0,
    'percent': 0,
    'message': ''
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("Starting DiaBay...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create pipeline with WebSocket callback
    global pipeline
    pipeline = ProcessingPipeline(
        db_session_factory=AsyncSessionLocal,
        status_callback=broadcast_status
    )

    # Start pipeline
    await pipeline.start()

    yield

    # Shutdown
    logger.info("Shutting down DiaBay...")
    if pipeline:
        await pipeline.stop()


# Create FastAPI app
app = FastAPI(
    title="DiaBay",
    description="Analog Slide Digitization & Enhancement System",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving images (skip in CI/test environments)
import os
if not (os.getenv("CI") or os.getenv("PYTEST_CURRENT_TEST")):
    # Ensure directories exist before mounting
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.analysed_dir.mkdir(parents=True, exist_ok=True)
    settings.input_dir.mkdir(parents=True, exist_ok=True)

    app.mount("/output", StaticFiles(directory=str(settings.output_dir)), name="output")

    # Create and mount thumbnails directory
    thumbnail_dir = settings.output_dir.parent / "thumbnails"
    thumbnail_dir.mkdir(exist_ok=True)
    app.mount("/thumbnails", StaticFiles(directory=str(thumbnail_dir)), name="thumbnails")

    # Mount analysed directory for original TIFF files
    app.mount("/analysed", StaticFiles(directory=str(settings.analysed_dir)), name="analysed")

    # Mount input directory for raw TIFF files
    app.mount("/input", StaticFiles(directory=str(settings.input_dir)), name="input")

    # Mount previews directory for downscaled original previews
    preview_dir = settings.output_dir.parent / "previews"
    preview_dir.mkdir(exist_ok=True)
    app.mount("/previews", StaticFiles(directory=str(preview_dir)), name="previews")

    # Mount temp_previews directory for preset comparison previews
    temp_preview_dir = settings.output_dir.parent / "temp_previews"
    temp_preview_dir.mkdir(exist_ok=True)
    app.mount("/temp_previews", StaticFiles(directory=str(temp_preview_dir)), name="temp_previews")


# ============================================================================
# WebSocket for Real-Time Monitoring
# ============================================================================

async def broadcast_status(status: dict):
    """Broadcast status update to all connected WebSocket clients"""
    for connection in active_connections[:]:  # Copy list to avoid modification during iteration
        try:
            await connection.send_json(status)
        except Exception:
            # Connection closed, remove it
            active_connections.remove(connection)


@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """
    WebSocket endpoint for real-time processing status updates

    Clients connect here to receive live updates about:
    - Current file being processed
    - Processing stage and progress
    - Pipeline statistics
    - Errors and alerts
    """
    await websocket.accept()
    active_connections.append(websocket)

    try:
        # Send initial status
        if pipeline:
            stats = pipeline.get_stats()
            await websocket.send_json(stats)

        # Keep connection alive and send periodic updates
        while True:
            # Wait for incoming messages (heartbeat/ping)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                # Client sent heartbeat, respond with current stats
                if pipeline:
                    stats = pipeline.get_stats()
                    await websocket.send_json(stats)
            except asyncio.TimeoutError:
                # No message received, send periodic update anyway
                if pipeline:
                    stats = pipeline.get_stats()
                    await websocket.send_json(stats)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.post("/api/maintenance/cleanup-orphaned")
async def cleanup_orphaned_records(db: AsyncSession = Depends(get_db)):
    """
    Clean up orphaned database records for images that no longer have files.

    Removes database entries where:
    - Enhanced image file is missing
    - Thumbnail file is missing

    Returns count of removed records.
    """
    from sqlalchemy import select
    from db.models import Image
    from pathlib import Path

    result = await db.execute(select(Image))
    images = result.scalars().all()

    removed_count = 0
    removed_filenames = []

    for image in images:
        enhanced_path = settings.output_dir / image.filename
        thumbnail_path = (settings.output_dir.parent / "thumbnails") / image.filename

        # Check if files exist
        enhanced_exists = enhanced_path.exists()
        thumbnail_exists = thumbnail_path.exists()

        # If either file is missing, remove the record
        if not enhanced_exists or not thumbnail_exists:
            removed_filenames.append(image.filename)
            await db.delete(image)  # Cascades to tags, metadata, embeddings
            removed_count += 1
            logger.info(f"Removed orphaned record: {image.filename} (enhanced={enhanced_exists}, thumb={thumbnail_exists})")

    await db.commit()

    return {
        'removed_count': removed_count,
        'removed_filenames': removed_filenames,
        'message': f'Successfully removed {removed_count} orphaned records'
    }


@app.post("/api/maintenance/retag-all")
async def retag_all_images(db: AsyncSession = Depends(get_db)):
    """
    Regenerate AI tags for all existing images using the current tagger.

    This is useful when:
    - The tagging algorithm has been updated
    - Scene labels have been changed
    - You want to refresh all AI tags

    Removes existing AI tags and generates new ones.
    """
    if not pipeline or not pipeline.tagger:
        return {"error": "Tagger not initialized"}

    from sqlalchemy import select, delete
    from db.models import Image, ImageTag
    from pathlib import Path
    import asyncio

    # Get all complete images
    result = await db.execute(
        select(Image).where(Image.status == 'complete')
    )
    images = result.scalars().all()

    retagged_count = 0
    errors = []

    for image in images:
        try:
            # Delete existing AI tags
            await db.execute(
                delete(ImageTag).where(
                    ImageTag.image_id == image.id,
                    ImageTag.source == 'ai'
                )
            )

            # Generate new tags
            enhanced_path = settings.output_dir / image.filename
            if enhanced_path.exists():
                logger.info(f"Retagging {image.filename}...")
                tags = await asyncio.to_thread(
                    pipeline.tagger.generate_tags,
                    enhanced_path
                )

                # Save new tags
                for tag_info in tags:
                    tag_record = ImageTag(
                        image_id=image.id,
                        tag=tag_info['tag'],
                        source='ai',
                        confidence=tag_info['confidence'],
                        category=tag_info.get('category', 'general')
                    )
                    db.add(tag_record)

                retagged_count += 1
                logger.info(f"Added {len(tags)} new AI tags for {image.filename}")
            else:
                errors.append(f"{image.filename}: Enhanced image not found")

        except Exception as e:
            logger.error(f"Error retagging {image.filename}: {e}")
            errors.append(f"{image.filename}: {str(e)}")

    await db.commit()

    return {
        'retagged_count': retagged_count,
        'total_images': len(images),
        'errors': errors,
        'message': f'Successfully retagged {retagged_count} images with new scene-focused AI tags'
    }


@app.get("/api")
async def api_root():
    """API root - health check"""
    return {
        "name": "DiaBay",
        "version": "3.0.0",
        "status": "running",
        "pipeline_active": pipeline is not None and pipeline.watcher is not None
    }


@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Get current pipeline statistics

    Returns detailed statistics for monitoring:
    - Current processing state
    - Pipeline stage counts
    - Performance metrics (rate, ETA)
    - Session history
    - Tag statistics
    """
    if not pipeline:
        return {"error": "Pipeline not initialized"}

    stats = pipeline.get_stats()

    # Add tag statistics
    try:
        from sqlalchemy import select, func
        from db.models import ImageTag, Image

        # Get tag counts for all processed images
        query = select(
            ImageTag.tag,
            ImageTag.source,
            func.count(ImageTag.image_id).label('count')
        ).join(
            Image, ImageTag.image_id == Image.id
        ).where(
            Image.status == 'complete'
        ).group_by(
            ImageTag.tag, ImageTag.source
        ).order_by(
            func.count(ImageTag.image_id).desc()
        )

        result = await db.execute(query)
        tag_rows = result.all()

        # Organize by source (ai vs user)
        tag_stats = {
            'ai_tags': [],
            'user_tags': [],
            'total_tags': 0,
            'total_images_tagged': 0
        }

        for row in tag_rows:
            tag_info = {
                'tag': row.tag,
                'count': row.count
            }

            if row.source == 'ai':
                tag_stats['ai_tags'].append(tag_info)
            else:
                tag_stats['user_tags'].append(tag_info)

            tag_stats['total_tags'] += 1

        # Count unique images with tags
        count_query = select(func.count(func.distinct(ImageTag.image_id))).join(
            Image, ImageTag.image_id == Image.id
        ).where(
            Image.status == 'complete'
        )
        count_result = await db.execute(count_query)
        tag_stats['total_images_tagged'] = count_result.scalar() or 0

        stats['tags'] = tag_stats

        # Cache tag stats in pipeline for WebSocket updates
        await pipeline.update_tag_stats_cache(tag_stats)

    except Exception as e:
        logger.error(f"Failed to get tag statistics: {e}")
        stats['tags'] = {
            'ai_tags': [],
            'user_tags': [],
            'total_tags': 0,
            'total_images_tagged': 0
        }

        # Cache empty stats
        await pipeline.update_tag_stats_cache(stats['tags'])

    return stats


def generate_thumbnail(image_filename: str, output_dir: Path) -> bool:
    """Generate thumbnail for an image if it doesn't exist"""
    import cv2

    thumbnail_dir = output_dir.parent / "thumbnails"
    thumbnail_dir.mkdir(exist_ok=True)
    thumbnail_path = thumbnail_dir / image_filename

    # Skip if thumbnail already exists
    if thumbnail_path.exists():
        return True

    # Load original image
    original_path = output_dir / image_filename
    if not original_path.exists():
        return False

    try:
        img = cv2.imread(str(original_path))
        if img is None:
            return False

        # Resize to 400px on longest side
        height, width = img.shape[:2]
        max_size = 400
        if height > width:
            new_height = max_size
            new_width = int(width * (max_size / height))
        else:
            new_width = max_size
            new_height = int(height * (max_size / width))

        thumbnail = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Save thumbnail with high quality
        cv2.imwrite(str(thumbnail_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return True
    except Exception as e:
        logger.error(f"Failed to generate thumbnail for {image_filename}: {e}")
        return False


def generate_original_preview(original_tiff_path: Path) -> tuple[bool, str]:
    """
    Generate a preview JPEG from original TIFF for web viewing
    Returns (success, preview_url)

    Instead of serving 100MB TIFFs, generate smaller JPEG previews
    (2000px max width, 90% quality) for much faster loading
    """
    import cv2

    if not original_tiff_path.exists():
        return False, ""

    # Create previews directory
    preview_dir = settings.output_dir.parent / "previews"
    preview_dir.mkdir(exist_ok=True)

    # Convert TIFF filename to JPEG
    preview_filename = original_tiff_path.stem + "_preview.jpg"
    preview_path = preview_dir / preview_filename

    # Skip if preview already exists
    if preview_path.exists():
        return True, f"/previews/{preview_filename}"

    try:
        # Load TIFF (cv2 supports 16-bit TIFFs)
        img = cv2.imread(str(original_tiff_path), cv2.IMREAD_UNCHANGED)
        if img is None:
            logger.error(f"Failed to load TIFF: {original_tiff_path}")
            return False, ""

        # Convert 16-bit to 8-bit if necessary
        if img.dtype == 'uint16':
            # Use percentile-based conversion for better dynamic range
            p_low, p_high = 0.1, 99.9
            low = img.min()  # Or use np.percentile(img, p_low) for clipping
            high = img.max()  # Or use np.percentile(img, p_high)

            if high > low:
                img = ((img.astype(float) - low) / (high - low) * 255).clip(0, 255).astype('uint8')
            else:
                img = (img / 256).astype('uint8')

        # Resize to 2000px on longest side for preview
        height, width = img.shape[:2]
        max_size = 2000
        if height > max_size or width > max_size:
            if height > width:
                new_height = max_size
                new_width = int(width * (max_size / height))
            else:
                new_width = max_size
                new_height = int(height * (max_size / width))

            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Save as JPEG with high quality
        cv2.imwrite(str(preview_path), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        logger.info(f"Generated preview for {original_tiff_path.name}")
        return True, f"/previews/{preview_filename}"

    except Exception as e:
        logger.error(f"Failed to generate preview for {original_tiff_path}: {e}")
        return False, ""


@app.get("/api/images")
async def list_images(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    List all processed images with metadata

    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum records to return
    """
    from sqlalchemy import select
    from db.models import Image, ImageTag

    # Query images
    query = select(Image).offset(skip).limit(limit).order_by(Image.created_at.desc())
    result = await db.execute(query)
    images = result.scalars().all()

    # Check file integrity and trigger recovery for missing files (non-blocking)
    import asyncio
    for img in images:
        asyncio.create_task(check_and_recover_missing_files(img, db))

    # Generate thumbnails for images that don't have them (async)
    await asyncio.gather(*[
        asyncio.to_thread(generate_thumbnail, img.filename, settings.output_dir)
        for img in images
    ], return_exceptions=True)  # Don't fail if one thumbnail fails

    # Format response with thumbnail URLs
    return {
        "total": len(images),
        "images": [
            {
                "id": img.id,
                "filename": img.filename,
                "enhanced_path": f"/output/{img.filename}",  # Serve via static files mount
                "thumbnail_url": f"/thumbnails/{img.filename}",  # Thumbnails served as static files
                "width": img.width,
                "height": img.height,
                "status": img.status,
                "quality_score": None,  # TODO: Store quality score
                "created_at": img.created_at.isoformat(),
                "processed_at": img.processed_at.isoformat() if img.processed_at else None
            }
            for img in images
        ]
    }


async def check_and_recover_missing_files(image, db: AsyncSession):
    """
    Check if enhanced image and thumbnail exist. If missing, trigger reprocessing.

    Args:
        image: Image database record
        db: Database session

    Returns:
        True if files exist or were recovered, False if recovery failed
    """
    enhanced_path = settings.output_dir / image.filename
    thumbnail_dir = settings.output_dir.parent / "thumbnails"
    thumbnail_path = thumbnail_dir / image.filename

    files_missing = []
    if not enhanced_path.exists():
        files_missing.append("enhanced image")
    if not thumbnail_path.exists():
        files_missing.append("thumbnail")

    if not files_missing:
        return True  # All files present

    logger.warning(f"Missing files for {image.filename}: {', '.join(files_missing)}")

    # Check if we have the original TIFF to reprocess from
    if not image.original_path:
        logger.error(f"Cannot recover {image.filename}: No original path recorded")
        return False

    original_path = settings.analysed_dir / Path(image.original_path).name
    if not original_path.exists():
        logger.error(f"Cannot recover {image.filename}: Original TIFF not found at {original_path}")
        return False

    # Trigger reprocessing
    logger.info(f"Triggering automatic reprocessing for {image.filename}")
    try:
        # Queue reprocessing task (don't block the response)
        import asyncio
        asyncio.create_task(pipeline.process_analysed_file(original_path))
        return True
    except Exception as e:
        logger.error(f"Failed to trigger reprocessing for {image.filename}: {e}")
        return False


@app.get("/api/images/{image_id}")
async def get_image(image_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed information about a specific image"""
    from sqlalchemy import select
    from db.models import Image, ImageTag, ImageMetadata

    # Get image
    query = select(Image).where(Image.id == image_id)
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        return {"error": "Image not found"}

    # Check file integrity and auto-recover if missing
    await check_and_recover_missing_files(image, db)

    # Get tags
    tag_query = select(ImageTag).where(ImageTag.image_id == image_id)
    tag_result = await db.execute(tag_query)
    tags = tag_result.scalars().all()

    # Generate preview for original TIFF if needed
    original_preview_url = None
    if image.original_path:
        original_full_path = settings.analysed_dir / Path(image.original_path).name
        if original_full_path.suffix.lower() in ['.tif', '.tiff']:
            success, preview_url = generate_original_preview(original_full_path)
            if success:
                original_preview_url = preview_url

    return {
        "id": image.id,
        "filename": image.filename,
        "original_path": image.original_path,
        "original_preview_url": original_preview_url,  # NEW: Preview URL for TIFF originals
        "enhanced_path": image.enhanced_path,
        "width": image.width,
        "height": image.height,
        "status": image.status,
        "enhancement_params": {
            "histogram_clip": image.histogram_clip,
            "clahe_clip": image.clahe_clip,
            "face_detected": image.face_detected
        },
        "tags": [
            {
                "tag": tag.tag,
                "source": tag.source,
                "confidence": tag.confidence,
                "category": tag.category
            }
            for tag in tags
        ],
        "created_at": image.created_at.isoformat(),
        "processed_at": image.processed_at.isoformat() if image.processed_at else None
    }


@app.get("/api/images/{image_id}/thumbnail")
async def get_thumbnail(image_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get thumbnail URL for an image (generates if doesn't exist)

    Args:
        image_id: ID of image

    Returns:
        {"thumbnail_url": "/thumbnails/image_name.jpg"}
    """
    from sqlalchemy import select
    from db.models import Image
    import cv2
    from pathlib import Path

    # Get image from database
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        return {"error": "Image not found"}

    # Thumbnail directory
    thumbnail_dir = settings.output_dir.parent / "thumbnails"
    thumbnail_dir.mkdir(exist_ok=True)

    # Thumbnail path (same name as original)
    thumbnail_path = thumbnail_dir / image.filename

    # Generate thumbnail if it doesn't exist
    if not thumbnail_path.exists():
        # Load original image
        original_path = settings.output_dir / image.filename
        if not original_path.exists():
            return {"error": "Original image not found"}

        img = cv2.imread(str(original_path))
        if img is None:
            return {"error": "Failed to load image"}

        # Resize to 400px on longest side
        height, width = img.shape[:2]
        max_size = 400
        if height > width:
            new_height = max_size
            new_width = int(width * (max_size / height))
        else:
            new_width = max_size
            new_height = int(height * (max_size / width))

        thumbnail = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Save thumbnail with high quality
        cv2.imwrite(str(thumbnail_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])

    return {"thumbnail_url": f"/thumbnails/{image.filename}"}


@app.delete("/api/images/{image_id}")
async def delete_image(image_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete an image and its associated files

    Args:
        image_id: ID of image to delete

    Returns:
        Success message or error
    """
    from sqlalchemy import select, delete
    from db.models import Image, ImageTag
    import os

    # Get image from database
    query = select(Image).where(Image.id == image_id)
    result = await db.execute(query)
    image = result.scalar_one_or_none()

    if not image:
        return {"error": "Image not found"}, 404

    # Delete physical files
    files_to_delete = []

    # Enhanced image (required)
    enhanced_path = settings.output_dir / image.filename
    if enhanced_path.exists():
        files_to_delete.append(enhanced_path)

    # Thumbnail
    thumbnail_path = settings.output_dir.parent / "thumbnails" / image.filename
    if thumbnail_path.exists():
        files_to_delete.append(thumbnail_path)

    # Preview (for original TIFF)
    if image.original_path:
        preview_filename = Path(image.original_path).stem + "_preview.jpg"
        preview_path = settings.output_dir.parent / "previews" / preview_filename
        if preview_path.exists():
            files_to_delete.append(preview_path)

    # Delete files
    deleted_count = 0
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            deleted_count += 1
            logger.info(f"Deleted file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete {file_path}: {e}")

    # Delete associated tags
    await db.execute(delete(ImageTag).where(ImageTag.image_id == image_id))

    # Delete database record
    await db.execute(delete(Image).where(Image.id == image_id))
    await db.commit()

    logger.info(f"Deleted image {image_id} ({image.filename}) and {deleted_count} files")

    # Broadcast deletion to all connected WebSocket clients
    await broadcast_status({
        "type": "image_deleted",
        "image_id": image_id,
        "filename": image.filename
    })

    return {
        "success": True,
        "message": f"Deleted {image.filename}",
        "files_deleted": deleted_count
    }


@app.post("/api/images/{image_id}/tags")
async def add_tag(
    image_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a tag to an image

    Args:
        image_id: ID of image
        request: {"tag": "tag_name", "category": "scene|era|film", "confidence": 1.0}

    Returns:
        Success message or error
    """
    from sqlalchemy import select
    from db.models import Image, ImageTag

    # Validate image exists
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Extract tag data from request
    tag_value = request.get("tag")
    category = request.get("category", "user")
    confidence = request.get("confidence", 1.0)

    if not tag_value:
        raise HTTPException(status_code=400, detail="Tag value is required")

    # Check if tag already exists
    tag_query = select(ImageTag).where(
        ImageTag.image_id == image_id,
        ImageTag.tag == tag_value
    )
    existing_tag = await db.execute(tag_query)
    if existing_tag.scalar_one_or_none():
        return {"message": "Tag already exists", "tag": tag_value}

    # Create new tag
    new_tag = ImageTag(
        image_id=image_id,
        tag=tag_value,
        source="user",  # User-added tags
        confidence=confidence,
        category=category
    )

    db.add(new_tag)
    await db.commit()

    logger.info(f"Added tag '{tag_value}' to image {image_id}")

    return {
        "success": True,
        "message": f"Tag '{tag_value}' added",
        "tag": {
            "tag": tag_value,
            "category": category,
            "confidence": confidence
        }
    }


@app.delete("/api/images/{image_id}/tags/{tag}")
async def remove_tag(
    image_id: int,
    tag: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a tag from an image

    Args:
        image_id: ID of image
        tag: Tag value to remove (URL-encoded)

    Returns:
        Success message or error
    """
    from sqlalchemy import select, delete
    from db.models import Image, ImageTag
    from urllib.parse import unquote

    # URL decode the tag
    tag = unquote(tag)

    # Validate image exists
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete the tag
    delete_stmt = delete(ImageTag).where(
        ImageTag.image_id == image_id,
        ImageTag.tag == tag
    )
    result = await db.execute(delete_stmt)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tag not found")

    logger.info(f"Removed tag '{tag}' from image {image_id}")

    return {
        "success": True,
        "message": f"Tag '{tag}' removed"
    }


@app.post("/api/images/{image_id}/rotate")
async def rotate_image(
    image_id: int,
    request_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Rotate an image by specified degrees

    Args:
        image_id: ID of image to rotate
        request_data: Request body containing {"degrees": 90, 180, or 270}

    Returns:
        Success message or error
    """
    from sqlalchemy import select
    from db.models import Image
    import cv2

    # Get image from database
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Get rotation degrees from request (default to 90 if not provided)
    degrees = request_data.get('degrees', 90)
    if degrees not in [90, 180, 270]:
        raise HTTPException(status_code=400, detail="Degrees must be 90, 180, or 270")

    # Load enhanced image
    enhanced_path = settings.output_dir / image.filename
    if not enhanced_path.exists():
        raise HTTPException(status_code=404, detail="Enhanced image file not found")

    try:
        # Load image
        logger.info(f"Loading image from: {enhanced_path}")
        img = cv2.imread(str(enhanced_path))
        if img is None:
            raise HTTPException(status_code=500, detail=f"Failed to load image from {enhanced_path}")

        original_shape = img.shape
        logger.info(f"Original image shape: {original_shape}")

        # Rotate
        if degrees == 90:
            rotated = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif degrees == 180:
            rotated = cv2.rotate(img, cv2.ROTATE_180)
        elif degrees == 270:
            rotated = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid degrees: {degrees}")

        logger.info(f"Rotated image shape: {rotated.shape}")

        # Save rotated image with verification
        logger.info(f"Saving rotated image to: {enhanced_path}")
        write_success = cv2.imwrite(str(enhanced_path), rotated, [cv2.IMWRITE_JPEG_QUALITY, 95])

        if not write_success:
            raise HTTPException(status_code=500, detail=f"Failed to save rotated image to {enhanced_path}")

        # Verify the file exists and is readable
        if not enhanced_path.exists():
            raise HTTPException(status_code=500, detail="Rotated image file does not exist after save")

        # Verify we can read it back
        verify_img = cv2.imread(str(enhanced_path))
        if verify_img is None:
            raise HTTPException(status_code=500, detail="Cannot read back saved rotated image")

        logger.info(f"Verified rotated image saved successfully, shape: {verify_img.shape}")

        # Update dimensions in database
        height, width = rotated.shape[:2]
        image.width = width
        image.height = height
        await db.commit()

        # Regenerate thumbnail
        try:
            thumbnail_dir = settings.output_dir.parent / "thumbnails"
            thumbnail_path = thumbnail_dir / image.filename
            if thumbnail_path.exists():
                thumbnail_path.unlink()  # Delete old thumbnail
            generate_thumbnail(image.filename, settings.output_dir)
            logger.info(f"Regenerated thumbnail for {image.filename}")
        except Exception as thumb_error:
            # Don't fail the whole operation if thumbnail generation fails
            logger.error(f"Failed to regenerate thumbnail: {thumb_error}")

        logger.info(f"Successfully rotated image {image_id} by {degrees} degrees")

        return {
            "success": True,
            "message": f"Image rotated {degrees}° clockwise",
            "width": width,
            "height": height
        }

    except Exception as e:
        logger.error(f"Failed to rotate image {image_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rotate image: {str(e)}")


@app.post("/api/images/{image_id}/reprocess")
async def reprocess_image(
    image_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocess an image with different enhancement preset

    Args:
        image_id: ID of image to reprocess
        request: {
            "preset": "gentle" | "balanced" | "aggressive" | "custom",
            "histogram_clip": 0.5,  # Optional for custom
            "clahe_clip": 1.5  # Optional for custom
        }

    Returns:
        Reprocessed image data
    """
    from sqlalchemy import select
    from db.models import Image
    from core.processor import ImageProcessor, EnhancementPreset
    import cv2

    # Get image from database
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Get original TIFF path
    if not image.original_path:
        raise HTTPException(status_code=400, detail="No original file available for reprocessing")

    original_path = settings.analysed_dir / Path(image.original_path).name
    if not original_path.exists():
        raise HTTPException(status_code=404, detail="Original file not found")

    # Get preset or custom parameters
    preset_name = request.get("preset", "balanced")

    # Define presets
    presets = {
        "gentle": {"histogram_clip": 0.3, "clahe_clip": 1.0},
        "balanced": {"histogram_clip": 0.5, "clahe_clip": 1.5},
        "aggressive": {"histogram_clip": 0.7, "clahe_clip": 2.0}
    }

    if preset_name in presets:
        params = presets[preset_name]
    elif preset_name == "custom":
        params = {
            "histogram_clip": request.get("histogram_clip", 0.5),
            "clahe_clip": request.get("clahe_clip", 1.5)
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid preset")

    try:
        # Create processor with new parameters
        processor = ImageProcessor(
            histogram_clip=params["histogram_clip"],
            clahe_clip=params["clahe_clip"],
            adaptive_grid=settings.adaptive_clahe_grid,
            face_detection=settings.enable_face_detection
        )

        # Load and process original image
        original_img = cv2.imread(str(original_path), cv2.IMREAD_UNCHANGED)
        if original_img is None:
            raise HTTPException(status_code=500, detail="Failed to load original image")

        # Process
        enhanced_img, metadata = processor.process(original_img)

        # Save enhanced image
        enhanced_path = settings.output_dir / image.filename
        cv2.imwrite(str(enhanced_path), enhanced_img, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # Update database
        image.histogram_clip = params["histogram_clip"]
        image.clahe_clip = params["clahe_clip"]
        image.face_detected = metadata.get("face_detected", False)
        await db.commit()

        # Regenerate thumbnail
        thumbnail_dir = settings.output_dir.parent / "thumbnails"
        thumbnail_path = thumbnail_dir / image.filename
        if thumbnail_path.exists():
            thumbnail_path.unlink()
        generate_thumbnail(image.filename, settings.output_dir)

        logger.info(f"Reprocessed image {image_id} with preset '{preset_name}'")

        return {
            "success": True,
            "message": f"Image reprocessed with {preset_name} preset",
            "preset": preset_name,
            "parameters": params,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"Failed to reprocess image {image_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reprocess: {str(e)}")


@app.post("/api/images/{image_id}/preview")
async def preview_presets(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate preview images for all presets without saving them.
    Returns temporary URLs for each preset preview.

    Args:
        image_id: ID of image to preview

    Returns:
        Dictionary with preview URLs for each preset
    """
    from sqlalchemy import select
    from db.models import Image
    from core.processor import ImageProcessor
    import cv2
    import tempfile
    import base64
    from io import BytesIO

    # Get image from database
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Get original TIFF path
    if not image.original_path:
        raise HTTPException(status_code=400, detail="No original file available")

    original_path = settings.analysed_dir / Path(image.original_path).name
    if not original_path.exists():
        raise HTTPException(status_code=404, detail="Original file not found")

    # Define presets
    presets = {
        "gentle": {"histogram_clip": 0.3, "clahe_clip": 1.0},
        "balanced": {"histogram_clip": 0.5, "clahe_clip": 1.5},
        "aggressive": {"histogram_clip": 0.7, "clahe_clip": 2.0}
    }

    try:
        # Load original image once
        original_img = cv2.imread(str(original_path), cv2.IMREAD_UNCHANGED)
        if original_img is None:
            raise HTTPException(status_code=500, detail="Failed to load original image")

        # Convert 16-bit to 8-bit if necessary
        if original_img.dtype == np.uint16:
            # Use percentile-based conversion (same as processor)
            p1, p99 = np.percentile(original_img, (0.1, 99.9))
            original_img = np.clip((original_img - p1) / (p99 - p1) * 255, 0, 255).astype(np.uint8)

        # Ensure BGR format
        if len(original_img.shape) == 2:  # Grayscale
            original_img = cv2.cvtColor(original_img, cv2.COLOR_GRAY2BGR)

        # Generate previews for each preset
        previews = {}

        for preset_name, params in presets.items():
            # Create processor with preset parameters
            processor = ImageProcessor(
                histogram_clip=params["histogram_clip"],
                clahe_clip=params["clahe_clip"],
                adaptive_grid=settings.adaptive_clahe_grid,
                face_detection=settings.enable_face_detection
            )

            # Process image using internal enhancement method
            enhanced_img = processor._enhance_image(original_img.copy())

            # Save to temporary file
            temp_dir = settings.output_dir.parent / "temp_previews"
            temp_dir.mkdir(exist_ok=True)

            preview_filename = f"{image.filename.rsplit('.', 1)[0]}_{preset_name}_preview.jpg"
            preview_path = temp_dir / preview_filename

            # Save as JPEG with quality 85 (smaller for preview)
            cv2.imwrite(str(preview_path), enhanced_img, [cv2.IMWRITE_JPEG_QUALITY, 85])

            # Return relative path that can be served
            previews[preset_name] = f"temp_previews/{preview_filename}"

        logger.info(f"Generated previews for image {image_id}")

        return {
            "success": True,
            "previews": previews,
            "current_preset": {
                "histogram_clip": image.histogram_clip,
                "clahe_clip": image.clahe_clip
            }
        }

    except Exception as e:
        logger.error(f"Failed to generate previews for image {image_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate previews: {str(e)}")


@app.post("/api/images/{image_id}/use-original")
async def use_original(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Revert to using original image (delete enhanced version).
    Marks the image as 'original_only' so it shows the original file.

    Args:
        image_id: ID of image

    Returns:
        Success message
    """
    from sqlalchemy import select
    from db.models import Image

    # Get image from database
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        # Delete enhanced file if it exists
        if image.enhanced_path:
            enhanced_path = settings.output_dir / image.filename
            if enhanced_path.exists():
                enhanced_path.unlink()
                logger.info(f"Deleted enhanced version: {enhanced_path}")

        # Delete thumbnail if it exists
        thumbnail_dir = settings.output_dir.parent / "thumbnails"
        thumbnail_path = thumbnail_dir / image.filename
        if thumbnail_path.exists():
            thumbnail_path.unlink()

        # Update database - mark as using original
        image.enhanced_path = None
        image.histogram_clip = None
        image.clahe_clip = None
        image.face_detected = None
        image.status = 'original_only'  # Custom status to indicate no enhancement
        await db.commit()

        # Generate thumbnail from original
        if image.original_path:
            original_path = settings.analysed_dir / Path(image.original_path).name
            if original_path.exists():
                # Generate thumbnail from original TIFF
                import cv2
                original_img = cv2.imread(str(original_path), cv2.IMREAD_UNCHANGED)
                if original_img is not None:
                    # Resize to thumbnail
                    height, width = original_img.shape[:2]
                    thumb_size = 200
                    if height > width:
                        new_height = thumb_size
                        new_width = int(width * thumb_size / height)
                    else:
                        new_width = thumb_size
                        new_height = int(height * thumb_size / width)

                    thumbnail = cv2.resize(original_img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                    thumbnail_path.parent.mkdir(exist_ok=True)
                    cv2.imwrite(str(thumbnail_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 80])

        logger.info(f"Reverted image {image_id} to original (deleted enhanced version)")

        return {
            "success": True,
            "message": "Reverted to original image",
            "status": "original_only"
        }

    except Exception as e:
        logger.error(f"Failed to revert image {image_id} to original: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to revert to original: {str(e)}")


@app.get("/api/duplicates")
async def find_duplicates(
    source: str = "output",
    threshold: float = 0.95,
    db: AsyncSession = Depends(get_db)
):
    """
    Find duplicate images

    Args:
        source: 'input' or 'output' - where to scan for duplicates
        threshold: Similarity threshold (0.0-1.0)
    """
    import sys
    from pathlib import Path
    # Import from parent directory's core module (not backend's core)
    root_dir = Path(__file__).parent.parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    from core.duplicates import DuplicateDetector
    from sqlalchemy import select
    from db.models import Image
    import uuid

    try:
        # Initialize detector (using default threshold 0.95)
        detector = DuplicateDetector(str(settings.output_dir))
        # Override threshold if different from default
        if threshold != 0.95:
            detector.threshold = threshold

        # Progress callback function
        def update_progress(current: int, total: int):
            duplicate_scan_progress['is_scanning'] = True
            duplicate_scan_progress['current'] = current
            duplicate_scan_progress['total'] = total
            duplicate_scan_progress['percent'] = int((current / total * 100) if total > 0 else 0)
            duplicate_scan_progress['message'] = f"Scanning {current} of {total} images..."

        # Reset progress
        duplicate_scan_progress['is_scanning'] = True
        duplicate_scan_progress['current'] = 0
        duplicate_scan_progress['total'] = 0
        duplicate_scan_progress['percent'] = 0
        duplicate_scan_progress['message'] = 'Starting scan...'

        # Scan for duplicates
        logger.info(f"Scanning for duplicates in {source} with threshold {threshold}")
        duplicates = detector.scan_for_duplicates(progress_callback=update_progress)

        # Convert results to API format with image metadata from database
        groups = []

        for original_path, info in duplicates.items():
            # Get image IDs from database by filename
            group_images = []

            # Add original image
            original_filename = Path(original_path).name
            query = select(Image).where(Image.filename == original_filename)
            result = await db.execute(query)
            original_image = result.scalar_one_or_none()

            if original_image:
                group_images.append({
                    "id": original_image.id,
                    "filename": original_image.filename,
                    "enhanced_path": original_image.enhanced_path,
                    "thumbnail_url": f"/thumbnails/{original_image.filename}",
                    "width": original_image.width,
                    "height": original_image.height,
                    "status": original_image.status,
                    "created_at": original_image.created_at.isoformat(),
                })

            # Add duplicate images
            for dupe_info in info['duplicates']:
                dupe_path = dupe_info['path']
                dupe_filename = Path(dupe_path).name
                similarity = dupe_info['similarity']

                query = select(Image).where(Image.filename == dupe_filename)
                result = await db.execute(query)
                dupe_image = result.scalar_one_or_none()

                if dupe_image:
                    group_images.append({
                        "id": dupe_image.id,
                        "filename": dupe_image.filename,
                        "enhanced_path": dupe_image.enhanced_path,
                        "thumbnail_url": f"/thumbnails/{dupe_image.filename}",
                        "width": dupe_image.width,
                        "height": dupe_image.height,
                        "status": dupe_image.status,
                        "created_at": dupe_image.created_at.isoformat(),
                    })

            # Only create a group if there are actual duplicates (more than just the original)
            if len(group_images) > 1 and len(info['duplicates']) > 0:
                # Determine duplicate type based on similarity
                avg_similarity = sum(d['similarity'] for d in info['duplicates']) / len(info['duplicates'])
                if avg_similarity >= 0.98:
                    duplicate_type = "exact"
                elif avg_similarity >= 0.95:
                    duplicate_type = "near"
                else:
                    duplicate_type = "similar"

                groups.append({
                    "id": str(uuid.uuid4()),
                    "images": group_images,
                    "similarity": avg_similarity,
                    "type": duplicate_type,
                    "source": source
                })

        # Get statistics
        stats = detector.get_duplicate_stats(duplicates)
        total_duplicates = stats['total_duplicates']

        logger.info(f"Found {len(groups)} duplicate groups with {total_duplicates} duplicates")

        # Reset progress
        duplicate_scan_progress['is_scanning'] = False
        duplicate_scan_progress['percent'] = 100
        duplicate_scan_progress['message'] = 'Scan complete'

        return {
            "groups": groups,
            "total_duplicates": total_duplicates,
            "total_groups": len(groups),
            "potential_space_mb": stats.get('potential_space_mb', 0)
        }
    except Exception as e:
        logger.error(f"Error finding duplicates: {e}", exc_info=True)
        # Reset progress on error
        duplicate_scan_progress['is_scanning'] = False
        duplicate_scan_progress['message'] = f'Error: {str(e)}'
        return {
            "error": str(e),
            "groups": [],
            "total_duplicates": 0,
            "total_groups": 0
        }


@app.get("/api/duplicates/progress")
async def get_duplicate_scan_progress():
    """Get current progress of duplicate scanning"""
    return {
        "is_scanning": duplicate_scan_progress['is_scanning'],
        "current": duplicate_scan_progress['current'],
        "total": duplicate_scan_progress['total'],
        "percent": duplicate_scan_progress['percent'],
        "message": duplicate_scan_progress['message']
    }


# ============================================================================
# RESCAN & SYNC
# ============================================================================

@app.post("/api/rescan")
async def rescan_output_directory(
    write_tags_to_files: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Rescan output directory and sync with database
    - Find images in output directory not in database
    - Create database records for missing images
    - Generate missing thumbnails
    - Optionally write tags to image EXIF/IPTC metadata
    """
    from sqlalchemy import select
    from db.models import Image, ImageTag
    import cv2
    from datetime import datetime

    try:
        output_dir = settings.output_dir
        thumbnail_dir = output_dir.parent / "thumbnails"
        thumbnail_dir.mkdir(exist_ok=True)

        # Get all image files in output directory
        image_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff'}
        image_files = [f for f in output_dir.iterdir()
                      if f.is_file() and f.suffix.lower() in image_extensions]

        logger.info(f"Found {len(image_files)} images in output directory")

        # Get all filenames currently in database
        query = select(Image.filename)
        result = await db.execute(query)
        db_filenames = set(row[0] for row in result.fetchall())

        # Find images not in database
        missing_images = [f for f in image_files if f.name not in db_filenames]
        logger.info(f"Found {len(missing_images)} images not in database")

        added_count = 0
        thumbnail_count = 0
        tags_written_count = 0

        for image_path in missing_images:
            try:
                # Read image to get dimensions
                img = cv2.imread(str(image_path))
                if img is None:
                    logger.warning(f"Could not read image: {image_path.name}")
                    continue

                height, width = img.shape[:2]

                # Try to find original TIFF file in input directory
                # Convert JPG filename back to TIFF pattern (e.g., image_260204_093826.jpg -> image_260204_093826.tif)
                input_dir = settings.input_dir
                base_name = image_path.stem  # filename without extension
                original_path_found = None

                # Try different TIFF extensions
                for ext in ['.tif', '.tiff', '.TIF', '.TIFF']:
                    potential_original = input_dir / f"{base_name}{ext}"
                    if potential_original.exists():
                        original_path_found = str(potential_original)
                        break

                # If no original found, use enhanced path as placeholder
                if not original_path_found:
                    original_path_found = str(image_path)
                    logger.warning(f"Original TIFF not found for {image_path.name}, using enhanced path as placeholder")

                # Create database record
                new_image = Image(
                    filename=image_path.name,
                    original_path=original_path_found,
                    enhanced_path=str(image_path),
                    width=width,
                    height=height,
                    status="completed",
                    created_at=datetime.fromtimestamp(image_path.stat().st_ctime),
                    processed_at=datetime.now()
                )
                db.add(new_image)
                await db.flush()  # Get the ID

                added_count += 1
                logger.info(f"Added to database: {image_path.name}")

                # Generate thumbnail if missing
                thumbnail_path = thumbnail_dir / image_path.name
                if not thumbnail_path.exists():
                    try:
                        max_size = 400
                        h, w = img.shape[:2]
                        if h > max_size or w > max_size:
                            if h > w:
                                new_height = max_size
                                new_width = int(w * (max_size / h))
                            else:
                                new_width = max_size
                                new_height = int(h * (max_size / w))
                            thumbnail = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
                        else:
                            thumbnail = img

                        cv2.imwrite(str(thumbnail_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 85])
                        thumbnail_count += 1
                        logger.info(f"Generated thumbnail: {image_path.name}")
                    except Exception as thumb_err:
                        logger.error(f"Failed to generate thumbnail for {image_path.name}: {thumb_err}")

            except Exception as img_err:
                logger.error(f"Error processing {image_path.name}: {img_err}")
                await db.rollback()  # Rollback failed transaction
                continue

        # Commit all new records
        try:
            await db.commit()
        except Exception as commit_err:
            logger.error(f"Error committing changes: {commit_err}")
            await db.rollback()
            raise

        # Write tags to file metadata if requested
        if write_tags_to_files:
            # Get all images with tags (eagerly load tags relationship)
            from sqlalchemy.orm import selectinload
            query = select(Image).options(selectinload(Image.tags)).join(ImageTag, isouter=True)
            result = await db.execute(query)
            images_with_tags = result.scalars().unique().all()

            for image in images_with_tags:
                if image.tags:
                    try:
                        image_path = output_dir / image.filename
                        if image_path.exists():
                            tags = [tag.tag for tag in image.tags]
                            if await write_tags_to_image_metadata(image_path, tags):
                                tags_written_count += 1
                    except Exception as tag_err:
                        logger.error(f"Failed to write tags for {image.filename}: {tag_err}")

        logger.info(f"Rescan complete: {added_count} added, {thumbnail_count} thumbnails generated, {tags_written_count} files tagged")

        return {
            "success": True,
            "images_added": added_count,
            "thumbnails_generated": thumbnail_count,
            "tags_written": tags_written_count,
            "total_scanned": len(image_files),
            "already_in_db": len(db_filenames)
        }

    except Exception as e:
        logger.error(f"Error during rescan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def write_tags_to_image_metadata(image_path: Path, tags: list[str]) -> bool:
    """
    Write tags to image EXIF/IPTC metadata

    Args:
        image_path: Path to image file
        tags: List of tag strings

    Returns:
        True if successful, False otherwise
    """
    try:
        from PIL import Image as PILImage
        from PIL import ExifTags
        import piexif

        # Convert tags to comma-separated string
        keywords = ", ".join(tags)

        # Load image
        img = PILImage.open(image_path)

        # Get existing EXIF data or create new
        exif_dict = piexif.load(str(image_path)) if "exif" in img.info else {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}

        # Write keywords to IPTC Keywords field (piexif doesn't support IPTC directly)
        # Use XPKeywords (Windows) and ImageDescription for compatibility
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = keywords.encode('utf-16le')
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = keywords.encode('utf-8')

        # Convert back to bytes
        exif_bytes = piexif.dump(exif_dict)

        # Save image with new EXIF data
        img.save(str(image_path), exif=exif_bytes, quality=95)

        logger.debug(f"Wrote {len(tags)} tags to {image_path.name}")
        return True

    except ImportError:
        logger.warning("piexif not installed - cannot write tags to metadata. Install with: pip install piexif")
        return False
    except Exception as e:
        logger.error(f"Failed to write tags to {image_path.name}: {e}")
        return False


# ============================================================================
# Production Frontend Serving (Optional - for single-server deployment)
# ============================================================================

# Check if built frontend exists and serve it
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists() and frontend_dist.is_dir():
    logger.info(f"Production mode: Serving frontend from {frontend_dist}")

    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="frontend-assets")

    # Serve index.html for all other routes (SPA support)
    from fastapi.responses import FileResponse

    @app.get("/")
    async def serve_root():
        """Serve React frontend at root"""
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        else:
            raise HTTPException(status_code=404, detail="Frontend not built")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve React frontend for all non-API routes"""
        # Don't intercept API routes or static file routes
        if full_path.startswith(("api", "output", "thumbnails", "analysed", "input", "ws")):
            raise HTTPException(status_code=404, detail="Not found")

        # Serve index.html for all other routes (React Router will handle routing)
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        else:
            raise HTTPException(status_code=404, detail="Frontend not built")
else:
    logger.info("Development mode: Frontend NOT served from backend (use Vite dev server)")
    logger.info(f"  To enable production mode, build frontend: cd frontend && npm run build")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info"
    )
