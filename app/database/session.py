from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

# A single pooled engine per process. pool_size/max_overflow are the knobs
# that matter under load: too small and requests queue on a connection,
# too large and Postgres itself becomes the bottleneck (each connection is
# a backend process). pool_pre_ping guards against stale connections after
# the DB restarts or a load balancer idles one out.
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI/Strawberry dependency: one session per request, always
    closed even if the request raises."""
    async with AsyncSessionLocal() as session:
        yield session
