from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

# Database connection URL (using aiosqlite for async SQLite)
DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Base class for all ORM models in SQLAlchemy 2.0+
class Base(DeclarativeBase):
    pass

# Database Model for Posts
class Post(Base):
    __tablename__ = "posts"  # Name of the table in the database

    # Primary key UUID, automatically generated if not provided
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caption = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    # Timestamp when the post is created (UTC)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Create the async engine that handles connections to the database
engine = create_async_engine(DATABASE_URL)

# Factory for creating async database sessions
# expire_on_commit=False prevents attributes from expiring after commit so they can still be read
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Function to initialize the database by creating all tables defined under Base
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# FastAPI dependency to yield an async database session per request and ensure cleanup
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session