from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    # Validate a pooled connection before handing it out, so a server-side idle
    # disconnect surfaces as a transparent reconnect rather than a mid-query
    # failure that wedges the caller.
    pool_pre_ping=True,
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _set_pgvector_options(dbapi_conn, connection_record):
    """Enable pgvector 0.8+ iterative scans and tuned search parameters."""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET hnsw.ef_search = 100")
    cursor.execute("SET hnsw.iterative_scan = relaxed_order")
    cursor.close()


async def get_session():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
