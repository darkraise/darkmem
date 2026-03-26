import secrets

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.auth import hash_api_key
from app.config import settings
from app.database import get_session
from app.main import app
from app.models import Base
from app.models.api_key import ApiKey


def _generate_test_api_key() -> tuple[str, str]:
    raw = "dm_" + secrets.token_hex(24)
    key_hash = hash_api_key(raw)
    return raw, key_hash

test_engine = create_async_engine(settings.test_database_url)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session():
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(session):
    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_key_raw(session):
    raw_key, key_hash = _generate_test_api_key()
    key = ApiKey(name="test-key", key_hash=key_hash, scopes=["read", "write", "admin"])
    session.add(key)
    await session.flush()
    return raw_key


@pytest_asyncio.fixture
async def auth_headers(api_key_raw):
    return {"Authorization": f"Bearer {api_key_raw}"}
