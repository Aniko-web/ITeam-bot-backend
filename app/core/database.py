import logging
import socket
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

logger = logging.getLogger("DATABASE")

db_url = settings.DATABASE_URL

# Detect unresolvable Docker host '@postgres:' outside Docker (e.g. on Alwaysdata or local dev)
if "@postgres:" in db_url or "@postgres/" in db_url:
    try:
        socket.gethostbyname("postgres")
    except socket.gaierror:
        logger.warning("Docker hostname 'postgres' is not resolvable in this environment. Falling back to local SQLite.")
        db_url = "sqlite+aiosqlite:///./mlbb_platform.db"

# Adjust sqlite connect args if needed
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
