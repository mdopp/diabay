"""
Test script for DiaBay pipeline
Tests the complete processing pipeline with sample images
"""
import asyncio
import sys
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from db.database import init_db, AsyncSessionLocal
from core.pipeline import ProcessingPipeline


async def test_pipeline():
    """Test the complete pipeline with sample images"""
    print("=" * 60)
    print("DiaBay Pipeline Test")
    print("=" * 60)

    # Setup test directories
    print("\n1. Setting up test directories...")
    settings.input_dir.mkdir(parents=True, exist_ok=True)
    settings.analysed_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"   ✓ Input: {settings.input_dir}")
    print(f"   ✓ Analysed: {settings.analysed_dir}")
    print(f"   ✓ Output: {settings.output_dir}")

    # Copy sample files to input
    print("\n2. Copying sample TIFF files to input...")
    samples_dir = Path("../../tests/samples")
    if samples_dir.exists():
        sample_files = list(samples_dir.glob("*.tif"))
        print(f"   Found {len(sample_files)} sample files")

        for sample in sample_files:
            dest = settings.input_dir / sample.name
            if not dest.exists():
                shutil.copy2(sample, dest)
                print(f"   ✓ Copied: {sample.name}")
    else:
        print(f"   ⚠ Sample directory not found: {samples_dir}")
        print("   Please ensure sample files are in tests/samples/")
        return

    # Initialize database
    print("\n3. Initializing database...")
    await init_db()
    print("   ✓ Database initialized")

    # Create pipeline
    print("\n4. Creating processing pipeline...")
    async def status_update(status):
        """Callback for status updates"""
        if status.get('current_file'):
            stage = status.get('current_stage', '')
            progress = status.get('progress', 0)
            print(f"   Processing: {status['current_file']} - {stage} ({progress}%)")

    pipeline = ProcessingPipeline(
        db_session_factory=AsyncSessionLocal,
        status_callback=status_update
    )
    print("   ✓ Pipeline created")

    # Start pipeline
    print("\n5. Starting pipeline...")
    await pipeline.start()
    print("   ✓ Pipeline started")

    # Wait for processing to complete
    print("\n6. Processing images...")
    print("   (This may take a few minutes for large TIFF files)")

    # Monitor progress
    while pipeline.is_processing or (
        sum(1 for _ in settings.input_dir.rglob("*.tif*")) > 0 or
        sum(1 for _ in settings.analysed_dir.rglob("*.tif*")) > 0
    ):
        await asyncio.sleep(2)

        stats = pipeline.get_stats()
        print(f"\n   Pipeline Status:")
        print(f"   - Input queue: {stats['pipeline']['input_queue']}")
        print(f"   - Analysed queue: {stats['pipeline']['analysed_queue']}")
        print(f"   - Completed: {stats['pipeline']['completed_session']}")
        print(f"   - Rate: {stats['performance']['pictures_per_hour']:.1f} pics/hour")

        if stats['pipeline']['input_queue'] == 0 and \
           stats['pipeline']['analysed_queue'] == 0 and \
           not pipeline.is_processing:
            break

    # Stop pipeline
    print("\n7. Stopping pipeline...")
    await pipeline.stop()
    print("   ✓ Pipeline stopped")

    # Show results
    print("\n8. Results:")
    output_files = list(settings.output_dir.glob("*.jpg"))
    print(f"   ✓ Generated {len(output_files)} enhanced JPEGs")

    for output_file in output_files:
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"      - {output_file.name} ({size_mb:.1f} MB)")

    # Final stats
    print("\n9. Final Statistics:")
    final_stats = pipeline.get_stats()
    print(f"   - Total processed: {final_stats['pipeline']['completed_session']}")
    print(f"   - Errors: {final_stats['history']['error_count']}")
    print(f"   - Session duration: {final_stats['history']['session_duration_hours']:.2f} hours")
    print(f"   - Average time per image: {final_stats['performance']['avg_time_per_image']:.1f}s")

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_pipeline())
