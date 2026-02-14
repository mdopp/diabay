"""Database models for DiaBay"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Image(Base):
    """Main image record"""
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True, nullable=False)
    original_path = Column(String, nullable=False)
    enhanced_path = Column(String)

    # Metadata
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)  # bytes
    exif_date = Column(DateTime)

    # Processing state
    status = Column(String, default="pending")  # pending, processing, complete, error
    stage = Column(String)  # ingestion, enhancement, tagging
    progress = Column(Float, default=0.0)

    # Enhancement parameters used
    histogram_clip = Column(Float)
    clahe_clip = Column(Float)
    face_detected = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tags = relationship("ImageTag", back_populates="image", cascade="all, delete-orphan")
    image_metadata = relationship("ImageMetadata", back_populates="image", uselist=False,
                                 cascade="all, delete-orphan")
    embedding = relationship("ImageEmbedding", back_populates="image", uselist=False,
                            cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_status_stage', 'status', 'stage'),
        Index('idx_created_at', 'created_at'),
    )


class ImageTag(Base):
    """Tags associated with images (AI-generated or manual)"""
    __tablename__ = "image_tags"

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    tag = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)  # 'ai' or 'manual'
    confidence = Column(Float)  # 0.0-1.0 for AI tags
    category = Column(String)  # 'scene', 'era', 'film_stock', 'custom'

    created_at = Column(DateTime, default=datetime.utcnow)

    image = relationship("Image", back_populates="tags")

    __table_args__ = (
        Index('idx_tag_source', 'tag', 'source'),
    )


class ImageMetadata(Base):
    """Transformation metadata (rotation, mirroring)"""
    __tablename__ = "image_metadata"

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey("images.id"), unique=True, nullable=False)

    rotation = Column(Integer, default=0)  # 0, 90, 180, 270
    mirror_h = Column(Boolean, default=False)
    mirror_v = Column(Boolean, default=False)

    # Film information
    film_type = Column(String)  # kodachrome, ektachrome, etc.
    era = Column(String)  # 1950s, 1970s, etc.

    # OCR extracted text
    ocr_text = Column(Text)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    image = relationship("Image", back_populates="image_metadata")


class ImageEmbedding(Base):
    """Similarity features for duplicate detection and smart albums"""
    __tablename__ = "image_embeddings"

    id = Column(Integer, primary_key=True)
    image_id = Column(Integer, ForeignKey("images.id"), unique=True, nullable=False)

    phash = Column(String, index=True)  # Perceptual hash (hex string)
    color_hist = Column(Text)  # JSON serialized color histogram
    face_count = Column(Integer, default=0)

    # Similarity scores (computed on demand)
    similar_images = Column(Text)  # JSON list of similar image IDs with scores

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    image = relationship("Image", back_populates="embedding")


class ProcessingSession(Base):
    """Track processing sessions for statistics and resume capability"""
    __tablename__ = "processing_sessions"

    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, index=True, nullable=False)

    # Batch information
    batch_name = Column(String)
    expected_count = Column(Integer)

    # Statistics
    files_processed = Column(Integer, default=0)
    files_pending = Column(Integer, default=0)
    avg_processing_time = Column(Float)  # seconds

    # Timestamps
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow)

    # Performance tracking
    hourly_counts = Column(Text)  # JSON dict of hour -> count

    is_active = Column(Boolean, default=True)


class DuplicateGroup(Base):
    """Groups of duplicate or similar images"""
    __tablename__ = "duplicate_groups"

    id = Column(Integer, primary_key=True)
    group_id = Column(String, unique=True, index=True, nullable=False)

    # Type of duplication
    type = Column(String)  # 'exact', 'near', 'similar'
    source = Column(String)  # 'input' or 'output'

    # Images in group (JSON list of image IDs)
    image_ids = Column(Text, nullable=False)

    # Similarity scores
    avg_similarity = Column(Float)

    # Resolution status
    resolved = Column(Boolean, default=False)
    kept_image_id = Column(Integer, ForeignKey("images.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
