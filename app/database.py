import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Reads from environment variable — set in docker-compose.yml or a .env file.
# Format: postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/ticket_intake",
)

# pool_pre_ping tests a pooled connection before using it, so after a database
# restart the first request reconnects instead of failing on a dead connection.
engine = create_async_engine(DATABASE_URL, echo=True, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency for FastAPI routes — yields a DB session."""
    async with AsyncSessionLocal() as session:
        yield session
