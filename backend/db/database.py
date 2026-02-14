"""Database connection and session management"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from db.models import Base
from config import settings


# Create async engine with SQLite concurrency settings
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # 30 second timeout for lock waits
    },
    pool_pre_ping=True,  # Verify connections before using them
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Enable WAL mode for better concurrency
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        # Set busy timeout
        await conn.execute(text("PRAGMA busy_timeout=30000"))
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for getting database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
