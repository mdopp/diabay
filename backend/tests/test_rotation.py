"""
Tests for image rotation functionality
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import cv2
import numpy as np
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import from parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.database import Base
from db.models import Image
from config import settings

# Test database
TEST_DB = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def test_db():
    """Create test database"""
    engine = create_async_engine(TEST_DB, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture(scope="function")
def temp_dirs_with_image():
    """Create temporary directories with test image"""
    temp_dir = Path(tempfile.mkdtemp())
    output_dir = temp_dir / "output"
    output_dir.mkdir()

    # Create test image with distinctive pattern to verify rotation
    img = np.zeros((200, 100, 3), dtype=np.uint8)
    # Top half blue, bottom half red
    img[:100, :] = (255, 0, 0)  # Blue (BGR format)
    img[100:, :] = (0, 0, 255)  # Red

    test_path = output_dir / "test_image.jpg"
    cv2.imwrite(str(test_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])

    # Verify image was saved correctly
    assert test_path.exists(), "Test image should be created"
    loaded = cv2.imread(str(test_path))
    assert loaded is not None, "Test image should be readable"

    yield {
        'base': temp_dir,
        'output': output_dir,
        'test_image': test_path,
        'test_img': img
    }

    # Cleanup
    shutil.rmtree(temp_dir)

class TestRotationFunctionality:
    """Tests for image rotation"""

    def test_rotate_90_clockwise(self, temp_dirs_with_image):
        """Test 90 degree clockwise rotation"""
        test_path = temp_dirs_with_image['test_image']
        original_img = cv2.imread(str(test_path))
        original_shape = original_img.shape

        # Rotate
        rotated = cv2.rotate(original_img, cv2.ROTATE_90_CLOCKWISE)

        # Save
        result = cv2.imwrite(str(test_path), rotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
        assert result, "cv2.imwrite should return True on success"

        # Verify file still exists
        assert test_path.exists(), "Image file should still exist after rotation"

        # Reload and verify
        reloaded = cv2.imread(str(test_path))
        assert reloaded is not None, "Rotated image should be readable"

        # Verify dimensions swapped
        assert reloaded.shape[0] == original_shape[1], f"Height should be {original_shape[1]}, got {reloaded.shape[0]}"
        assert reloaded.shape[1] == original_shape[0], f"Width should be {original_shape[0]}, got {reloaded.shape[1]}"

    def test_rotate_180(self, temp_dirs_with_image):
        """Test 180 degree rotation"""
        test_path = temp_dirs_with_image['test_image']
        original_img = cv2.imread(str(test_path))
        original_shape = original_img.shape

        # Rotate
        rotated = cv2.rotate(original_img, cv2.ROTATE_180)

        # Save
        result = cv2.imwrite(str(test_path), rotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
        assert result, "cv2.imwrite should return True on success"

        # Reload
        reloaded = cv2.imread(str(test_path))
        assert reloaded is not None, "Rotated image should be readable"

        # Dimensions should stay the same for 180 degree rotation
        assert reloaded.shape == original_shape, "Dimensions should not change for 180° rotation"

    def test_rotate_270_clockwise(self, temp_dirs_with_image):
        """Test 270 degree clockwise (90 counter-clockwise) rotation"""
        test_path = temp_dirs_with_image['test_image']
        original_img = cv2.imread(str(test_path))
        original_shape = original_img.shape

        # Rotate
        rotated = cv2.rotate(original_img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Save
        result = cv2.imwrite(str(test_path), rotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
        assert result, "cv2.imwrite should return True on success"

        # Reload
        reloaded = cv2.imread(str(test_path))
        assert reloaded is not None, "Rotated image should be readable"

        # Verify dimensions swapped
        assert reloaded.shape[0] == original_shape[1], "Height should match original width"
        assert reloaded.shape[1] == original_shape[0], "Width should match original height"

    def test_image_not_corrupted_after_rotation(self, temp_dirs_with_image):
        """Test that image data is not corrupted after rotation"""
        test_path = temp_dirs_with_image['test_image']

        # Get original file size
        original_size = test_path.stat().st_size
        assert original_size > 0, "Original image should have non-zero size"

        # Load and rotate
        img = cv2.imread(str(test_path))
        rotated = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

        # Save
        result = cv2.imwrite(str(test_path), rotated, [cv2.IMWRITE_JPEG_QUALITY, 95])
        assert result, "cv2.imwrite should succeed"

        # Verify file still exists and has content
        assert test_path.exists(), "Image file should exist after rotation"
        new_size = test_path.stat().st_size
        assert new_size > 0, "Rotated image should have non-zero size"

        # File size should be similar (within 50% margin for JPEG)
        assert 0.5 * original_size < new_size < 2.0 * original_size, \
            f"File size changed suspiciously: {original_size} -> {new_size}"

        # Verify it's still readable
        reloaded = cv2.imread(str(test_path))
        assert reloaded is not None, "Rotated image should be readable"
        assert reloaded.size > 0, "Rotated image should have pixels"

    def test_multiple_rotations(self, temp_dirs_with_image):
        """Test that multiple rotations work correctly"""
        test_path = temp_dirs_with_image['test_image']
        original_img = cv2.imread(str(test_path))
        original_shape = original_img.shape

        # Rotate 4 times by 90 degrees (should end up back at original orientation)
        current_img = original_img
        for i in range(4):
            current_img = cv2.rotate(current_img, cv2.ROTATE_90_CLOCKWISE)
            cv2.imwrite(str(test_path), current_img, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Verify file exists and is readable after each rotation
            assert test_path.exists(), f"Image should exist after rotation {i+1}"
            reloaded = cv2.imread(str(test_path))
            assert reloaded is not None, f"Image should be readable after rotation {i+1}"

        # After 4x90° rotations, should be back to original orientation
        final_img = cv2.imread(str(test_path))
        assert final_img.shape == original_shape, "Should be back to original dimensions after 360°"

    def test_path_construction(self):
        """Test that path construction works correctly"""
        from pathlib import Path

        # Simulate how the rotation endpoint constructs paths
        output_dir = Path("/tmp/test_output")
        filename = "test_image.jpg"

        # This is what the code does
        enhanced_path = output_dir / filename

        # Verify it creates correct path
        assert str(enhanced_path) == "/tmp/test_output/test_image.jpg"
        assert enhanced_path.name == filename
        assert enhanced_path.parent == output_dir

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
